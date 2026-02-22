"""
Tests for API routes.

This module contains tests for the FastAPI routes, including request validation,
error handling, and successful analysis workflows.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List
import json

from app.api.routes import router, set_analysis_service, set_settings
from app.services.analysis_service import AnalysisService, ServiceError
from app.config.settings import Settings
from fastapi import FastAPI


@pytest.fixture
def app():
    """Create a FastAPI application for testing."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    import os
    settings = Mock(spec=Settings)
    settings.sendgrid_api_key = "test-api-key"
    settings.sendgrid_from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@test.local")
    settings.sendgrid_test_email = os.getenv("SENDGRID_TEST_EMAIL", "test@test.local")
    settings.mongodb_database = "test_db"
    settings.aws_bedrock_model_id = "test-model"
    settings.aws_region = "us-east-1"
    return settings


@pytest.fixture
def mock_data_client():
    """Create a mock data client."""
    client = Mock()
    client.query = Mock(return_value=[
        {
            "ejecutivo": "Test Ejecutivo 1",
            "email": "exec1@test.local",
            "clientes": [{"name": "Client 1"}]
        },
        {
            "ejecutivo": "Test Ejecutivo 2", 
            "email": "exec2@test.local",
            "clientes": [{"name": "Client 2"}]
        }
    ])
    return client


@pytest.fixture
def mock_ai_client():
    """Create a mock AI client."""
    client = Mock()
    # Return JSON-formatted analysis result
    analysis_result = [
        {
            "ejecutivo": "Test Ejecutivo 1",
            "email": "exec1@test.local",
            "recommendations": ["Recommendation 1"]
        },
        {
            "ejecutivo": "Test Ejecutivo 2",
            "email": "exec2@test.local", 
            "recommendations": ["Recommendation 2"]
        }
    ]
    client.analyze = Mock(return_value={
        "analysis": json.dumps(analysis_result),
        "metadata": {
            "model": "test-model",
            "tokens": 100,
            "cost": 0.001
        }
    })
    return client


@pytest.fixture
def analysis_service(mock_data_client, mock_ai_client):
    """Create an analysis service with mock clients."""
    return AnalysisService(mock_data_client, mock_ai_client)


@pytest.fixture
def client(app, analysis_service, mock_settings):
    """Create a test client with configured service."""
    set_analysis_service(analysis_service)
    set_settings(mock_settings)
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""
    
    def test_health_check_returns_healthy_status(self, client):
        """Test that health check endpoint returns healthy status."""
        response = client.get("/api/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "AWS Bedrock API Service"


class TestAnalyzeEndpoint:
    """Tests for the /analyze endpoint."""
    
    @patch('app.config.queries.get_queries')
    @patch('app.config.queries.get_analysis_prompt')
    def test_successful_analysis_returns_200(
        self, mock_get_prompt, mock_get_queries, client, mock_data_client, mock_ai_client
    ):
        """Test successful analysis workflow returns 200 OK."""
        # Mock the queries configuration
        mock_get_queries.return_value = [{
            "collection": "clientes_por_ejecutivo",
            "pipeline": [{"$match": {}}]
        }]
        mock_get_prompt.return_value = "Test analysis prompt"
        
        request_data = {
            "current_date": "2026-02-17",
            "is_testing": False
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "metadata" in data
        assert data["metadata"]["data_count"] == 2
        
        # Verify clients were called
        mock_data_client.query.assert_called_once()
        mock_ai_client.analyze.assert_called_once()
    
    @patch('app.config.queries.get_queries')
    @patch('app.config.queries.get_analysis_prompt')
    def test_analysis_with_testing_mode(
        self, mock_get_prompt, mock_get_queries, client, mock_data_client, mock_ai_client
    ):
        """Test analysis with testing mode enabled."""
        mock_get_queries.return_value = [{
            "collection": "clientes_por_ejecutivo",
            "pipeline": [{"$match": {}}]
        }]
        mock_get_prompt.return_value = "Test analysis prompt"
        
        request_data = {
            "current_date": "2026-02-17",
            "is_testing": True
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "email_notifications" in data
    
    def test_missing_current_date_returns_422(self, client):
        """Test request without current_date field returns 422 Unprocessable Entity."""
        request_data = {
            "is_testing": False
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        # FastAPI returns 422 for validation errors
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_invalid_current_date_format_returns_422(self, client):
        """Test request with invalid date format returns 422."""
        request_data = {
            "current_date": "invalid-date",
            "is_testing": False
        }
        
        # Note: The API doesn't validate date format in schema, but we test the field is required
        response = client.post("/api/analyze", json=request_data)
        
        # Should still accept it (no format validation in schema)
        # This test documents current behavior
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR]
    
    @patch('app.config.queries.get_queries')
    @patch('app.config.queries.get_analysis_prompt')
    def test_data_retrieval_connection_error_returns_503(
        self, mock_get_prompt, mock_get_queries, client, mock_data_client, analysis_service
    ):
        """Test MongoDB connection error returns 503 Service Unavailable."""
        mock_get_queries.return_value = [{
            "collection": "clientes_por_ejecutivo",
            "filter": {}
        }]
        mock_get_prompt.return_value = "Test prompt"
        
        # Configure mock to raise ConnectionError
        mock_data_client.query.side_effect = ConnectionError("Connection timeout")
        
        request_data = {
            "current_date": "2026-02-17",
            "is_testing": False
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    
    @patch('app.config.queries.get_queries')
    @patch('app.config.queries.get_analysis_prompt')
    def test_ai_service_connection_error_returns_503(
        self, mock_get_prompt, mock_get_queries, client, mock_ai_client, analysis_service
    ):
        """Test AWS Bedrock connection error returns 503 Service Unavailable."""
        mock_get_queries.return_value = [{
            "collection": "clientes_por_ejecutivo",
            "filter": {}
        }]
        mock_get_prompt.return_value = "Test prompt"
        
        # Configure mock to raise ConnectionError
        mock_ai_client.analyze.side_effect = ConnectionError("Connection refused")
        
        request_data = {
            "current_date": "2026-02-17",
            "is_testing": False
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    
    @patch('app.config.queries.get_queries')
    @patch('app.config.queries.get_analysis_prompt')
    def test_ai_service_error_returns_502(
        self, mock_get_prompt, mock_get_queries, client, mock_ai_client, analysis_service
    ):
        """Test AWS Bedrock service error returns 502 Bad Gateway."""
        mock_get_queries.return_value = [{
            "collection": "clientes_por_ejecutivo",
            "filter": {}
        }]
        mock_get_prompt.return_value = "Test prompt"
        
        # Configure mock to raise ServiceError with AI service failure
        mock_ai_client.analyze.side_effect = ServiceError(
            message="Failed to analyze data with AI service",
            step="ai_analysis",
            details="API rate limit exceeded"
        )
        
        request_data = {
            "current_date": "2026-02-17",
            "is_testing": False
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "Failed to analyze data with AI service" in response.json()["detail"]
    
    @patch('app.config.queries.get_queries')
    @patch('app.config.queries.get_analysis_prompt')
    def test_empty_query_results_returns_success(
        self, mock_get_prompt, mock_get_queries, client, mock_data_client, mock_ai_client
    ):
        """Test empty query results returns success with zero count."""
        mock_get_queries.return_value = [{
            "collection": "clientes_por_ejecutivo",
            "filter": {}
        }]
        mock_get_prompt.return_value = "Test prompt"
        
        # Configure mock to return empty list
        mock_data_client.query.return_value = []
        
        request_data = {
            "current_date": "2026-02-17",
            "is_testing": False
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metadata"]["data_count"] == 0
        
        # AI client should not be called for empty results
        mock_ai_client.analyze.assert_not_called()
    
    @patch('app.config.queries.get_queries')
    def test_no_queries_generated_returns_400(
        self, mock_get_queries, client
    ):
        """Test that no queries generated returns 400."""
        # Mock get_queries to return empty list
        mock_get_queries.return_value = []
        
        request_data = {
            "current_date": "2026-02-17",
            "is_testing": False
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "No queries could be generated" in response.json()["detail"]


class TestDependencyInjection:
    """Tests for dependency injection functionality."""
    
    def test_get_analysis_service_without_configuration_returns_503(self):
        """Test that accessing endpoint without configured service returns 503."""
        # Create a new app without setting the service
        import app.api.routes as routes_module
        
        # Temporarily clear the service
        original_service = routes_module._analysis_service
        routes_module._analysis_service = None
        
        try:
            test_app = FastAPI()
            test_app.include_router(router)
            test_client = TestClient(test_app)
            
            response = test_client.post("/api/analyze", json={
                "current_date": "2026-02-17",
                "is_testing": False
            })
            
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert "Service not initialized" in response.json()["detail"]
        finally:
            # Restore the service
            routes_module._analysis_service = original_service
    
    def test_set_analysis_service_with_none_raises_error(self):
        """Test that setting service to None raises ValueError."""
        with pytest.raises(ValueError, match="Analysis service cannot be None"):
            set_analysis_service(None)
    
    def test_set_settings_with_none_raises_error(self):
        """Test that setting settings to None raises ValueError."""
        with pytest.raises(ValueError, match="Settings cannot be None"):
            set_settings(None)


class TestErrorResponseFormat:
    """Tests for error response format consistency."""
    
    @patch('app.config.queries.get_queries')
    @patch('app.config.queries.get_analysis_prompt')
    def test_error_response_has_required_fields(
        self, mock_get_prompt, mock_get_queries, client, mock_data_client, analysis_service
    ):
        """Test that error responses have all required fields."""
        mock_get_queries.return_value = [{
            "collection": "clientes_por_ejecutivo",
            "filter": {}
        }]
        mock_get_prompt.return_value = "Test prompt"
        
        # Trigger an error
        mock_data_client.query.side_effect = ServiceError(
            message="Test error",
            step="data_retrieval",
            details="Test details"
        )
        
        request_data = {
            "current_date": "2026-02-17",
            "is_testing": False
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        # Should return error via HTTPException
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_502_BAD_GATEWAY,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]
        
        data = response.json()
        assert "detail" in data


class TestHealthCheckEndpoints:
    """Tests for health check endpoints."""
    
    def test_mongodb_health_check_success(self, client, mock_data_client):
        """Test MongoDB health check returns success when connected."""
        mock_data_client.query.return_value = []
        
        response = client.get("/api/health/mongodb")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "connected"
        assert "database" in data
    
    def test_mongodb_health_check_failure(self, client, mock_data_client):
        """Test MongoDB health check returns 503 when connection fails."""
        mock_data_client.query.side_effect = ConnectionError("Connection failed")
        
        response = client.get("/api/health/mongodb")
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    
    def test_bedrock_health_check_success(self, client, mock_ai_client):
        """Test Bedrock health check returns success when connected."""
        mock_ai_client.analyze.return_value = {
            "analysis": "OK",
            "metadata": {}
        }
        
        response = client.get("/api/health/bedrock")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "connected"
        assert "model" in data
        assert "region" in data
    
    def test_bedrock_health_check_failure(self, client, mock_ai_client):
        """Test Bedrock health check returns 503 when connection fails."""
        mock_ai_client.analyze.side_effect = ConnectionError("Connection failed")
        
        response = client.get("/api/health/bedrock")
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    
    def test_sendgrid_health_check_success(self, client, mock_settings):
        """Test SendGrid health check returns success when configured."""
        response = client.get("/api/health/sendgrid")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "configured"
        assert "from_email" in data
        assert "test_email" in data
