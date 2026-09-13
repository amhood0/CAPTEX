"""Regression coverage"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app import models


def seed(client):
    def create(path, data):
        response = client.post("/api" + path, json=data)
        assert response.status_code == 200, response.text
        return response.json()["id"]
    cap = create("/capabilities", {"name": "<script>alert(1)</script>", "category": "Test"})
    version = create(f"/capabilities/{cap}/versions", {"capability_id": cap, "version": "1", "entry_point": "main.py"})
    plan = create("/test-plans", {"capability_id": cap, "name": "Plan"})
    case = create(f"/test-plans/{plan}/test-cases", {"test_plan_id": plan, "name": "Case", "test_type": "exit_code"})
    env = create("/environments", {"name": "Ubuntu", "os": "Ubuntu"})
    run = create("/test-runs", {"capability_version_id": version, "test_plan_id": plan, "environment_id": env})
    result = create(f"/test-runs/{run}/results", {"test_run_id": run, "test_case_id": case, "status": "PASS", "stdout": "<script>alert(1)</script>"})
    return cap, version, plan, case, env, run, result


def test_populated_pages_and_escaping(client):
    cap, version, plan, case, env, run, result = seed(client)
    for path in ["/dashboard", "/capabilities", f"/capabilities/{cap}", "/environments",
                 "/test-plans", f"/test-plans/{plan}", "/test-runs", f"/test-runs/{run}",
                 f"/capabilities/{cap}/edit", f"/capabilities/{cap}/versions/{version}/edit"]:
        response = client.get(path)
        assert response.status_code == 200, path
        assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;" in client.get("/capabilities").text
    assert "Ubuntu" in client.get(f"/test-runs/{run}").text


@pytest.mark.parametrize("path", ["/capabilities/999", "/test-runs/999", "/test-plans/999", "/capabilities/999/edit", "/capabilities/999/versions/999/edit"])
def test_missing_pages(client, path):
    assert client.get(path).status_code == 404


def test_preserve_run_history(client):
    cap, version, plan, case, env, run, result = seed(client)
    for path in [f"/capabilities/{cap}", f"/capabilities/{cap}/versions/{version}",
                 f"/test-plans/{plan}", f"/test-cases/{case}", f"/environments/{env}"]:
        assert client.delete("/api" + path).status_code == 409
    assert client.get(f"/api/test-results/{result}").status_code == 200


def test_relationship_validation(client):
    cap, version, plan, case, env, run, result = seed(client)
    other = client.post("/api/capabilities", json={"name": "Other", "category": "Test"}).json()["id"]
    other_plan = client.post("/api/test-plans", json={"capability_id": other, "name": "Other"}).json()["id"]
    response = client.post("/api/test-runs", json={"capability_version_id": version, "test_plan_id": other_plan, "environment_id": env})
    assert response.status_code == 400
    other_case = client.post(f"/api/test-plans/{other_plan}/test-cases", json={"test_plan_id": other_plan, "name": "Other", "test_type": "exit_code"}).json()["id"]
    assert client.post(f"/api/test-runs/{run}/results", json={"test_run_id": run, "test_case_id": other_case, "status": "PASS"}).status_code == 400
    assert client.post(f"/api/capabilities/{cap}/versions", json={"capability_id": other, "version": "2"}).status_code == 400


@pytest.mark.parametrize("value", [None, "", "x" * 256])
def test_invalid_update(client, value):
    cap = client.post("/api/capabilities", json={"name": "Example", "category": "Test"}).json()["id"]
    assert client.put(f"/api/capabilities/{cap}", json={"name": value}).status_code == 422
    assert client.get(f"/api/capabilities/{cap}").json()["name"] == "Example"


def test_version_partial_update_and_uniqueness(client):
    cap, version, *_ = seed(client)
    endpoint = f"/api/capabilities/{cap}/versions"
    response = client.put(f"{endpoint}/{version}", json={"description": "Updated"})
    assert response.status_code == 200
    assert response.json()["entry_point"] == "main.py"
    client.post(endpoint, json={"capability_id": cap, "version": "2"})
    assert client.put(f"{endpoint}/{version}", json={"version": "2"}).status_code == 409


def test_foreign_keys_enforced(db):
    assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1
    db.add(models.CapabilityVersion(capability_id=999, version="1"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_result_and_test_type_validation(client):
    cap, version, plan, case, env, run, result = seed(client)
    assert client.put(f"/api/test-cases/{case}", json={"timeout": -1}).status_code == 422
    assert client.put(f"/api/test-cases/{case}", json={"test_type": "arbitrary"}).status_code == 422
    assert client.put(f"/api/test-results/{result}", json={"status": "arbitrary"}).status_code == 422
    assert client.put(f"/api/test-runs/{run}?status=arbitrary").status_code == 422
