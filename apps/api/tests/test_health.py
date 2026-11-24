from fastapi.testclient import TestClient

from app.main import app
from app.schemas import HealthResponse


def test_health_returns_ok_shape():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    body = HealthResponse.model_validate(response.json())
    assert body.status == "ok"
    assert body.service == "pulsar-api"
    assert set(response.json()) == {"status", "service", "demo_mode"}
