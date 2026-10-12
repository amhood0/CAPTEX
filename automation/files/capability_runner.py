"""Fixed guest runner: execute an argv list and emit bounded structured results."""
import json
from pathlib import Path
import subprocess
import sys
import time


def bounded(value):
    return value[-65536:]


def main():
    manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    root = Path(manifest["artifact_root"]).resolve()
    results = []
    for case in manifest["cases"]:
        started = time.monotonic()
        try:
            completed = subprocess.run(
                manifest["argv"], cwd=root, stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=case["timeout"], shell=False,
            )
            stdout, stderr, exit_code = bounded(completed.stdout), bounded(completed.stderr), completed.returncode
            kind, expected = case["test_type"], case.get("expected_result") or ""
            if kind == "exit_code":
                try:
                    wanted = int(expected)
                    passed, actual = exit_code == wanted, str(exit_code)
                except ValueError:
                    passed, actual = False, str(exit_code)
                    stderr = bounded(stderr + "\nInvalid expected exit code")
            elif kind == "stdout_contains":
                passed, actual = expected in stdout, stdout
            else:
                candidate = (root / expected).resolve()
                allowed = candidate == root or root in candidate.parents
                passed, actual = allowed and candidate.is_file(), str(candidate) if allowed else "Path leaves artifact directory"
            status, notes = ("PASS" if passed else "FAIL"), None
        except subprocess.TimeoutExpired as error:
            stdout = bounded((error.stdout or b"").decode(errors="replace") if isinstance(error.stdout, bytes) else error.stdout or "")
            stderr = bounded((error.stderr or b"").decode(errors="replace") if isinstance(error.stderr, bytes) else error.stderr or "")
            exit_code, actual, status, notes = None, "Timed out", "ERROR", f"Timed out after {case['timeout']} seconds"
        except (OSError, ValueError) as error:
            stdout, stderr, exit_code, actual, status, notes = "", str(error), None, "Execution error", "ERROR", str(error)
        results.append({"test_case_id": case["id"], "status": status, "actual_result": bounded(actual),
                        "stdout": stdout, "stderr": stderr, "exit_code": exit_code,
                        "duration": int((time.monotonic() - started) * 1000), "notes": notes})
    payload = json.dumps(results, separators=(",", ":"))
    Path(sys.argv[2]).write_text(payload, encoding="utf-8")
    print("CAPTEX_RESULTS_READY")


if __name__ == "__main__":
    main()
