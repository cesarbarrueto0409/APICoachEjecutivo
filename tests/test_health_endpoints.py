"""Tests for health check endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from app.main import create_app
from app.config.settings import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = Mock(spec=Settings)
    settings.mongodb_uri = "mongodb://localhost:27017"
    settings.mongodb_database = "test_db"
    settings.aws_region = "us-east-1"
    settings.aws_bedrock_model_id = "test-model"
    settings.sendgrid_api_key = "SG.test_key"
    settings.sendgrid_from_email = "test@example.com"
    settings.sendgrid_test_email = "test@example.com"
    settings.api_host = "0.0.0.0"
    settings.api_port = 8000
    settings.validate = Mock()
    return settings


@pytest.fixture
def mock_mongodb_client():
    """Create mock MongoDB client."""
    client = Mock()
    client.query = Mock(return_value=[{"test": "data"}])
    return client


@pytest.fixture
def mock_bedrock_client():
    """Create mock AWS Bedrock client."""
    client = Mock()
    client.analyze = Mock(return_value={
        "analysis": "OK",
        "confidence": None,
        "metadata": {}
    })
    return client


@pytest.fixture
def client(mock_settings, mock_mongodb_client, mock_bedrock_client):
    """Create test client with mocked dependencies."""
    with patch('app.main.Settings', return_value=mock_settings):
        with patch('app.main.MongoDBClient', return_value=mock_mongodb_client):
            with patch('app.main.AWSBedrockClient', return_value=mock_bedrock_client):
                app = create_app()
                return TestClient(app)


def test_health_check(client):
    """Test general health check endpoint."""
    response = client.get("/api/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "AWS Bedrock API Service"


def test_health_check_mongodb_success(client, mock_mongodb_client):
    """Test MongoDB health check with successful connection."""
    response = client.get("/api/health/mongodb")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert data["message"] == "MongoDB connection is healthy"
    assert data["database"] == "test_db"
    
    # Verify query was called
    mock_mongodb_client.query.assert_called_once()


def test_health_check_mongodb_connection_error(client, mock_mongodb_client):
    """Test MongoDB health check with connection error."""
    # Mock connection error
    mock_mongodb_client.query.side_effect = ConnectionError("Connection refused")
    
    response = client.get("/api/health/mongodb")
    
    assert response.status_code == 503
    data = response.json()
    assert "MongoDB connection failed" in data["detail"]


def test_health_check_mongodb_general_error(client, mock_mongodb_client):
    """Test MongoDB health check with general error."""
    # Mock general error
    mock_mongodb_client.query.side_effect = Exception("Unexpected error")
    
    response = client.get("/api/health/mongodb")
    
    assert response.status_code == 500
    data = response.json()
    assert "MongoDB health check error" in data["detail"]


def test_health_check_bedrock_success(client, mock_bedrock_client):
    """Test AWS Bedrock health check with successful connection."""
    response = client.get("/api/health/bedrock")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert data["message"] == "AWS Bedrock connection is healthy"
    assert data["model"] == "test-model"
    assert data["region"] == "us-east-1"
    assert "test_response" in data
    
    # Verify analyze was called
    mock_bedrock_client.analyze.assert_called_once()


def test_health_check_bedrock_connection_error(client, mock_bedrock_client):
    """Test AWS Bedrock health check with connection error."""
    # Mock connection error
    mock_bedrock_client.analyze.side_effect = ConnectionError("Unable to connect")
    
    response = client.get("/api/health/bedrock")
    
    assert response.status_code == 503
    data = response.json()
    assert "AWS Bedrock connection failed" in data["detail"]


def test_health_check_bedrock_general_error(client, mock_bedrock_client):
    """Test AWS Bedrock health check with general error."""
    # Mock general error
    mock_bedrock_client.analyze.side_effect = Exception("Unexpected error")
    
    response = client.get("/api/health/bedrock")
    
    assert response.status_code == 500
    data = response.json()
    assert "AWS Bedrock health check error" in data["detail"]


def test_health_check_sendgrid_success(client):
    """Test SendGrid health check with proper configuration."""
    response = client.get("/api/health/sendgrid")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "configured"
    assert data["message"] == "SendGrid is properly configured"
    assert data["from_email"] == "test@example.com"
    assert data["test_email"] == "test@example.com"
    assert "note" in data


def test_health_check_sendgrid_missing_api_key(mock_settings, mock_mongodb_client, mock_bedrock_client):
    """Test SendGrid health check with missing API key."""
    # Create settings without API key
    mock_settings.sendgrid_api_key = ""
    
    with patch('app.main.Settings', return_value=mock_settings):
        with patch('app.main.MongoDBClient', return_value=mock_mongodb_client):
            with patch('app.main.AWSBedrockClient', return_value=mock_bedrock_client):
                app = create_app()
                client = TestClient(app)
                
                response = client.get("/api/health/sendgrid")
                
                assert response.status_code == 503
                data = response.json()
                assert "SendGrid API key not configured" in data["detail"]


def test_health_check_sendgrid_missing_from_email(mock_settings, mock_mongodb_client, mock_bedrock_client):
    """Test SendGrid health check with missing from_email."""
    # Create settings without from_email
    mock_settings.sendgrid_from_email = ""
    
    with patch('app.main.Settings', return_value=mock_settings):
        with patch('app.main.MongoDBClient', return_value=mock_mongodb_client):
            with patch('app.main.AWSBedrockClient', return_value=mock_bedrock_client):
                app = create_app()
                client = TestClient(app)
                
                response = client.get("/api/health/sendgrid")
                
                assert response.status_code == 503
                data = response.json()
                assert "SendGrid from_email not configured" in data["detail"]


def test_all_health_endpoints_accessible(client):
    """Test that all health endpoints are accessible."""
    endpoints = [
        "/api/health",
        "/api/health/mongodb",
        "/api/health/bedrock",
        "/api/health/sendgrid"
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        # Should return 200 or 503, but not 404
        assert response.status_code in [200, 503]
        assert response.status_code != 404
