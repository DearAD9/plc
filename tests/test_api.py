"""Unit and integration tests for FastAPI endpoints."""

from fastapi.testclient import TestClient
import pytest
from backend.main import app


@pytest.fixture
def client():
    # Use context manager so lifespan startup/shutdown execute
    with TestClient(app) as test_client:
        yield test_client


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert data["health_endpoint"] == "/api/health"


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["backend_running"] is True
    assert "plc_connected" in data
    assert "status" in data


def test_plc_status_endpoint(client):
    response = client.get("/api/plc/status")
    assert response.status_code == 200
    data = response.json()
    assert "ip" in data
    assert "rack" in data
    assert "slot" in data
    assert "connected" in data


def test_plc_variables_endpoint(client):
    response = client.get("/api/plc/variables")
    assert response.status_code == 200
    variables = response.json()
    assert isinstance(variables, list)
    assert len(variables) > 0
    assert variables[0]["name"] == "voltage"


def test_plc_data_endpoint(client):
    response = client.get("/api/plc/data")
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "plc_connected" in data
    assert "variables" in data
