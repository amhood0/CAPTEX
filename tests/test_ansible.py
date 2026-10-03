"""Phase 5 tests use fakes and never install packages or start a VM."""
import json
import threading

import pytest
from fastapi import HTTPException

from app.main import app
from app.routers.automation import get_automation_manager
from app.services.ansible import AnsibleService
from app.services.automation_operations import AutomationManager
from app.services.vagrant import CommandResult


def result(command, exit_code=0, stdout="", stderr="", timed_out=False):
    return CommandResult(command.split(), exit_code, stdout, stderr, timed_out)


class FakeVagrant:
    def __init__(self, state="running", ansible=True):
        self.state = state
        self.ansible = ansible
        self.calls = []
        self.fail_upload = False
        self.fail_playbook = False

    def status(self):
        return {"ok": self.state != "unknown", "state": self.state, "command": {}}

    def guest_command(self, command, timeout=60):
        self.calls.append(("ssh", command, timeout))
        if command == "/bin/true":
            return result(command)
        if command == "command -v ansible-playbook":
            return result(command, 0 if self.ansible else 1, "/usr/bin/ansible-playbook\n" if self.ansible else "")
        if command == "ansible-playbook --version":
            return result(command, 0 if self.ansible else 1, "ansible-playbook [core 2.16]\n")
        if "ansible-playbook -i" in command:
            return result(command, 2 if self.fail_playbook else 0,
                          "fatal: validation failed" if self.fail_playbook else "CAPTEX_ANSIBLE_OK\n")
        return result(command)

    def bootstrap_ansible(self):
        self.calls.append(("bootstrap",))
        self.ansible = True
        return result("vagrant provision")

    def upload(self, source, destination):
        self.calls.append(("upload", source.name, destination))
        return result("vagrant upload", 1 if self.fail_upload else 0,
                      stderr="upload failed" if self.fail_upload else "")


def finish(manager, action):
    assert manager.submit(action, 1)["status"] == "running"
    manager.executor.submit(lambda: None).result(timeout=5)
    return manager.state()


def test_connectivity_requires_running_vm():
    service = AnsibleService(FakeVagrant("poweroff"))
    response = service.connectivity()
    assert not response["ok"]
    assert "Start" in response["message"]


def test_prepare_bootstraps_and_transfers_fixed_assets():
    vagrant = FakeVagrant(ansible=False)
    response = AnsibleService(vagrant).prepare()
    assert response["ok"]
    assert ("bootstrap",) in vagrant.calls
    uploads = [call for call in vagrant.calls if call[0] == "upload"]
    assert [call[1] for call in uploads] == ["inventory.ini", "connectivity.yml", "phase5-message.txt"]
    assert all(call[2].startswith("/tmp/captex-phase5/") for call in uploads)


def test_validation_requires_success_marker():
    service = AnsibleService(FakeVagrant())
    response = service.validate()
    assert response["ok"] and response["result"]["exit_code"] == 0
    assert "CAPTEX_ANSIBLE_OK" in response["result"]["stdout"]

    vagrant = FakeVagrant()
    vagrant.fail_playbook = True
    response = AnsibleService(vagrant).validate()
    assert not response["ok"]


def test_upload_failure_stops_workflow():
    vagrant = FakeVagrant()
    vagrant.fail_upload = True
    response = AnsibleService(vagrant).prepare()
    assert not response["ok"] and "File transfer failed" in response["message"]
    assert not any("ansible-playbook -i" in call[1] for call in vagrant.calls if call[0] == "ssh")


def test_background_operation_and_persistence(tmp_path):
    manager = AutomationManager(tmp_path, AnsibleService(FakeVagrant()))
    try:
        operation = finish(manager, "validate")
        assert operation["status"] == "succeeded"
        assert operation["completed_at"]
        assert json.loads((tmp_path / "ansible-operation.json").read_text())["details"]["ok"]
    finally:
        manager.executor.shutdown()


def test_automation_and_vm_operations_share_lock(tmp_path):
    entered, release = threading.Event(), threading.Event()
    service = AnsibleService(FakeVagrant())
    original = service.validate

    def blocked():
        entered.set()
        release.wait(5)
        return original()

    service.validate = blocked
    automation = AutomationManager(tmp_path, service)
    from app.services.vm_operations import OperationManager
    vm = OperationManager(tmp_path)
    try:
        automation.submit("validate", 1)
        assert entered.wait(3)
        with pytest.raises(HTTPException) as error:
            vm.submit("status", 1)
        assert error.value.status_code == 409
    finally:
        release.set()
        automation.executor.shutdown()
        vm.executor.shutdown()


def test_automation_api(client, tmp_path):
    manager = AutomationManager(tmp_path, AnsibleService(FakeVagrant()))
    app.dependency_overrides[get_automation_manager] = lambda: manager
    try:
        environment = client.post("/api/virtualization/environment").json()
        response = client.post(f"/api/environments/{environment['id']}/automation/validate")
        assert response.status_code == 202
        manager.executor.submit(lambda: None).result(timeout=5)
        assert client.get("/api/automation/operation").json()["status"] == "succeeded"
        assert client.get("/automation").status_code == 200
        manual = client.post("/api/environments", json={"name": "Manual", "os": "Windows"}).json()
        assert client.post(f"/api/environments/{manual['id']}/automation/validate").status_code == 400
        assert client.post("/api/environments/999/automation/validate").status_code == 404
        assert client.post(f"/api/environments/{environment['id']}/automation/arbitrary").status_code == 422
        assert client.post(f"/api/environments/{environment['id']}/automation/validate",
                           headers={"Origin": "https://other.example"}).status_code == 403
    finally:
        app.dependency_overrides.pop(get_automation_manager, None)
        manager.executor.shutdown()
