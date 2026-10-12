"""Bounded deployment and execution of project-owned capability artifacts."""
import json
from pathlib import Path
import shlex
import tempfile

from app.config import BASE_DIR
from app.services.ansible import AnsibleService
from app.services.artifacts import ArtifactStore


REMOTE = "/tmp/captex-phase6"


class CapabilityExecutionService:
    def __init__(self, ansible=None, artifacts=None):
        self.ansible = ansible or AnsibleService()
        self.vagrant = self.ansible.vagrant
        self.artifacts = artifacts or ArtifactStore()

    @staticmethod
    def argv(command):
        values = shlex.split(command or "", posix=True)
        if not values or len(values) > 32 or any("\x00" in value for value in values):
            raise ValueError("Execution command must contain 1 to 32 arguments")
        return values

    def execute(self, version, cases, progress=None):
        source, argv = self.artifacts.resolve(version.artifact_path), self.argv(version.execution_command)
        prepared = self.ansible.prepare()
        if not prepared["ok"]:
            return prepared
        if progress:
            progress("running", "Deploying the capability and executing its test cases")
        reset = self.vagrant.guest_command(f"rm -rf {REMOTE} && install -d -m 0750 {REMOTE}/artifact", timeout=60)
        prepared["steps"].append(self.ansible._step("Create capability staging directory", reset))
        if reset.exit_code != 0 or reset.timed_out:
            return {**prepared, "ok": False, "message": "Could not create the capability staging directory."}
        manifest = {"artifact_root": "/opt/captex/current", "argv": argv,
                    "cases": [{"id": result.test_case_id, "test_type": result.test_case.test_type,
                               "expected_result": result.expected_result, "timeout": max(1, min(result.test_case.timeout, 300))}
                              for result in cases]}
        with tempfile.TemporaryDirectory(prefix="captex-phase6-") as directory:
            manifest_path = Path(directory) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            assets = ((source, f"{REMOTE}/artifact/"),
                      (BASE_DIR / "automation/files/capability_runner.py", f"{REMOTE}/capability_runner.py"),
                      (BASE_DIR / "automation/playbooks/capability_test.yml", f"{REMOTE}/capability_test.yml"),
                      (manifest_path, f"{REMOTE}/manifest.json"))
            for item, destination in assets:
                upload = self.vagrant.upload(item, destination)
                prepared["steps"].append(self.ansible._step(f"Upload {item.name}", upload))
                if upload.exit_code != 0 or upload.timed_out:
                    return {**prepared, "ok": False, "message": f"Capability transfer failed: {item.name}"}
        command = (f"ANSIBLE_NOCOLOR=1 ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook "
                   f"-i {REMOTE}/../captex-phase5/inventory.ini {REMOTE}/capability_test.yml")
        executed = self.vagrant.guest_command(command, timeout=sum(manifest_case["timeout"] for manifest_case in manifest["cases"]) + 120)
        prepared["steps"].append(self.ansible._step("Run capability playbook", executed))
        if executed.exit_code != 0 or executed.timed_out:
            return {**prepared, "ok": False, "message": "Capability playbook execution failed."}
        collected = self.vagrant.guest_command(f"cat {REMOTE}/results.json", timeout=60)
        prepared["steps"].append(self.ansible._step("Collect structured results", collected))
        try:
            results = json.loads(collected.stdout)
        except (json.JSONDecodeError, TypeError):
            return {**prepared, "ok": False, "message": "The guest returned invalid structured results."}
        expected_ids = {case["id"] for case in manifest["cases"]}
        valid_statuses = {"PASS", "FAIL", "ERROR"}
        if (not isinstance(results, list) or len(results) != len(expected_ids)
                or any(not isinstance(item, dict) or item.get("status") not in valid_statuses
                       or not isinstance(item.get("duration"), int) or item["duration"] < 0
                       for item in results)
                or {item["test_case_id"] for item in results} != expected_ids):
            return {**prepared, "ok": False, "message": "The guest returned results for unexpected test cases."}
        return {**prepared, "ok": True, "message": "Capability tests executed and results returned.",
                "results": results, "result": executed.to_dict()}
