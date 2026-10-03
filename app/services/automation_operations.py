"""Background Ansible operations with exclusive VM lock."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from app.config import BASE_DIR
from app.services.ansible import AnsibleService
from app.services.vm_operations import OperationManager, utc_stamp


class AutomationManager(OperationManager):
    def __init__(self, directory=None, service=None):
        self.directory = Path(directory or BASE_DIR / ".runtime")
        self.service = service or AnsibleService()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="captex-ansible")

    @property
    def operation_path(self):
        return self.directory / "ansible-operation.json"

    def _save(self, operation):
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.directory / f"{uuid4().hex}.tmp"
        temporary.write_text(json.dumps(operation), encoding="utf-8")
        temporary.replace(self.operation_path)

    def state(self):
        try:
            operation = json.loads(self.operation_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"status": "idle"}
        except (ValueError, OSError):
            return {"status": "error", "message": "Saved Ansible operation could not be read."}
        if operation.get("status") == "running":
            try:
                handle = self._acquire()
            except HTTPException:
                return operation
            try:
                operation = json.loads(self.operation_path.read_text(encoding="utf-8"))
                if operation.get("status") == "running":
                    operation.update(status="interrupted", completed_at=utc_stamp(),
                                     message="The server stopped before Ansible finished. Check VM state and retry.")
                    self._save(operation)
            finally:
                handle.close()
        return operation

    def submit(self, action, environment_id):
        if action not in {"connectivity", "prepare", "validate"}:
            raise HTTPException(422, "Unsupported Ansible operation")
        handle = self._acquire()
        operation = {"id": uuid4().hex, "action": action, "environment_id": environment_id,
                     "status": "running", "started_at": utc_stamp(), "completed_at": None,
                     "message": f"Ansible {action} in progress"}
        try:
            self._save(operation)
            self.executor.submit(self._execute, operation.copy(), handle)
        except Exception:
            handle.close()
            raise
        return operation

    def _execute(self, operation, handle):
        try:
            result = getattr(self.service, operation["action"])()
            operation["details"] = result
            operation.update(status="succeeded" if result["ok"] else "failed", message=result["message"])
        except Exception as error:
            operation.update(status="failed", message=f"Ansible operation could not finish: {error}")
        finally:
            operation["completed_at"] = utc_stamp()
            try:
                self._save(operation)
            finally:
                handle.close()


manager = AutomationManager()
