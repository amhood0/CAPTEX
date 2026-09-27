"""Virtualization tests never start a real VM."""
import json
import sys
import threading
import pytest
from fastapi import HTTPException
from app.services.vagrant import VagrantService, CommandResult
from app.services.vm_operations import OperationManager
from app.routers.virtualization import get_vm_manager
from app.main import app


class FakeVagrant:
    def __init__(self):
        self.current = "not_created"
        self.ready = True
        self.failure = False
        self.timed_out = False
        self.calls = []

    def readiness(self):
        return {"ready": self.ready, "checks": []}

    def status(self):
        return {"state": self.current, "ok": self.current != "unknown", "command": {"stdout": "status"}}

    def start(self):
        self.calls.append("start")
        self.current = "running"
        return CommandResult(["vagrant", "up"], 1 if self.failure else 0, "output", "failed" if self.failure else "", self.timed_out)

    def stop(self):
        self.calls.append("stop")
        self.current = "poweroff"
        return CommandResult(["vagrant", "halt"], 0, "stopped", "")


def finish(manager, action):
    response = manager.submit(action, 1)
    assert response["status"] == "running"
    manager.executor.submit(lambda: None).result(timeout=5)
    return manager.state()


def test_lifecycle_and_durable_output(tmp_path):
    service = FakeVagrant()
    manager = OperationManager(tmp_path, service)
    try:
        assert finish(manager, "check")["readiness"]["ready"]
        assert finish(manager, "start")["vm"]["state"] == "running"
        assert finish(manager, "start")["status"] == "succeeded"
        assert service.calls == ["start"]
        assert finish(manager, "stop")["vm"]["state"] == "poweroff"
        assert finish(manager, "stop")["status"] == "succeeded"
        saved = json.loads((tmp_path / "vm-operation.json").read_text())
        assert saved["completed_at"] and saved["status"] == "succeeded"
    finally:
        manager.executor.shutdown()


@pytest.mark.parametrize("reason", ["missing", "unknown", "nonzero", "timeout"])
def test_failures(tmp_path, reason):
    service = FakeVagrant()
    service.ready = reason != "missing"
    service.current = "unknown" if reason == "unknown" else "not_created"
    service.failure = reason == "nonzero"
    service.timed_out = reason == "timeout"
    manager = OperationManager(tmp_path, service)
    try:
        operation = finish(manager, "start")
        assert operation["status"] == "failed"
        if reason in {"missing", "unknown"}:
            assert service.calls == []
        else:
            assert operation["vm"]["state"] == "unknown"
            assert operation["command"]["stdout"] == "output"
    finally:
        manager.executor.shutdown()


def test_exclusive_operation_lock(tmp_path):
    entered, release = threading.Event(), threading.Event()
    service = FakeVagrant()
    original = service.start
    def blocked():
        entered.set()
        release.wait(5)
        return original()
    service.start = blocked
    first = OperationManager(tmp_path, service)
    second = OperationManager(tmp_path, service)
    try:
        first.submit("start")
        assert entered.wait(3)
        assert first.state()["status"] == "running"
        with pytest.raises(HTTPException) as error:
            second.submit("stop")
        assert error.value.status_code == 409
    finally:
        release.set()
        first.executor.shutdown()
        second.executor.shutdown()


def test_interrupted_operation(tmp_path):
    manager = OperationManager(tmp_path, FakeVagrant())
    manager._save({"status":"running", "action":"start"})
    assert manager.state()["status"] == "interrupted"
    manager.executor.shutdown()


@pytest.mark.parametrize("output,expected", [
    ("1,default,state,running\n1,default,provider-name,vmware_desktop\n", "running"),
    ("1,default,state,not_created\n", "not_created"),
    ("1,default,state,running\n1,default,provider-name,virtualbox\n", "unknown"),
    ("1,default,state,not_running\n1,default,provider-name,vmware_desktop\n", "poweroff"),
    ("human readable output", "unknown")])
def test_machine_readable_status(monkeypatch, output, expected):
    monkeypatch.setattr("app.services.vagrant.shutil.which", lambda name: "vagrant.exe")
    service = VagrantService(lambda args, timeout: CommandResult(args, 0, output, ""))
    assert service.status()["state"] == expected


def test_fixed_command_arguments(monkeypatch):
    monkeypatch.setattr("app.services.vagrant.shutil.which", lambda name: "vagrant.exe")
    calls = []
    def run(args, timeout):
        calls.append((args, timeout))
        return CommandResult(args, 0, "", "")
    service = VagrantService(run)
    service.start()
    service.stop()
    assert calls == [(["vagrant.exe", "up", "default", "--provider=vmware_desktop", "--no-provision"], 900), (["vagrant.exe", "halt", "default"], 180)]


def test_real_runner_capture_and_timeout():
    service = VagrantService()
    result = service.run_command([sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(7)"], timeout=10)
    assert result.exit_code == 7 and "out" in result.stdout and "err" in result.stderr
    result = service.run_command([sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.5)
    assert result.timed_out


def test_vm_api_mapping_and_actions(client, tmp_path):
    vm = OperationManager(tmp_path, FakeVagrant())
    app.dependency_overrides[get_vm_manager] = lambda: vm
    try:
        env = client.post("/api/virtualization/environment").json()
        assert client.post("/api/virtualization/environment").json() == env
        assert client.post(f"/api/environments/{env['id']}/vm/start").status_code == 202
        vm.executor.submit(lambda: None).result(timeout=5)
        assert client.get("/api/virtualization/operation").json()["vm"]["state"] == "running"
        assert client.get("/virtualization").status_code == 200
        assert client.delete(f"/api/environments/{env['id']}").status_code == 409
        assert client.put(f"/api/environments/{env['id']}", json={"vagrant_path":"../other"}).status_code == 409
        assert client.post(f"/api/environments/{env['id']}/vm/destroy").status_code == 422
        assert client.post("/api/environments/999/vm/start").status_code == 404
        manual = client.post("/api/environments", json={"name":"Manual", "os":"Windows", "vagrant_path":"C:/untrusted"}).json()
        assert client.post(f"/api/environments/{manual['id']}/vm/start").status_code == 400
        assert client.post("/api/virtualization/check", headers={"Origin":"https://other.example"}).status_code == 403
    finally:
        app.dependency_overrides.pop(get_vm_manager, None)
        vm.executor.shutdown()


def test_missing_vagrant(monkeypatch):
    monkeypatch.setattr("app.services.vagrant.shutil.which", lambda name: None)
    result = VagrantService().command("status")
    assert result.exit_code is None and "not installed" in result.stderr


@pytest.mark.parametrize("version,ready", [("202510.26.0", True), ("202510.26.01", False)])
def test_readiness_box_pin(monkeypatch, version, ready):
    import os
    from pathlib import Path
    if os.name != "nt":
        pytest.skip("Version 1 readiness checks target Windows")
    original = Path.is_file
    monkeypatch.setattr(Path, "is_file", lambda path: True if path.name in {"vmrun.exe", "Vagrantfile"} else original(path))
    def run(args, timeout):
        return CommandResult(args, 0, "STATE : 4 RUNNING", "")
    service = VagrantService(run)
    def command(*args, **kwargs):
        output = "Vagrant 2.4.9" if args[0] == "--version" else "vagrant-vmware-desktop (3.0.5, global)" if args[0] == "plugin" else f"bento/ubuntu-24.04 (vmware_desktop, {version}, (amd64))"
        return CommandResult(list(args), 0, output, "")
    monkeypatch.setattr(service, "command", command)
    result = service.readiness()
    assert result["ready"] is ready
    assert len(result["checks"]) == 6


def test_output_is_bounded():
    result = VagrantService().run_command([sys.executable, "-c", "print('x' * 70000)"], timeout=10)
    assert result.exit_code == 0
    assert result.stdout.startswith("[Earlier output truncated]")
    assert len(result.stdout) < 66000
