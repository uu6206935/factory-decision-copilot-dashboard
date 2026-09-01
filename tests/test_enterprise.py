from pathlib import Path

from fastapi.testclient import TestClient

from app.data_quality import run_data_quality
from app.main import app
from app.provenance import build_file_catalog

client = TestClient(app)


def test_enterprise_endpoints():
    assert client.get('/healthz').status_code == 200
    ready = client.get('/readyz').json()
    assert ready['ready'] is True
    catalog = client.get('/api/v1/catalog')
    assert catalog.status_code == 200
    assert catalog.json()['files']
    dq = client.get('/api/v1/data-quality').json()
    assert dq['status'] == 'pass'
    r = client.post('/api/v1/analyze', json={'question':'QV-017の品質NG原因を調べて','use_llm':False})
    assert r.status_code == 200
    assert r.json()['candidates'][0]['label'].startswith('EQ-R03')
    assert r.json()['case_id'] >= 1
    assert client.get('/api/v1/cases').json()['items']
    assert client.get('/api/v1/audit').json()['items']
    assert client.get('/metrics').status_code == 200


def test_provenance_and_quality():
    data = Path(__file__).resolve().parents[1] / 'sample_data'
    catalog = build_file_catalog(data)
    assert len(catalog) >= 7
    assert all(x.get('sha256') for x in catalog if x['allowed'])
    dq = run_data_quality(data)
    assert dq['status'] == 'pass'
