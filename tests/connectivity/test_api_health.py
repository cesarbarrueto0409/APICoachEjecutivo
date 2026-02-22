"""Tests for API health endpoints."""

import pytest
import requests


def test_api_health_endpoint(test_config):
    """Test main health endpoint."""
    response = requests.get(f"{test_config['api_base_url']}/api/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_mongodb_health_endpoint(test_config):
    """Test MongoDB health endpoint."""
    response = requests.get(f"{test_config['api_base_url']}/api/health/mongodb")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"


def test_bedrock_health_endpoint(test_config):
    """Test AWS Bedrock health endpoint."""
    response = requests.get(f"{test_config['api_base_url']}/api/health/bedrock")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"


def test_sendgrid_health_endpoint(test_config):
    """Test SendGrid health endpoint."""
    response = requests.get(f"{test_config['api_base_url']}/api/health/sendgrid")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "configured"


def test_embedding_health_endpoint(test_config):
    """Test Embedding service health endpoint."""
    response = requests.get(f"{test_config['api_base_url']}/api/health/embedding")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["connected", "disabled", "not_configured"]
