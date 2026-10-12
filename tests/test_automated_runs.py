"""Execution, persistence, validation, and endpoint tests."""
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from app.main import app
from app.models import Capability, CapabilityVersion, Environment, TestCase as Case, TestPlan as Plan, TestRun as Run
from app.routers.automated_runs import get_automated_run_manager
from app.services.automated_runs import AutomatedRunManager
from app.config import BASE_DIR
from app.services.capability_execution import CapabilityExecutionService
from app.services.artifacts import ArtifactStore
from app.services.vagrant import CommandResult


def command_result(exit_code=0):
    return CommandResult(["fake"], exit_code, "", "", False)


class FakeVagrant:
    def __init__(self, state="poweroff"):
        self.state, self.started, self.stopped = state, False, False

    def status(self):
        return {"ok": True, "state": self.state, "command": {}}

    def start(self):
        self.state, self.started = "running", True
        return command_result()

    def stop(self):
        self.state, self.stopped = "poweroff", True
        return command_result()


class FakeExecution:
    def __init__(self, returned_status="PASS"):
        self.vagrant, self.returned_status = FakeVagrant(), returned_status

    def execute(self, version, results, progress=None):
        if progress:
            progress("running", "executing")
        return {"ok": True, "message": "done", "steps": [], "results": [
            {"test_case_id": item.test_case_id, "status": self.returned_status,
             "actual_result": "0", "stdout": "demo", "stderr": "", "exit_code": 0,
             "duration": 4, "notes": None} for item in results
        ]}


def seed(db, artifact_path="bundled:phase6-demo", command="python3 run.py"):
    capability = Capability(name="Automated demo", category="Test")
    db.add(capability); db.flush()
    version = CapabilityVersion(capability_id=capability.id, version="1", artifact_path=artifact_path,
                                execution_command=command)
    plan = Plan(capability_id=capability.id, name="Automated plan")
    db.add_all([version, plan]); db.flush()
    case = Case(test_plan_id=plan.id, name="Exit", test_type="exit_code", expected_result="0", timeout=5)
    environment = Environment(name="Managed", os="Ubuntu", vagrant_path="environments/ubuntu24")
    db.add_all([case, environment]); db.flush()
    run = Run(capability_version_id=version.id, test_plan_id=plan.id, environment_id=environment.id)
    from app.services.manual_runs import snapshot_cases
    snapshot_cases(run, [case]); db.add(run); db.commit()
    return run.id


def test_fixed_guest_runner_evaluates_all_supported_types(tmp_path):
    artifact = tmp_path / "artifact"; artifact.mkdir()
    (artifact / "program.py").write_text("from pathlib import Path\nPath('made.txt').write_text('yes')\nprint('hello marker')\n")
    manifest = {"artifact_root": str(artifact), "argv": [sys.executable, "program.py"], "cases": [
        {"id": 1, "test_type": "exit_code", "expected_result": "0", "timeout": 5},
        {"id": 2, "test_type": "stdout_contains", "expected_result": "marker", "timeout": 5},
        {"id": 3, "test_type": "file_exists", "expected_result": "made.txt", "timeout": 5},
    ]}
    manifest_path, output = tmp_path / "manifest.json", tmp_path / "results.json"
    manifest_path.write_text(json.dumps(manifest))
    runner = BASE_DIR / "automation/files/capability_runner.py"
    completed = subprocess.run([sys.executable, runner, manifest_path, output], capture_output=True, text=True)
    results = json.loads(output.read_text())
    assert completed.returncode == 0 and "CAPTEX_RESULTS_READY" in completed.stdout
    assert [item["status"] for item in results] == ["PASS", "PASS", "PASS"]


def test_artifacts_are_restricted_to_project_directory():
    assert ArtifactStore().resolve("bundled:phase6-demo").name == "phase6-demo"
    with pytest.raises(ValueError):
        ArtifactStore().resolve("bundled:../automation")
    with pytest.raises(ValueError):
        CapabilityExecutionService.argv("")


def test_manager_records_results_and_stops_vm(db, tmp_path):
    run_id = seed(db)
    factory = __import__("sqlalchemy.orm").orm.sessionmaker(bind=db.get_bind())
    service = FakeExecution("PASS")
    manager = AutomatedRunManager(tmp_path, service, factory)
    try:
        manager.submit_run(run_id)
        manager.executor.submit(lambda: None).result(timeout=5)
        db.expire_all(); run = db.get(Run, run_id)
        assert run.status == "completed" and run.overall_result == "PASS"
        assert run.test_results[0].stdout == "demo" and service.vagrant.stopped
        assert manager.state()["status"] == "succeeded"
    finally:
        manager.executor.shutdown()


def test_automated_run_api_validation(client, db):
    run_id = seed(db)
    fake = SimpleNamespace(submit_run=lambda value: {"status": "running", "test_run_id": value},
                           state=lambda: {"status": "idle"})
    app.dependency_overrides[get_automated_run_manager] = lambda: fake
    try:
        assert client.post(f"/api/test-runs/{run_id}/execute").status_code == 202
        assert client.get("/api/automated-runs/operation").json()["status"] == "idle"
        assert client.post("/api/test-runs/999/execute").status_code == 404
        assert client.post(f"/api/test-runs/{run_id}/execute", headers={"Origin": "https://other.example"}).status_code == 403
        run = db.get(Run, run_id); run.status = "completed"; db.commit()
        assert client.post(f"/api/test-runs/{run_id}/execute").status_code == 409
    finally:
        app.dependency_overrides.pop(get_automated_run_manager, None)


def test_run_page_shows_progress_and_hides_completed_actions(client, db):
    run_id = seed(db)
    run = db.get(Run, run_id)
    run.status = "provisioning"
    db.commit()
    page = client.get(f"/test-runs/{run_id}").text
    assert "Automated run progress" in page and 'id="automatedProgress"' in page
    run.status, run.overall_result = "completed", "PASS"
    db.commit()
    page = client.get(f"/test-runs/{run_id}").text
    assert "<th>Actions</th>" not in page and ">Details</a>" not in page
