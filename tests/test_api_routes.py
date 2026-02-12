"""
Tests for API routes.

This module contains tests for the FastAPI routes, including request validation,
error handling, and successful analysis workflows.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, List

from app.api.routes import router, set_analysis_service
from app.services.analysis_service import AnalysisService, ServiceError
from fastapi import FastAPI


@pytest.fixture
def app():
    """Create a FastAPI application for testing."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def mock_data_client():
    """Create a mock data client."""
    client = Mock()
    client.query = Mock(return_value=[
        {"id": 1, "name": "Test User 1", "status": "active"},
        {"id": 2, "name": "Test User 2", "status": "active"}
    ])
    return client


@pytest.fixture
def mock_ai_client():
    """Create a mock AI client."""
    client = Mock()
    client.analyze = Mock(return_value={
        "analysis": "Test analysis results",
        "confidence": 0.95,
        "metadata": {"model": "test-model"}
    })
    return client


@pytest.fixture
def analysis_service(mock_data_client, mock_ai_client):
    """Create an analysis service with mock clients."""
    return AnalysisService(mock_data_client, mock_ai_client)


@pytest.fixture
def client(app, analysis_service):
    """Create a test client with configured service."""
    set_analysis_service(analysis_service)
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""
    
    def test_health_check_returns_healthy_status(self, client):
        """Test that health check endpoint returns healthy status."""
        response = client.get("/api/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Azure AI API Service"


class TestAnalyzeEndpoint:
    """Tests for the /analyze endpoint."""
    
    def test_successful_analysis_returns_200(self, client, mock_data_client, mock_ai_client):
        """Test successful analysis workflow returns 200 OK."""
        request_data = {
            "collection": "users",
            "filter": {"status": "active"},
            "limit": 100
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["data_count"] == 2
        assert "analysis" in data
        assert data["error"] is None
        
        # Verify clients were called correctly
        mock_data_client.query.assert_called_once()
        mock_ai_client.analyze.assert_called_once()
    
    def test_analysis_with_custom_prompt(self, client, mock_data_client, mock_ai_client):
        """Test analysis with custom prompt passes prompt to AI client."""
        request_data = {
            "collection": "users",
            "filter": {"status": "active"},
            "prompt": "Custom analysis prompt"
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify AI client received the custom prompt
        call_args = mock_ai_client.analyze.call_args
        assert call_args[1]["prompt"] == "Custom analysis prompt"
    
    def test_analysis_with_projection(self, client, mock_data_client):
        """Test analysis with field projection."""
        request_data = {
            "collection": "users",
            "filter": {"status": "active"},
            "projection": {"name": 1, "email": 1}
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify projection was passed to data client
        call_args = mock_data_client.query.call_args[0][0]
        assert "projection" in call_args
        assert call_args["projection"] == {"name": 1, "email": 1}
    
    def test_missing_collection_returns_422(self, client):
        """Test request without collection field returns 422 Unprocessable Entity."""
        request_data = {
            "filter": {"status": "active"}
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        # FastAPI returns 422 for validation errors
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_invalid_limit_returns_422(self, client):
        """Test request with invalid limit returns 422."""
        request_data = {
            "collection": "users",
            "limit": -1  # Invalid: must be >= 1
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_limit_exceeds_maximum_returns_422(self, client):
        """Test request with limit exceeding maximum returns 422."""
        request_data = {
            "collection": "users",
            "limit": 20000  # Invalid: must be <= 10000
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_data_retrieval_connection_error_returns_503(
        self, client, mock_data_client, analysis_service
    ):
        """Test MongoDB connection error returns 503 Service Unavailable."""
        # Configure mock to raise ConnectionError (which service layer wraps)
        mock_data_client.query.side_effect = ConnectionError("Connection timeout")
        
        request_data = {
            "collection": "users",
            "filter": {"status": "active"}
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Failed to connect to data source" in response.json()["detail"]
    
    def test_ai_service_connection_error_returns_503(
        self, client, mock_ai_client, analysis_service
    ):
        """Test Azure AI connection error returns 503 Service Unavailable."""
        # Configure mock to raise ConnectionError (which service layer wraps)
        mock_ai_client.analyze.side_effect = ConnectionError("Connection refused")
        
        request_data = {
            "collection": "users",
            "filter": {"status": "active"}
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "Failed to connect to AI service" in response.json()["detail"]
    
    def test_ai_service_error_returns_502(
        self, client, mock_ai_client, analysis_service
    ):
        """Test Azure AI service error returns 502 Bad Gateway."""
        # Configure mock to raise ServiceError with AI service failure
        mock_ai_client.analyze.side_effect = ServiceError(
            message="Failed to analyze data with AI service",
            step="ai_analysis",
            details="API rate limit exceeded"
        )
        
        request_data = {
            "collection": "users",
            "filter": {"status": "active"}
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "Failed to analyze data with AI service" in response.json()["detail"]
    
    def test_empty_query_results_returns_success(
        self, client, mock_data_client, mock_ai_client
    ):
        """Test empty query results returns success with zero count."""
        # Configure mock to return empty list
        mock_data_client.query.return_value = []
        
        request_data = {
            "collection": "users",
            "filter": {"status": "inactive"}
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert data["data_count"] == 0
        assert "No data found" in data["analysis"]["analysis"]
        
        # AI client should not be called for empty results
        mock_ai_client.analyze.assert_not_called()
    
    def test_default_filter_is_empty_dict(self, client, mock_data_client):
        """Test that default filter is an empty dictionary."""
        request_data = {
            "collection": "users"
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify empty filter was passed
        call_args = mock_data_client.query.call_args[0][0]
        assert call_args["filter"] == {}
    
    def test_default_limit_is_100(self, client, mock_data_client):
        """Test that default limit is 100."""
        request_data = {
            "collection": "users"
        }
        
        response = client.post("/api/analyze", json=request_data)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify default limit was passed
        call_args = mock_data_client.query.call_args[0][0]
        assert call_args["limit"] == 100


class TestDependencyInjection:
    """Tests for dependency injection functionality."""
    
    def test_get_analysis_service_without_configuration_returns_503(self):
        """Test that accessing endpoint without configured service returns 503."""
        # Create a new app without setting the service
        from app.api.routes import _analysis_service, router
        import app.api.routes as routes_module
        
        # Temporarily clear the service
        original_service = routes_module._analysis_service
        routes_module._analysis_service = None
        
        try:
            test_app = FastAPI()
            test_app.include_router(router)
            test_client = TestClient(test_app)
            
            response = test_client.post("/api/analyze", json={"collection": "test"})
            
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert "Service not initialized" in response.json()["detail"]
        finally:
            # Restore the service
            routes_module._analysis_service = original_service
    
    def test_set_analysis_service_with_none_raises_error(self):
        """Test that setting service to None raises ValueError."""
        with pytest.raises(ValueError, match="Analysis service cannot be None"):
            set_analysis_service(None)


class TestErrorResponseFormat:
    """Tests for error response format consistency."""
    
    def test_error_response_has_required_fields(
        self, client, mock_data_client, analysis_service
    ):
        """Test that error responses have all required fields."""
        # Trigger an error
        mock_data_client.query.side_effect = ServiceError(
            message="Test error",
            step="data_retrieval",
            details="Test details"
        )
        
        request_data = {
            "collection": "users"
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
