import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from app.config import config
from app import auth, database as db
from app.main import app, attempts
from app.agent import agent

@pytest.fixture
def environment(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'database_path', str(tmp_path/'test.sqlite3'))
    monkeypatch.setattr(config, 'authorized_roots', str(tmp_path/'workspace'))
    monkeypatch.setattr(auth, 'SETUP_FILE', tmp_path/'setup-key.txt')
    agent.current = None
    attempts.clear()
    with TestClient(app, base_url='http://127.0.0.1:8765') as client:
        yield client, tmp_path

@pytest.fixture
def client(environment):
    client, tmp_path = environment
    client.headers.update({'Origin':'http://127.0.0.1:8765','X-Local-App':'1'})
    response = client.post('/api/auth/login', json={'password':'test-password-123!', 'setup_key':auth.SETUP_FILE.read_text()})
    assert response.status_code == 200
    client.headers['X-CSRF-Token'] = response.json()['csrf']
    return client
