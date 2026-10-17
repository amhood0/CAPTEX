"""Verify a harmless child stays running, then terminate and reap it."""
import subprocess
import sys


def main():
    child = None
    running = False
    try:
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            child.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            running = child.poll() is None
        if not running:
            print("FAIL: child exited before the process check", file=sys.stderr)
    except OSError as error:
        print(f"FAIL: could not start child: {error}", file=sys.stderr)
    finally:
        if child is not None:
            if child.poll() is None:
                child.terminate()
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=2)

    if running:
        print("PASS: child process was running and has been stopped")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
