"""
Tests for health check endpoint.
"""
import pytest
from flask import Flask

from app.main import create_app


@pytest.fixture
def app() -> Flask:
    """Create Flask app for testing."""
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app: Flask):
    """Create test client."""
    return app.test_client()


def test_health_endpoint(client):
    """Test that health endpoint returns correct response."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["message"] == "hello from flask"


