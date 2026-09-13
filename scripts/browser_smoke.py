"""Run the browser workflow against a disposable database and server.

Install requirements-browser.txt, then run: python -m scripts.browser_smoke
Uses the installed Microsoft Edge browser in headless mode.
"""
import os
import socket
import tempfile
import threading
import time
from pathlib import Path


def main():
    with tempfile.TemporaryDirectory(prefix="captex-browser-") as directory:
        os.environ["DATABASE_URL"] = f"sqlite:///{Path(directory) / 'browser.db'}"
        from app.config import settings
        from app.database import engine
        from app.main import app
        from app.migrate import migrate
        import httpx
        import uvicorn
        from playwright.sync_api import sync_playwright, expect
        migrate(settings.DATABASE_URL)
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if server.started:
                    break
                time.sleep(0.05)
            assert server.started, "Temporary server failed to start"
            base = f"http://127.0.0.1:{port}"
            with httpx.Client(base_url=base) as client:
                cap = client.post("/api/capabilities", json={"name": "Browser demo", "category": "Test"}).json()["id"]
                client.post(f"/api/capabilities/{cap}/versions", json={"capability_id": cap, "version": "1.0"}).raise_for_status()
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="msedge", headless=True)
                page = browser.new_page()
                page.set_default_timeout(10000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                # Phase 2 forms work even when the optional Bootstrap CDN is unavailable.
                page.route("https://cdn.jsdelivr.net/**", lambda route: route.abort())
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base + "/environments/new")
                page.get_by_label("Name", exact=True).fill("Browser Ubuntu")
                page.get_by_label("Operating system", exact=True).fill("Ubuntu")
                page.get_by_role("button", name="Save", exact=True).click()
                page.wait_for_url(base + "/environments")
                page.get_by_role("link", name="Edit", exact=True).click()
                page.get_by_label("Name", exact=True).fill("   ")
                page.get_by_role("button", name="Save", exact=True).click()
                expect(page.locator("#saveError")).to_contain_text("Must not be blank")
                page.get_by_label("Name", exact=True).fill("Browser Ubuntu")
                page.get_by_label("Description", exact=True).fill("Edited environment")
                page.get_by_role("button", name="Save", exact=True).click()
                page.wait_for_url(base + "/environments")
                expect(page.get_by_text("Edited environment", exact=True)).to_be_visible()
                page.goto(base + "/test-plans/new")
                page.get_by_label("Name", exact=True).fill("Browser plan")
                page.get_by_role("button", name="Save", exact=True).click()
                page.wait_for_url(base + "/test-plans")
                page.get_by_role("link", name="View", exact=True).click()
                plan_url = page.url
                page.get_by_role("link", name="Add test case", exact=True).click()
                page.get_by_label("Name", exact=True).fill("Exit check")
                page.get_by_label("Expected result", exact=True).fill("0")
                page.get_by_role("button", name="Save", exact=True).click()
                page.wait_for_url(plan_url)
                page.get_by_role("link", name="New manual run", exact=True).click()
                page.get_by_role("button", name="Create run", exact=True).click()
                page.wait_for_url("**/test-runs/*")
                expect(page.get_by_role("heading", name="Test Run #1", exact=True)).to_be_visible()
                page.get_by_role("button", name="Start manual run", exact=True).click()
                expect(page.get_by_text("running", exact=True)).to_be_visible()
                page.get_by_role("button", name="Complete run", exact=True).click()
                expect(page.locator("#actionError")).to_contain_text("Record a result for every case")
                page.get_by_role("link", name="Record / edit", exact=True).click()
                page.get_by_label("Outcome", exact=True).select_option("PASS")
                page.get_by_label("Actual result", exact=True).fill("0")
                page.get_by_label("Exit code", exact=True).fill("0")
                page.get_by_label("Duration (milliseconds)", exact=True).fill("0")
                page.get_by_role("button", name="Save", exact=True).click()
                page.wait_for_url(base + "/test-runs/1")
                page.get_by_role("button", name="Complete run", exact=True).click()
                expect(page.get_by_text("completed", exact=True)).to_be_visible()
                expect(page.get_by_role("link", name="Record / edit", exact=True)).to_have_count(0)
                page.goto(base + "/test-runs")
                page.get_by_label("Search capability, version, plan, or environment").fill("Browser Ubuntu")
                page.get_by_label("Outcome", exact=True).select_option("PASS")
                page.get_by_role("button", name="Filter", exact=True).click()
                expect(page.get_by_role("link", name="View", exact=True)).to_have_count(1)
                with httpx.Client(base_url=base) as client:
                    original = client.get("/api/test-runs/1").json()
                    for _ in range(12):
                        client.post("/api/test-runs", json={key: original[key] for key in ("capability_version_id", "test_plan_id", "environment_id")}).raise_for_status()
                page.goto(base + "/dashboard")
                expect(page.get_by_text("100.0%", exact=True)).to_be_visible()
                page.goto(base + "/test-runs")
                page.get_by_label("Status", exact=True).select_option("queued")
                page.get_by_label("Environment", exact=True).select_option(label="Browser Ubuntu")
                page.get_by_label("Runs per page").select_option("10")
                page.get_by_role("button", name="Filter", exact=True).click()
                expect(page.get_by_role("link", name="View", exact=True)).to_have_count(10)
                page.get_by_role("link", name="Next", exact=True).click()
                expect(page.get_by_role("link", name="View", exact=True)).to_have_count(2)
                expect(page.get_by_label("Status", exact=True)).to_have_value("queued")
                page.get_by_role("link", name="Previous", exact=True).click()
                expect(page.get_by_role("link", name="View", exact=True)).to_have_count(10)
                page.goto(base + "/test-plans/999/edit")
                expect(page.get_by_role("heading", name="404 - Page not found")).to_be_visible()
                assert not errors, errors
                browser.close()
            print("Browser workflow passed: environment edit, plan/case creation, manual run, results, completion, history pagination, dashboard statistics, and validation errors.")
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            listener.close()
            engine.dispose()


if __name__ == "__main__":
    main()
