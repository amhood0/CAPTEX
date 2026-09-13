"""Manual testing workflow and history regression tests."""
import pytest
from tests.test_regressions import seed


def test_manual_run_lifecycle(client):
    cap, version, plan, case, env, old_run, _ = seed(client)
    client.put(f"/api/test-cases/{case}", json={"expected_result": "original"})
    disabled = client.post(f"/api/test-plans/{plan}/test-cases", json={"test_plan_id": plan, "name": "Disabled", "test_type": "exit_code", "enabled": False}).json()
    run = client.post("/api/test-runs", json={"capability_version_id": version, "test_plan_id": plan, "environment_id": env}).json()
    assert len(run["test_results"]) == 1
    result = run["test_results"][0]
    assert result["status"] == "PENDING"
    client.put(f"/api/test-cases/{case}", json={"expected_result": "changed", "enabled": False})
    assert client.get(f"/api/test-results/{result['id']}").json()["expected_result"] == "original"
    endpoint = f"/api/test-runs/{run['id']}"
    assert client.put(endpoint + "?status=completed").status_code == 400
    assert client.put(endpoint + "?status=running").status_code == 200
    assert client.put(f"/api/test-results/{result['id']}", json={"status": "PASS", "actual_result": "original", "stdout": "ok", "exit_code": 0, "duration": 0}).status_code == 200
    completed = client.put(endpoint + "?status=completed").json()
    assert completed["overall_result"] == "PASS"
    assert completed["started_at"] and completed["completed_at"]
    assert completed["duration"] >= 0
    assert client.put(f"/api/test-results/{result['id']}", json={"status": "FAIL"}).status_code == 409
    assert client.delete(f"/api/test-results/{result['id']}").status_code == 409
    assert client.put(endpoint + "?status=running").status_code == 409
    history = client.get("/api/test-runs", params={"q": "Ubuntu", "overall_result": "PASS", "status": "completed"}).json()
    assert [r["id"] for r in history] == [run["id"]]
    assert client.get("/test-runs?q=Ubuntu&overall_result=PASS").status_code == 200


@pytest.mark.parametrize("outcomes,expected", [(["PASS", "FAIL"], "FAIL"), (["FAIL", "ERROR"], "ERROR"), (["PASS", "SKIPPED"], "PASS"), (["SKIPPED", "SKIPPED"], "ERROR")])
def test_overall_result(client, outcomes, expected):
    cap, version, plan, case, env, run, result = seed(client)
    client.post(f"/api/test-plans/{plan}/test-cases", json={"test_plan_id": plan, "name": "Second", "test_type": "exit_code"})
    run = client.post("/api/test-runs", json={"capability_version_id": version, "test_plan_id": plan, "environment_id": env}).json()
    for result, outcome in zip(run["test_results"], outcomes):
        client.put(f"/api/test-results/{result['id']}", json={"status": outcome})
    response = client.put(f"/api/test-runs/{run['id']}?status=completed")
    assert response.status_code == 200
    assert response.json()["overall_result"] == expected


def test_clear_result_does_not_remove_required_case(client):
    *_, run, result = seed(client)
    assert client.delete(f"/api/test-results/{result}").status_code == 200
    assert client.get(f"/api/test-results/{result}").json()["status"] == "PENDING"
    assert client.put(f"/api/test-runs/{run}?status=completed").status_code == 400


def test_forms_and_crud(client):
    cap, version, plan, case, env, run, result = seed(client)
    for path in ["/environments/new", f"/environments/{env}/edit", "/test-plans/new",
                 f"/test-plans/{plan}/edit", f"/test-plans/{plan}/cases/new", f"/test-cases/{case}/edit",
                 f"/test-results/{result}/edit", "/test-runs/new"]:
        response = client.get(path)
        assert response.status_code == 200, path
        assert '<script>alert(1)</script>' not in response.text
    assert client.put(f"/api/environments/{env}", json={"description": "Updated"}).status_code == 200
    assert client.put(f"/api/test-plans/{plan}", json={"description": "Updated"}).status_code == 200
    extra = client.post(f"/api/test-plans/{plan}/test-cases", json={"test_plan_id": plan, "name": "Extra", "test_type": "file_exists"}).json()
    assert client.delete(f"/api/test-cases/{extra['id']}").status_code == 200
    assert client.get("/api/test-runs?q=nonexistent").json() == []
    assert client.get("/api/test-runs?q=%25").json() == []


def test_inactive_plan_and_duplicate_result(client):
    cap, version, plan, case, env, run, result = seed(client)
    assert client.post(f"/api/test-runs/{run}/results", json={"test_run_id": run, "test_case_id": case, "status": "PASS"}).status_code == 409
    client.put(f"/api/test-plans/{plan}", json={"active": False})
    assert client.post("/api/test-runs", json={"capability_version_id": version, "test_plan_id": plan, "environment_id": env}).status_code == 400
    assert client.put(f"/api/test-runs/{run}?overall_result=PASS").status_code == 400


def test_missing_form_records(client):
    for path in ["/environments/999/edit", "/test-plans/999/edit", "/test-plans/999/cases/new", "/test-cases/999/edit", "/test-results/999/edit"]:
        assert client.get(path).status_code == 404


def test_empty_plan_rejected_and_failure_timed(client):
    cap, version, plan, case, env, run, result = seed(client)
    client.put(f"/api/test-cases/{case}", json={"enabled": False})
    assert client.post("/api/test-runs", json={"capability_version_id": version, "test_plan_id": plan, "environment_id": env}).status_code == 400
    response = client.put(f"/api/test-runs/{run}?status=failed")
    assert response.status_code == 200
    assert response.json()["overall_result"] == "ERROR"
    assert response.json()["completed_at"] is not None
    assert client.put(f"/api/test-results/{result}", json={"status": "PASS"}).status_code == 409
