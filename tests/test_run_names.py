"""Plan context and editable run names preserve existing results."""
import json
import re

import pytest
from sqlalchemy import create_engine, text
from alembic import command
from app.migrate import migrate, migration_config
from tests.test_regressions import seed


def test_plan_context(client):
    cap, version, plan, *_ = seed(client)
    other = client.post('/api/test-plans', json={'capability_id': cap, 'name': 'Second plan'}).json()['id']
    client.post(f'/api/test-plans/{other}/test-cases', json={
        'test_plan_id': other, 'name': 'Check', 'test_type': 'exit_code'})
    page = client.get(f'/test-runs/new?plan_id={other}')
    assert page.status_code == 200
    selected = json.loads(re.search(r'const selected = (.*);', page.text).group(1))
    assert selected == {'capability_id': cap, 'plan_id': other}
    assert 'value="Second plan"' in page.text
    assert f'/test-runs/new?plan_id={other}' in client.get(f'/test-plans/{other}').text
    assert client.get('/test-runs/new?plan_id=99999').status_code == 404
    client.put(f'/api/test-plans/{other}', json={'active': False})
    assert client.get(f'/test-runs/new?plan_id={other}').status_code == 400


def test_name_creation_rename_and_history(client):
    cap, version, plan, case, env, old_run, _ = seed(client)
    created = client.post('/api/test-runs', json={'capability_version_id': version,
        'test_plan_id': plan, 'environment_id': env, 'name': '  Regression check  '})
    assert created.status_code == 200
    assert created.json()['name'] == 'Regression check'
    endpoint = f'/api/test-runs/{old_run}'
    client.put(endpoint + '?status=completed')
    before = client.get(endpoint).json()
    response = client.put(endpoint + '/name', json={'name': '<b>Release acceptance</b>'})
    assert response.status_code == 200
    assert response.json()['test_results'] == before['test_results']
    assert response.json()['status'] == 'completed'
    assert '&lt;b&gt;Release acceptance&lt;/b&gt;' in client.get(f'/test-runs/{old_run}').text
    assert client.get(f'/test-runs/{old_run}/edit').status_code == 200
    assert [run['id'] for run in client.get('/api/test-runs?q=Release acceptance').json()] == [old_run]
    assert client.put('/api/test-runs/99999/name', json={'name': 'Missing'}).status_code == 404


@pytest.mark.parametrize('name', ['', '   ', None, 'a' * 256])
def test_invalid_rename(client, name):
    *_, run, result = seed(client)
    assert client.put(f'/api/test-runs/{run}/name', json={'name': name}).status_code == 422


def test_upgrade_preserves_unnamed_runs(tmp_path):
    url = f"sqlite:///{tmp_path / 'older.db'}"
    command.upgrade(migration_config(url), '002_builtin_demos')
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO environments (id, name, os, created_at) VALUES (1, 'Manual', 'Ubuntu', CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO test_runs (capability_version_id, test_plan_id, environment_id, status, created_at) VALUES (1, 1, 1, 'completed', CURRENT_TIMESTAMP)"))
    migrate(url)
    with engine.connect() as db:
        assert db.execute(text('SELECT name, status FROM test_runs')).one() == (None, 'completed')
    engine.dispose()
