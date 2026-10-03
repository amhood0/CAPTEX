"""Bounded Vagrant commands for the single approved VMware environment."""
from dataclasses import asdict, dataclass
import csv
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from app.config import BASE_DIR

TEMPLATE = BASE_DIR / "environments" / "ubuntu24"
BOX = "bento/ubuntu-24.04"
BOX_VERSION = "202510.26.0"
PROVIDER = "vmware_desktop"


@dataclass
class CommandResult:
    command: list[str]
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False

    def to_dict(self):
        return asdict(self)


class VagrantService:
    def __init__(self, runner=None):
        self.runner = runner or self.run_command

    def run_command(self, args: list[str], timeout: int = 60) -> CommandResult:
        """Use argument arrays and retain at most 64 KiB of each output stream."""
        environment = os.environ.copy()
        environment.update(VAGRANT_CWD=str(TEMPLATE), VAGRANT_VAGRANTFILE="Vagrantfile",
                           VAGRANT_DEFAULT_PROVIDER=PROVIDER, VAGRANT_CHECKPOINT_DISABLE="1", VAGRANT_NO_COLOR="1")
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            try:
                process = subprocess.Popen(args, cwd=TEMPLATE, env=environment, stdin=subprocess.DEVNULL,
                    stdout=out, stderr=err, shell=False, creationflags=flags,
                    start_new_session=os.name != "nt")
            except OSError as error:
                return CommandResult(args, None, "", str(error))
            timed_out = False
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                if os.name == "nt":
                    subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                                   capture_output=True, timeout=15, creationflags=flags)
                else:
                    import signal
                    os.killpg(process.pid, signal.SIGKILL)
                process.kill()
                process.wait(timeout=15)
            def tail(stream):
                length = stream.tell()
                stream.seek(max(0, length - 65536))
                return ("[Earlier output truncated]\n" if length > 65536 else "") + stream.read().decode("utf-8", errors="replace")
            return CommandResult(args, process.returncode, tail(out), tail(err), timed_out)

    def command(self, *args, timeout=60):
        executable = shutil.which("vagrant")
        if not executable:
            return CommandResult(["vagrant", *args], None, "", "Vagrant is not installed or not on PATH")
        return self.runner([executable, *args], timeout=timeout)

    def readiness(self) -> dict:
        checks = []
        version = self.command("--version")
        checks.append(dict(name="Vagrant", ready=version.exit_code == 0, detail=version.stdout.strip() or version.stderr,
                           action="Install Vagrant, then restart the application."))
        vmware = next((path for path in [Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "VMware/VMware Workstation/vmrun.exe",
                         Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "VMware/VMware Workstation/vmrun.exe"] if path.is_file()), None)
        checks.append(dict(name="VMware Workstation", ready=vmware is not None, detail=str(vmware or "Not found in standard installation locations"), action="Install VMware Workstation."))
        utility = self.runner(["sc.exe", "query", "VagrantVMware"], timeout=30) if os.name == "nt" else CommandResult([], None, "", "Windows host required")
        checks.append(dict(name="VMware Utility service", ready=utility.exit_code == 0 and bool(re.search(r"STATE\s*:\s*4\b", utility.stdout)), detail=utility.stdout or utility.stderr,
                           action="Install Vagrant VMware Utility and start its VagrantVMware service."))
        plugins = self.command("plugin", "list")
        checks.append(dict(name="VMware provider plugin", ready=plugins.exit_code == 0 and bool(re.search(r"^vagrant-vmware-desktop\s+\(", plugins.stdout, re.M)), detail=plugins.stdout or plugins.stderr,
                           action="Run: vagrant plugin install vagrant-vmware-desktop"))
        boxes = self.command("box", "list")
        box_ready = boxes.exit_code == 0 and any(bool(re.search(r"^" + re.escape(BOX) + r"\s+\(" + PROVIDER + r",\s*" + re.escape(BOX_VERSION) + r"(?:,|\))", line)) and "arm64" not in line for line in boxes.stdout.splitlines())
        checks.append(dict(name="Pinned Ubuntu box", ready=box_ready, detail=boxes.stdout or boxes.stderr,
                           action=f"Run: vagrant box add {BOX} --provider {PROVIDER} --box-version {BOX_VERSION}"))
        checks.append(dict(name="Managed Vagrantfile", ready=(TEMPLATE / "Vagrantfile").is_file(), detail=str(TEMPLATE), action="Restore environments/ubuntu24/Vagrantfile from the project."))
        return dict(ready=all(check["ready"] for check in checks), checks=checks)

    def status(self) -> dict:
        result = self.command("status", "default", "--machine-readable")
        states = [row[3] for row in csv.reader(io.StringIO(result.stdout)) if len(row) >= 4 and row[1] == "default" and row[2] == "state"]
        providers = [row[3] for row in csv.reader(io.StringIO(result.stdout)) if len(row) >= 4 and row[1] == "default" and row[2] == "provider-name"]
        valid = result.exit_code == 0 and len(states) == 1 and (not providers or all(p == PROVIDER for p in providers))
        provider_state = states[0] if valid else "unknown"
        state = "poweroff" if provider_state == "not_running" else provider_state
        return dict(state=state, provider_state=provider_state, ok=valid, command=result.to_dict())

    def start(self) -> CommandResult:
        return self.command("up", "default", "--provider=" + PROVIDER, "--no-provision", timeout=900)

    def stop(self) -> CommandResult:
        return self.command("halt", "default", timeout=180)

    def bootstrap_ansible(self) -> CommandResult:
        """Run only the fixed guest bootstrap provisioner."""
        return self.command("provision", "default", "--provision-with", "ansible-bootstrap", timeout=900)

    def upload(self, source: Path, destination: str) -> CommandResult:
        """Upload one caller-approved project path to a fixed guest destination."""
        return self.command("upload", str(source.resolve()), destination, "default", timeout=120)

    def guest_command(self, command: str, timeout: int = 300) -> CommandResult:
        """Execute a service-owned command string through Vagrant SSH."""
        return self.command("ssh", "default", "-c", command, timeout=timeout)
