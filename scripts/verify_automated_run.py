"""Opt-in real Phase 6 API-to-VM automated test verification."""
import argparse
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Capability, CapabilityVersion, Environment, TestCase, TestPlan, TestRun
from app.routers.automated_runs import get_automated_run_manager
from app.services.automated_runs import AutomatedRunManager
from app.services.capability_execution import CapabilityExecutionService
from app.services.manual_runs import snapshot_cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Allow real VMware and guest execution")
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to acknowledge that this starts and changes the managed VM")
    with tempfile.TemporaryDirectory(prefix="captex-phase6-live-") as directory:
        engine = create_engine(f"sqlite:///{Path(directory) / 'verify.db'}", connect_args={"check_same_thread": False})
        factory = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)
        with factory() as db:
            capability = Capability(name="Phase 6 live demo", category="Validation")
            db.add(capability); db.flush()
            version = CapabilityVersion(capability_id=capability.id, version="1", artifact_path="bundled:file-creation",
                                        execution_command="python3 run.py")
            plan = TestPlan(capability_id=capability.id, name="Three real validations")
            db.add_all([version, plan]); db.flush()
            cases = [
                TestCase(test_plan_id=plan.id, name="Exit zero", test_type="exit_code", expected_result="0"),
                TestCase(test_plan_id=plan.id, name="Output marker", test_type="stdout_contains", expected_result="CAPTEX_PHASE6_DEMO_OK"),
                TestCase(test_plan_id=plan.id, name="Created file", test_type="file_exists", expected_result="proof.txt"),
            ]
            environment = Environment(name="Managed Ubuntu", os="Ubuntu", vagrant_path="environments/ubuntu24")
            db.add_all([*cases, environment]); db.flush()
            run = TestRun(capability_version_id=version.id, test_plan_id=plan.id, environment_id=environment.id,
                          initiated_by="Phase 6 live verifier")
            snapshot_cases(run, cases); db.add(run); db.commit(); run_id = run.id
        manager = AutomatedRunManager(Path(directory) / "runtime", CapabilityExecutionService(), factory)
        def override_db():
            with factory() as db:
                yield db
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_automated_run_manager] = lambda: manager
        try:
            with TestClient(app) as client:
                response = client.post(f"/api/test-runs/{run_id}/execute")
                response.raise_for_status()
                manager.executor.submit(lambda: None).result(timeout=1200)
            with factory() as db:
                run = db.get(TestRun, run_id)
                print({"status": run.status, "overall_result": run.overall_result,
                       "results": [{"case": item.test_case.name, "status": item.status,
                                    "exit_code": item.exit_code, "duration": item.duration}
                                   for item in run.test_results]})
                if run.status != "completed" or run.overall_result != "PASS":
                    raise RuntimeError(run.error_message or "Automated test did not pass")
            print("LIVE PHASE 6 CHECK PASSED: three real results were stored as PASS.")
        finally:
            manager.executor.shutdown(wait=True)
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_automated_run_manager, None)
            engine.dispose()


if __name__ == "__main__":
    main()
