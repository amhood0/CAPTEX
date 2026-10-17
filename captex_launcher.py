"""Windows launcher for the packaged local CAPTEX web application."""
import json
import logging
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request
import webbrowser
import os

from app.config import settings
from app.runtime import initialize_runtime


def running_url():
    url = f"http://{settings.HOST}:{settings.PORT}/health"
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            body = json.loads(response.read())
            return f"http://{settings.HOST}:{settings.PORT}/" if body.get("app") == settings.APP_NAME else None
    except (OSError, ValueError, urllib.error.URLError):
        return None


def open_when_ready(url):
    for _ in range(120):
        if running_url():
            if os.environ.get("CAPTEX_NO_BROWSER", "").lower() not in {"1", "true", "yes"}:
                webbrowser.open(url)
            return
        time.sleep(0.25)
    logging.error("Server did not become ready at %s", url)


def acquire_instance_lock():
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    handle = (settings.DATA_DIR / "runtime" / "launcher.lock").open("a+b")
    if handle.tell() == 0:
        handle.write(b"0"); handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return handle
    except OSError:
        handle.close()
        return None


def main():
    (settings.DATA_DIR / "runtime").mkdir(parents=True, exist_ok=True)
    instance_lock = acquire_instance_lock()
    if instance_lock is None:
        open_when_ready(f"http://{settings.HOST}:{settings.PORT}/")
        return
    try:
        initialize_runtime()
        dashboard = f"http://{settings.HOST}:{settings.PORT}/"
        existing = running_url()
        if existing:
            if os.environ.get("CAPTEX_NO_BROWSER", "").lower() not in {"1", "true", "yes"}:
                webbrowser.open(existing)
            return
        log_path = Path(settings.DATA_DIR) / "logs" / "captex.log"
        logging.basicConfig(filename=log_path, level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(name)s %(message)s")
        threading.Thread(target=open_when_ready, args=(dashboard,), daemon=True).start()
        import uvicorn
        from app.main import app
        config = uvicorn.Config(app, host=settings.HOST, port=settings.PORT, log_config=None)
        server = uvicorn.Server(config)
        app.state.request_shutdown = lambda: setattr(server, "should_exit", True)
        server.run()
    except Exception:
        logging.exception("CAPTEX could not start")
        if os.name == "nt" and os.environ.get("CAPTEX_NO_DIALOG", "").lower() not in {"1", "true", "yes"}:
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, f"CAPTEX could not start. See {settings.DATA_DIR / 'logs' / 'captex.log'}", "CAPTEX", 0x10)
            except Exception:
                pass
        raise
    finally:
        instance_lock.close()


if __name__ == "__main__":
    main()
