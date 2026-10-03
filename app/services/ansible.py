"""Guest-local Ansible workflow using only approved project assets and commands."""
from app.config import BASE_DIR
from app.services.vagrant import CommandResult, VagrantService


AUTOMATION = BASE_DIR / "automation"
REMOTE_ROOT = "/tmp/captex-phase5"


class AnsibleService:
    """Bootstrap and run Ansible inside the managed Vagrant guest."""

    def __init__(self, vagrant: VagrantService | None = None):
        self.vagrant = vagrant or VagrantService()

    @staticmethod
    def _step(name: str, result: CommandResult) -> dict:
        return {"name": name, **result.to_dict()}

    def connectivity(self) -> dict:
        status = self.vagrant.status()
        if not status["ok"] or status["state"] != "running":
            return {"ok": False, "message": "Start the managed VM before using Ansible.",
                    "vm": status, "steps": []}
        result = self.vagrant.guest_command("/bin/true", timeout=60)
        return {"ok": result.exit_code == 0 and not result.timed_out,
                "message": "Guest SSH connectivity succeeded." if result.exit_code == 0 else "Guest SSH connectivity failed.",
                "vm": status, "steps": [self._step("SSH connectivity", result)]}

    def prepare(self) -> dict:
        connected = self.connectivity()
        if not connected["ok"]:
            return connected
        steps = connected["steps"]
        check = self.vagrant.guest_command("command -v ansible-playbook", timeout=60)
        steps.append(self._step("Check Ansible", check))
        if check.exit_code != 0:
            bootstrap = self.vagrant.bootstrap_ansible()
            steps.append(self._step("Install ansible-core", bootstrap))
            if bootstrap.exit_code != 0 or bootstrap.timed_out:
                return {"ok": False, "message": "Ansible installation failed.", "vm": connected["vm"], "steps": steps}
        verify = self.vagrant.guest_command("ansible-playbook --version", timeout=60)
        steps.append(self._step("Verify Ansible", verify))
        if verify.exit_code != 0:
            return {"ok": False, "message": "ansible-playbook is unavailable after setup.", "vm": connected["vm"], "steps": steps}
        mkdir = self.vagrant.guest_command(
            f"rm -rf {REMOTE_ROOT} && install -d -m 0750 {REMOTE_ROOT}/playbooks {REMOTE_ROOT}/files",
            timeout=60,
        )
        steps.append(self._step("Create staging directory", mkdir))
        if mkdir.exit_code != 0:
            return {"ok": False, "message": "Could not prepare the guest staging directory.", "vm": connected["vm"], "steps": steps}
        assets = (
            (AUTOMATION / "inventory.ini", f"{REMOTE_ROOT}/inventory.ini"),
            (AUTOMATION / "playbooks/connectivity.yml", f"{REMOTE_ROOT}/playbooks/connectivity.yml"),
            (AUTOMATION / "files/phase5-message.txt", f"{REMOTE_ROOT}/files/phase5-message.txt"),
        )
        for source, destination in assets:
            if not source.is_file():
                return {"ok": False, "message": f"Required project asset is missing: {source.name}",
                        "vm": connected["vm"], "steps": steps}
            upload = self.vagrant.upload(source, destination)
            steps.append(self._step(f"Upload {source.name}", upload))
            if upload.exit_code != 0 or upload.timed_out:
                return {"ok": False, "message": f"File transfer failed: {source.name}",
                        "vm": connected["vm"], "steps": steps}
        return {"ok": True, "message": "Ansible and approved files are ready in the guest.",
                "vm": connected["vm"], "steps": steps}

    def validate(self) -> dict:
        prepared = self.prepare()
        if not prepared["ok"]:
            return prepared
        command = (
            "cd /tmp/captex-phase5 && "
            "ANSIBLE_NOCOLOR=1 ANSIBLE_HOST_KEY_CHECKING=False "
            "ansible-playbook -i inventory.ini playbooks/connectivity.yml"
        )
        result = self.vagrant.guest_command(command, timeout=300)
        prepared["steps"].append(self._step("Run connectivity playbook", result))
        prepared["ok"] = result.exit_code == 0 and not result.timed_out and "CAPTEX_ANSIBLE_OK" in result.stdout
        prepared["message"] = ("Ansible validation succeeded and returned CAPTEX_ANSIBLE_OK."
                               if prepared["ok"] else "Ansible playbook failed or returned unexpected output.")
        prepared["result"] = result.to_dict()
        return prepared
