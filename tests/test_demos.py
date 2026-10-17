"""Ready-to-run demos, durable initialization, and normal run workflow."""
import json
import os
import shutil
import subprocess
import sys
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.main import app
from app.migrate import migrate
from app.models import Capability, CapabilityVersion, TestRun as Run
from app.routers.automated_runs import get_automated_run_manager
from app.services.demos import seed_demos
from app.runtime import register_managed_environment


def test_initialization_preserves_edits_and_deletions(tmp_path):
    url = f"sqlite:///{tmp_path / 'demos.db'}"
    migrate(url)
    engine = create_engine(url)
    with Session(engine) as db:
        assert db.query(Capability).count() == 4
        assert db.query(CapabilityVersion).count() == 5
        assert db.query(Run).count() == 0
        db.query(Capability).filter_by(name="Text Summary").one().description = "User edit"
        db.delete(db.query(Capability).filter_by(name="File Creation").one())
        db.commit()
    migrate(url)
    with Session(engine) as db:
        assert db.query(Capability).count() == 3
        assert db.query(Capability).filter_by(name="Text Summary").one().description == "User edit"
    engine.dispose()


def test_existing_name_is_not_overwritten(db):
    db.add(Capability(name="Text Summary", category="User", description="Keep"))
    db.commit()
    seed_demos(db)
    db.commit()
    existing = db.query(Capability).filter_by(name="Text Summary").one()
    assert existing.description == "Keep" and not existing.versions


def test_examples_use_normal_workflow(client, db):
    seed_demos(db)
    db.commit()
    environment = register_managed_environment(db)
    assert 'data-demo-url' not in client.get('/dashboard').text
    assert 'Text Summary' in client.get('/capabilities').text
    assert 'Text Summary checks' in client.get('/test-plans').text
    assert 'Text Summary' in client.get('/test-runs/new').text
    submitted = []
    app.dependency_overrides[get_automated_run_manager] = lambda: SimpleNamespace(
        submit_run=lambda run_id: {'test_run_id': run_id, 'status': 'running'})
    try:
        for version in db.query(CapabilityVersion).all():
            plan = version.capability.test_plans[0]
            response = client.post('/api/test-runs', json={
                'capability_version_id': version.id, 'test_plan_id': plan.id,
                'environment_id': environment.id})
            assert response.status_code == 200, response.text
            run_id = response.json()['id']
            assert db.get(Run, run_id).test_results
            assert client.post(f'/api/test-runs/{run_id}/execute').status_code == 202
            submitted.append(run_id)
        assert len(submitted) == 5
    finally:
        app.dependency_overrides.pop(get_automated_run_manager, None)


def test_seeded_checks_match_real_artifacts(db, tmp_path):
    seed_demos(db)
    db.commit()
    for index, version in enumerate(db.query(CapabilityVersion).all()):
        plan = version.capability.test_plans[0]
        artifact = version.artifact_path.removeprefix('bundled:')
        target = tmp_path / artifact
        shutil.copytree(BASE_DIR / 'capability_artifacts' / artifact, target)
        cases = sorted(plan.test_cases, key=lambda case: case.execution_order)
        manifest = {'artifact_root': str(target), 'argv': [sys.executable, 'run.py'], 'cases': [
            {'id': case.id, 'test_type': case.test_type, 'expected_result': case.expected_result,
             'timeout': case.timeout} for case in cases]}
        source, output = tmp_path / f'{index}.json', tmp_path / f'{index}-results.json'
        source.write_text(json.dumps(manifest))
        subprocess.run([sys.executable, str(BASE_DIR / 'automation/files/capability_runner.py'),
                        str(source), str(output)], check=True, capture_output=True, timeout=30)
        statuses = [item['status'] for item in json.loads(output.read_text())]
        assert statuses == (['PASS', 'FAIL', 'PASS'] if artifact.endswith('broken') else ['PASS'] * len(cases))


def test_source_launch_initializes_demos(tmp_path):
    environment = dict(os.environ, DATABASE_URL=f"sqlite:///{tmp_path / 'launch.db'}",
                       CAPTEX_DATA_DIR=str(tmp_path / 'data'))
    code = "from fastapi.testclient import TestClient\nfrom app.main import app\nwith TestClient(app) as client:\n assert len(client.get('/api/capabilities').json()) == 4\n assert len(client.get('/api/test-plans').json()) == 4\n assert 'data-demo-url' not in client.get('/dashboard').text\n"
    subprocess.run([sys.executable, '-c', code], env=environment, check=True, capture_output=True, timeout=30)
