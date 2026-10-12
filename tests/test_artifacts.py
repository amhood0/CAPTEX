"""Managed artifact upload, archive safety, selection, and deletion tests."""
from io import BytesIO
import zipfile

import pytest

from app.main import app
from app.routers.artifacts import get_artifact_store
from app.services.artifacts import ArtifactError, ArtifactStore


def archive(entries):
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as zipped:
        for name, contents in entries.items():
            zipped.writestr(name, contents)
    return output.getvalue()


def test_import_flattens_one_root_and_resolves_opaque_id(tmp_path):
    store = ArtifactStore(tmp_path / "artifacts")
    source = tmp_path / "demo.zip"
    source.write_bytes(archive({"demo/run.py": "print('ok')", "demo/readme.txt": "demo"}))
    imported = store.import_zip(source, "demo.zip")
    assert imported["id"].startswith("managed:")
    resolved = store.resolve(imported["id"])
    assert (resolved / "run.py").read_text() == "print('ok')"
    assert imported in store.list()


@pytest.mark.parametrize("name", ["../escape.py", "/absolute.py", "C:/windows.py"])
def test_import_rejects_unsafe_paths(tmp_path, name):
    store = ArtifactStore(tmp_path / "artifacts")
    source = tmp_path / "unsafe.zip"
    source.write_bytes(archive({name: "bad"}))
    with pytest.raises(ArtifactError):
        store.import_zip(source, "unsafe.zip")
    assert not list((tmp_path / "artifacts").glob("[!.]*"))


def test_upload_api_and_referenced_delete_protection(client, db, tmp_path):
    store = ArtifactStore(tmp_path / "artifacts")
    app.dependency_overrides[get_artifact_store] = lambda: store
    try:
        response = client.post("/api/artifacts", content=archive({"run.py": "print('ok')"}),
                               headers={"X-CAPTEX-Filename": "my%20tool.zip", "Content-Type": "application/zip"})
        assert response.status_code == 201
        artifact = response.json()
        assert artifact["name"] == "my tool"
        capability = client.post("/api/capabilities", json={"name": "Upload", "category": "Test"}).json()
        version = client.post(f"/api/capabilities/{capability['id']}/versions", json={
            "capability_id": capability["id"], "version": "1", "artifact_path": artifact["id"],
            "execution_command": "python3 run.py",
        })
        assert version.status_code == 200
        artifact_id = artifact["id"].split(":", 1)[1]
        assert client.delete(f"/api/artifacts/{artifact_id}").status_code == 409
        assert client.get("/api/artifacts").status_code == 200
        assert client.post("/api/artifacts", content=b"bad", headers={"X-CAPTEX-Filename": "bad.zip"}).status_code == 400
    finally:
        app.dependency_overrides.pop(get_artifact_store, None)


def test_combined_capability_creation_is_atomic(client, db):
    payload = {"name": "Combined", "category": "Test", "initial_version": {
        "version": "1", "artifact_path": "bundled:phase6-demo", "execution_command": "python3 run.py"}}
    response = client.post("/api/capabilities/with-version", json=payload)
    assert response.status_code == 201 and len(response.json()["versions"]) == 1
    invalid = {"name": "Must not remain", "category": "Test", "initial_version": {
        "version": "1", "artifact_path": "managed:missing", "execution_command": "python3 run.py"}}
    assert client.post("/api/capabilities/with-version", json=invalid).status_code == 400
    from app.models import Capability
    assert db.query(Capability).filter_by(name="Must not remain").first() is None


def test_combined_capability_creation_is_atomic(client):
    payload = {"name": "Combined", "category": "Tool", "description": "One workflow", "active": True,
               "initial_version": {"version": "1.0", "artifact_path": "bundled:phase6-demo",
                                   "entry_point": "run.py", "execution_command": "python3 run.py"}}
    response = client.post("/api/capabilities/with-version", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Combined" and body["versions"][0]["artifact_path"] == "bundled:phase6-demo"
    invalid = payload | {"name": "Not persisted", "initial_version": payload["initial_version"] | {"artifact_path": "managed:missing"}}
    assert client.post("/api/capabilities/with-version", json=invalid).status_code == 400
    assert all(item["name"] != "Not persisted" for item in client.get("/api/capabilities").json())
