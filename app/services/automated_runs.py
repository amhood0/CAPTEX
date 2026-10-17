"""Background orchestration and durable database result recording."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from app.config import RUNTIME_DIR
from app.database import SessionLocal
from app.models import TestRun, utc_now
from app.services.capability_execution import CapabilityExecutionService
from app.services.vm_operations import OperationManager


class AutomatedRunManager(OperationManager):
    def __init__(self, directory=None, service=None, session_factory=None):
        self.directory = Path(directory or RUNTIME_DIR)
        self.service = service or CapabilityExecutionService()
        self.session_factory = session_factory or SessionLocal
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="captex-run")

    @property
    def operation_path(self):
        return self.directory / "test-operation.json"

    def submit_run(self, run_id):
        handle = self._acquire()
        operation = {"id": uuid4().hex, "action": "automated-test", "test_run_id": run_id,
                     "status": "running", "started_at": utc_now().isoformat(), "completed_at": None,
                     "message": "Automated test queued"}
        try:
            self._save(operation)
            self.executor.submit(self._execute_run, operation.copy(), handle)
        except Exception:
            handle.close()
            raise
        return operation

    def state(self):
        operation = super().state()
        if operation.get("status") == "interrupted" and operation.get("test_run_id"):
            with self.session_factory() as db:
                run = db.get(TestRun, operation["test_run_id"])
                if run is not None and run.status not in {"completed", "failed"}:
                    self._set_failure(db, run, "The server stopped before automated execution finished.")
        return operation

    def _set_failure(self, db, run, message):
        now = utc_now()
        for result in run.test_results:
            if result.status == "PENDING":
                result.status, result.actual_result, result.notes = "ERROR", "Execution did not complete", message
        run.status, run.overall_result, run.error_message = "failed", "ERROR", message
        run.started_at, run.completed_at = run.started_at or now, now
        run.duration = max(0, int((now - run.started_at).total_seconds()))
        db.commit()

    def _progress(self, db, run, operation, status, message):
        run.status = status
        operation["message"] = message
        db.commit()
        self._save(operation)

    def _execute_run(self, operation, handle):
        db = self.session_factory()
        vm_started = False
        run = None
        try:
            run = db.get(TestRun, operation["test_run_id"])
            if run is None or run.status != "queued":
                raise ValueError("The test run is missing or no longer queued")
            run.started_at = utc_now()
            self._progress(db, run, operation, "provisioning", "Starting and checking the managed VM")
            status = self.service.vagrant.status()
            if not status["ok"]:
                raise RuntimeError("Could not determine managed VM status")
            if status["state"] != "running":
                started = self.service.vagrant.start()
                if started.exit_code != 0 or started.timed_out:
                    raise RuntimeError("Managed VM startup failed")
                vm_started = True
            self._progress(db, run, operation, "configuring", "Preparing Ansible and the guest workspace")
            response = self.service.execute(
                run.capability_version, run.test_results,
                lambda status, message: self._progress(db, run, operation, status, message),
            )
            operation["details"] = response
            if not response["ok"]:
                raise RuntimeError(response["message"])
            returned = {item["test_case_id"]: item for item in response["results"]}
            if set(returned) != {result.test_case_id for result in run.test_results}:
                raise RuntimeError("Guest results do not match the run's test cases")
            self._progress(db, run, operation, "collecting_results", "Validating and storing returned results")
            for result in run.test_results:
                item = returned[result.test_case_id]
                for field in ("status", "actual_result", "stdout", "stderr", "exit_code", "duration", "notes"):
                    setattr(result, field, item.get(field))
            statuses = {result.status for result in run.test_results}
            run.overall_result = "ERROR" if "ERROR" in statuses else "FAIL" if "FAIL" in statuses else "PASS"
            operation.update(status="succeeded", message=f"Automated test completed: {run.overall_result}")
        except Exception as error:
            message = str(error)
            if run is not None:
                db.rollback()
                run = db.get(TestRun, operation["test_run_id"])
                self._set_failure(db, run, message)
            operation.update(status="failed", message=message)
        finally:
            if run is not None and run.status != "failed":
                self._progress(db, run, operation, "cleaning_up", "Finishing the run and stopping the VM if CAPTEX started it")
            halted = None
            if vm_started:
                halted = self.service.vagrant.stop()
            if run is not None and run.status != "failed":
                now = utc_now()
                run.status, run.completed_at = "completed", now
                run.duration = max(0, int((now - run.started_at).total_seconds()))
                if halted and (halted.exit_code != 0 or halted.timed_out):
                    run.error_message = "Tests completed, but the VM could not be stopped automatically."
                db.commit()
            operation["completed_at"] = utc_now().isoformat()
            if halted:
                operation["cleanup"] = halted.to_dict()
            try:
                self._save(operation)
            finally:
                db.close()
                handle.close()


manager = AutomatedRunManager()
