"""Dashboard, filtering, pagination, and error handling checks."""
from datetime import datetime
from html import unescape
import re
import pytest
from app.models import TestRun as Run
from app.services.statistics import run_statistics
from tests.test_regressions import seed


def test_dashboard_excludes_unfinished_and_error_runs(client, db):
    cap, version, plan, case, env, run, result = seed(client)
    client.put(f"/api/test-runs/{run}?status=completed")
    for status, outcome in [("queued", None), ("running", None), ("failed", "ERROR"), ("completed", "FAIL")]:
        db.add(Run(capability_version_id=version, test_plan_id=plan, environment_id=env, status=status, overall_result=outcome))
    db.commit()
    stats = run_statistics(db)
    assert stats["total"] == 5
    assert stats["pass_rate"] == 50.0
    assert stats["queued"] == stats["active"] == stats["errors"] == 1
    assert stats["completed"] == 2
    assert run_statistics(db, cap) == stats
    assert run_statistics(db, 999)["pass_rate"] is None
    html = client.get("/dashboard").text
    assert "50.0%" in html and "finalized runs only" in html
    assert f"capability_id={cap}" in client.get(f"/capabilities/{cap}").text


def test_empty_dashboard(client):
    assert "Not available" in client.get("/dashboard").text


def test_history_pagination_retains_filters(client, db):
    cap, version, plan, case, env, run, result = seed(client)
    for _ in range(12):
        db.add(Run(capability_version_id=version, test_plan_id=plan, environment_id=env, status="queued", created_at=datetime(2026, 1, 5, 23, 59, 59)))
    db.commit()
    params = dict(q="Ubuntu", status="queued", capability_id=cap, environment_id=env,
                  date_from="2026-01-05", date_to="2026-01-05", page_size=10)
    response = client.get("/test-runs", params=params)
    assert response.status_code == 200
    assert "12 matching runs" in response.text
    assert response.text.count('>View</a>') == 10
    next_url = unescape(re.search(r'href="([^"]+)" class="btn btn-outline-primary">Next', response.text).group(1))
    second = client.get(next_url)
    assert second.text.count('>View</a>') == 2
    assert "Page 2 of 2" in second.text
    assert client.get("/test-runs", params={**params, "page": 999}).text.count('>View</a>') == 2
    api = client.get("/api/test-runs", params={**params, "skip": 10, "limit": 10})
    assert len(api.json()) == 2
    assert client.get("/api/test-runs", params={"capability_id": "999"}).json() == []
    assert client.get("/api/test-runs", params={"environment_id": "999"}).json() == []


@pytest.mark.parametrize("params", [{"date_from":"bad"}, {"date_from":"2026-02-02", "date_to":"2026-01-01"},
    {"status":"invalid"}, {"overall_result":"invalid"}, {"capability_id":"abc"}, {"environment_id":"-1"}, {"q":"x"*201}])
def test_invalid_filters_html_and_json(client, params):
    browser = client.get("/test-runs", params=params)
    assert browser.status_code == 422
    assert "text/html" in browser.headers["content-type"]
    api = client.get("/api/test-runs", params=params)
    assert api.status_code == 422
    assert "detail" in api.json()


@pytest.mark.parametrize("params", [{"page":0}, {"page":"bad"}, {"page_size":101}])
def test_invalid_pagination(client, params):
    response = client.get("/test-runs", params=params)
    assert response.status_code == 422
    assert "Invalid request" in response.text


def test_result_filter_and_complete_summary(client):
    *_, run, result = seed(client)
    html = client.get(f"/test-runs/{run}?result_status=PENDING").text
    assert "1 of 1 cases recorded" in html
    assert "No cases match" in html
    html = client.get(f"/test-runs/{run}?result_status=PASS").text
    assert "Full results and output" in html
    assert "&lt;script&gt;" in html
    assert client.get(f"/test-runs/{run}?result_status=INVALID").status_code == 422


def test_input_validation_and_text_preservation(client):
    assert client.post("/api/capabilities", json={"name":"   ", "category":"Test"}).status_code == 422
    assert client.post("/api/capabilities", json={"name":"Name", "category":"Test", "misspelled":True}).status_code == 422
    cap, version, plan, case, env, run, result = seed(client)
    assert client.put(f"/api/test-cases/{case}", json={"execution_order": -1}).status_code == 422
    assert client.put(f"/api/capabilities/{cap}", json={"name":"  Renamed  "}).json()["name"] == "Renamed"
    text = "  exact output\n"
    assert client.put(f"/api/test-results/{result}", json={"stdout":text}).json()["stdout"] == text
    assert client.get("/test-plans/999/edit").status_code == 404
    assert "Page not found" in client.get("/test-plans/999/edit").text
    assert client.get("/api/test-plans/999").json() == {"detail":"Test plan not found"}


def test_unexpected_errors_do_not_expose_details():
    from fastapi.testclient import TestClient
    from app.main import app
    original_routes = list(app.router.routes)
    def fail():
        raise RuntimeError("private database connection details")
    app.add_api_route("/test-error-page", fail)
    app.add_api_route("/api/test-error-page", fail)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            for path in ("/test-error-page", "/api/test-error-page"):
                response = client.get(path)
                assert response.status_code == 500
                assert "private database" not in response.text
                assert "server log" in response.text
            assert "text/html" in client.get("/test-error-page").headers["content-type"]
            assert "detail" in client.get("/api/test-error-page").json()
    finally:
        app.router.routes[:] = original_routes
