"""Opt-in live Phase 5 check against the real managed Ubuntu VM.

Run: python -m scripts.verify_ansible --live
The script starts a stopped VM, runs the app's Ansible API, then restores it to stopped.
"""
import argparse
import json
import tempfile
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Permit VM start, package installation, and stop")
    if not parser.parse_args().live:
        parser.error("--live is required because this test changes the guest")

    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import get_db
    from app.main import app
    from app.migrate import migrate
    from app.routers.automation import get_automation_manager
    from app.services.ansible import AnsibleService
    from app.services.automation_operations import AutomationManager
    from app.services.vagrant import VagrantService

    vagrant = VagrantService()
    initial = vagrant.status()
    print(f"Initial VM state: {initial['state']}", flush=True)
    if not initial["ok"] or initial["state"] not in {"not_created", "poweroff", "running"}:
        raise RuntimeError("Managed VM state could not be safely determined")
    started_here = initial["state"] != "running"
    if started_here:
        started = vagrant.start()
        if started.exit_code != 0 or started.timed_out:
            raise RuntimeError(f"VM start failed: {started.stderr or started.stdout}")

    with tempfile.TemporaryDirectory(prefix="captex-ansible-live-") as directory:
        url = f"sqlite:///{Path(directory) / 'test.db'}"
        migrate(url)
        engine = create_engine(url, connect_args={"check_same_thread": False})
        sessions = sessionmaker(bind=engine)

        def database():
            with sessions() as session:
                yield session

        manager = AutomationManager(Path(directory) / "operations", AnsibleService(vagrant))
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_automation_manager] = lambda: manager
        try:
            with TestClient(app) as client:
                environment_id = client.post("/api/virtualization/environment").json()["id"]
                response = client.post(f"/api/environments/{environment_id}/automation/validate")
                assert response.status_code == 202, response.text
                deadline = time.monotonic() + 1200
                while time.monotonic() < deadline:
                    operation = client.get("/api/automation/operation").json()
                    if operation["status"] != "running":
                        print(json.dumps(operation), flush=True)
                        if operation["status"] != "succeeded":
                            raise RuntimeError(operation["message"])
                        output = operation["details"]["result"]["stdout"]
                        if "CAPTEX_ANSIBLE_OK" not in output:
                            raise RuntimeError("Playbook success marker was not returned")
                        print("LIVE ANSIBLE CHECK PASSED: guest configured, file transferred, playbook output returned.", flush=True)
                        break
                    time.sleep(1)
                else:
                    raise TimeoutError("Live Ansible operation did not finish")
        finally:
            manager.executor.shutdown(wait=True)
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_automation_manager, None)
            engine.dispose()
            if started_here:
                stopped = vagrant.stop()
                print(f"Restored VM to stopped: {stopped.exit_code == 0}", flush=True)


if __name__ == "__main__":
    main()
