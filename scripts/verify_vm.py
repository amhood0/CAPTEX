"""Opt-in live API test. Creates/starts and then halts the managed Ubuntu VM.

Run: python -m scripts.verify_vm --live
Requires the VMware prerequisites and pinned box. Never destroys a VM or uses app.db.
"""
import argparse
import json
import tempfile
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Permit a real VM start and stop")
    if not parser.parse_args().live:
        parser.error("--live is required because this test starts a real VM")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import get_db
    from app.migrate import migrate
    from app.routers.virtualization import get_vm_manager
    from app.services.vagrant import VagrantService
    from app.services.vm_operations import OperationManager
    service = VagrantService()
    baseline = service.status()
    print("Initial VM state:", baseline["state"], flush=True)
    if not baseline["ok"] or baseline["state"] not in {"not_created", "poweroff"}:
        raise RuntimeError("The live test requires a stopped or uncreated managed VM")
    with tempfile.TemporaryDirectory(prefix="captex-live-") as directory:
        url = f"sqlite:///{Path(directory) / 'test.db'}"
        migrate(url)
        engine = create_engine(url, connect_args={"check_same_thread": False})
        sessions = sessionmaker(bind=engine)
        def database():
            with sessions() as session:
                yield session
        manager = OperationManager(service=service)
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_vm_manager] = lambda: manager
        attempted = False
        try:
            with TestClient(app) as client:
                def invoke(endpoint):
                    response = client.post(endpoint)
                    assert response.status_code == 202, response.text
                    deadline = time.monotonic() + 1200
                    while time.monotonic() < deadline:
                        operation = client.get("/api/virtualization/operation").json()
                        if operation["status"] != "running":
                            print(json.dumps(operation), flush=True)
                            assert operation["status"] == "succeeded", operation["message"]
                            return operation
                        time.sleep(1)
                    raise TimeoutError("Live API operation did not finish")
                invoke("/api/virtualization/check")
                env = client.post("/api/virtualization/environment").json()["id"]
                attempted = True
                started = invoke(f"/api/environments/{env}/vm/start")
                assert started["vm"]["state"] == "running"
                assert invoke(f"/api/environments/{env}/vm/status")["vm"]["state"] == "running"
                assert invoke(f"/api/environments/{env}/vm/stop")["vm"]["state"] in {"poweroff", "not_created"}
                print("LIVE API CHECK PASSED: VM started, reported running, and stopped.", flush=True)
        finally:
            manager.executor.shutdown(wait=True)
            if attempted:
                current = service.status()
                if current["state"] not in {"poweroff", "not_created"}:
                    print("Cleanup halt:", json.dumps(service.stop().to_dict()), flush=True)
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_vm_manager, None)
            engine.dispose()


if __name__ == "__main__":
    main()
