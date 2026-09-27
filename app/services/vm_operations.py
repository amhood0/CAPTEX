"""One background VM operation at a time, with a cross-process lock and durable output."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException
from app.config import BASE_DIR
from app.services.vagrant import VagrantService


def utc_stamp():
    return datetime.now(timezone.utc).isoformat()


class OperationManager:
    def __init__(self, directory=None, service=None):
        self.directory = Path(directory or BASE_DIR / ".runtime")
        self.service = service or VagrantService()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="captex-vm")

    def _acquire(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        handle = (self.directory / "vm.lock").open("a+b")
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise HTTPException(409, "A VM operation is already in progress; wait for it to finish")
        return handle

    def _save(self, operation):
        temporary = self.directory / f"{uuid4().hex}.tmp"
        temporary.write_text(json.dumps(operation), encoding="utf-8")
        temporary.replace(self.directory / "vm-operation.json")

    def state(self):
        try:
            operation = json.loads((self.directory / "vm-operation.json").read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"status": "idle"}
        except (ValueError, OSError):
            return {"status": "error", "message": "Saved VM operation could not be read. Refresh VM status."}
        if operation.get("status") == "running":
            try:
                handle = self._acquire()
            except HTTPException:
                return operation
            try:
                # Reload after locking: another worker may have just finished.
                operation = json.loads((self.directory / "vm-operation.json").read_text(encoding="utf-8"))
                if operation.get("status") == "running":
                    operation.update(status="interrupted", message="The server stopped before the operation finished. Refresh VM status before proceeding.", completed_at=utc_stamp())
                    self._save(operation)
            finally:
                handle.close()
        return operation

    def submit(self, action, environment_id=None):
        if action not in {"check", "status", "start", "stop"}:
            raise HTTPException(422, "Unsupported VM operation")
        handle = self._acquire()
        operation = dict(id=uuid4().hex, action=action, environment_id=environment_id,
                         status="running", started_at=utc_stamp(), completed_at=None,
                         message=f"{action.title()} in progress")
        try:
            self._save(operation)
            self.executor.submit(self._execute, operation.copy(), handle)
        except Exception:
            handle.close()
            raise
        return operation

    def _execute(self, operation, handle):
        try:
            action = operation["action"]
            if action in {"check", "start"}:
                readiness = self.service.readiness()
                operation["readiness"] = readiness
                if not readiness["ready"]:
                    operation.update(status="failed", message="Prerequisites are missing; follow the actions below.")
                    return
            if action == "check":
                operation.update(status="succeeded", message="All prerequisites are ready.")
                return
            if action in {"start", "stop"}:
                # Check provider before halt, and do not mutate on unknown status.
                before = self.service.status()
                operation["vm"] = before
                if not before["ok"]:
                    operation.update(status="failed", message="VM status could not be determined; inspect the command output.")
                    return
                if action == "stop" and before["state"] in {"not_created", "poweroff"}:
                    operation.update(status="succeeded", message="VM is already stopped.")
                    return
                if action == "start" and before["state"] == "running":
                    operation.update(status="succeeded", message="VM is already running.")
                    return
                result = self.service.start() if action == "start" else self.service.stop()
                operation["command"] = result.to_dict()
                if result.timed_out or result.exit_code != 0:
                    operation["vm"] = {"state": "unknown", "ok": False}
                    operation.update(status="failed", message="VM command timed out. Refresh VM status before retrying." if result.timed_out else "VM command failed; inspect the output below.")
                    return
            operation["vm"] = self.service.status()
            expected = {"running"} if action == "start" else {"poweroff", "not_created"} if action == "stop" else None
            success = operation["vm"]["ok"] and (expected is None or operation["vm"]["state"] in expected)
            operation.update(status="succeeded" if success else "failed", message=f"VM state: {operation['vm']['state']}")
        except Exception as error:
            operation.update(status="failed", message=f"VM operation could not finish: {error}")
        finally:
            operation["completed_at"] = utc_stamp()
            try:
                self._save(operation)
            finally:
                handle.close()


manager = OperationManager()
