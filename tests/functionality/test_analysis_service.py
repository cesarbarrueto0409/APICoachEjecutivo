"""
Unit tests for AnalysisService.

These tests verify the AnalysisService orchestrates the workflow correctly,
handles errors appropriately, and returns properly structured results.
"""

import pytest
from typing import List, Dict, Any
from app.services.analysis_service import AnalysisService, ServiceError
from app.clients.interfaces import IDataClient, IAIClient


class MockDataClient(IDataClient):
    """Mock data client for testing."""
    
    def __init__(self, return_data: List[Dict[str, Any]] = None, raise_error: Exception = None):
        self.return_data = return_data if return_data is not None else []
        self.raise_error = raise_error
        self.connected = False
        self.query_called = False
        self.last_query_params = None
    
    def connect(self) -> None:
        self.connected = True
    
    def query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.query_called = True
        self.last_query_params = query_params
        if self.raise_error:
            raise self.raise_error
        return self.return_data
    
    def disconnect(self) -> None:
        self.connected = False


class MockAIClient(IAIClient):
    """Mock AI client for testing."""
    
    def __init__(self, return_result: Dict[str, Any] = None, raise_error: Exception = None):
        self.return_result = return_result if return_result is not None else {
            "analysis": "Mock analysis result",
            "confidence": 0.95,
            "metadata": {}
        }
        self.raise_error = raise_error
        self.connected = False
        self.analyze_called = False
        self.last_data = None
        self.last_prompt = None
    
    def connect(self) -> None:
        self.connected = True
    
    def analyze(self, data: List[Dict[str, Any]], prompt: str = None) -> Dict[str, Any]:
        self.analyze_called = True
        self.last_data = data
        self.last_prompt = prompt
        if self.raise_error:
            raise self.raise_error
        return self.return_result


class TestAnalysisServiceInitialization:
    """Test AnalysisService initialization."""
    
    def test_init_with_valid_clients(self):
        """Test initialization with valid clients."""
        data_client = MockDataClient()
        ai_client = MockAIClient()
        
        service = AnalysisService(data_client, ai_client)
        
        assert service._data_client is data_client
        assert service._ai_client is ai_client
    
    def test_init_with_none_data_client(self):
        """Test initialization fails with None data_client."""
        ai_client = MockAIClient()
        
        with pytest.raises(ValueError, match="data_client cannot be None"):
            AnalysisService(None, ai_client)
    
    def test_init_with_none_ai_client(self):
        """Test initialization fails with None ai_client."""
        data_client = MockDataClient()
        
        with pytest.raises(ValueError, match="ai_client cannot be None"):
            AnalysisService(data_client, None)


class TestAnalysisServiceExecuteAnalysis:
    """Test AnalysisService.execute_analysis() method."""
    
    def test_successful_analysis_with_data(self):
        """Test successful analysis workflow with data."""
        # Setup
        test_data = [
            {"id": 1, "name": "Alice", "score": 85},
            {"id": 2, "name": "Bob", "score": 92}
        ]
        data_client = MockDataClient(return_data=test_data)
        ai_client = MockAIClient(return_result={
            "analysis": "Users show strong performance",
            "confidence": 0.9,
            "metadata": {"model": "gpt-4"}
        })
        service = AnalysisService(data_client, ai_client)
        
        query_params = {
            "collection": "users",
            "filter": {"active": True}
        }
        
        # Execute
        result = service.execute_analysis(query_params, analysis_prompt="Analyze users")
        
        # Verify
        assert result["status"] == "success"
        assert result["data_count"] == 2
        assert result["analysis"]["analysis"] == "Users show strong performance"
        assert result["analysis"]["confidence"] == 0.9
        assert result["query_params"] == query_params
        
        # Verify clients were called correctly
        assert data_client.query_called
        assert data_client.last_query_params == query_params
        assert ai_client.analyze_called
        assert ai_client.last_data == test_data
        assert ai_client.last_prompt == "Analyze users"
    
    def test_successful_analysis_with_empty_data(self):
        """Test analysis with empty query results."""
        # Setup
        data_client = MockDataClient(return_data=[])
        ai_client = MockAIClient()
        service = AnalysisService(data_client, ai_client)
        
        query_params = {"collection": "users"}
        
        # Execute
        result = service.execute_analysis(query_params)
        
        # Verify
        assert result["status"] == "success"
        assert result["data_count"] == 0
        assert "No data found" in result["analysis"]["analysis"]
        
        # AI client should not be called for empty data
        assert not ai_client.analyze_called
    
    def test_analysis_without_custom_prompt(self):
        """Test analysis uses None prompt when not provided."""
        # Setup
        test_data = [{"id": 1}]
        data_client = MockDataClient(return_data=test_data)
        ai_client = MockAIClient()
        service = AnalysisService(data_client, ai_client)
        
        # Execute
        result = service.execute_analysis({"collection": "test"})
        
        # Verify
        assert result["status"] == "success"
        assert ai_client.last_prompt is None
    
    def test_invalid_query_params_not_dict(self):
        """Test error when query_params is not a dictionary."""
        # Setup
        data_client = MockDataClient()
        ai_client = MockAIClient()
        service = AnalysisService(data_client, ai_client)
        
        # Execute & Verify
        with pytest.raises(ValueError, match="query_params must be a dictionary"):
            service.execute_analysis("not a dict")
    
    def test_invalid_query_params_missing_collection(self):
        """Test error when query_params missing collection field."""
        # Setup
        data_client = MockDataClient()
        ai_client = MockAIClient()
        service = AnalysisService(data_client, ai_client)
        
        # Execute & Verify
        with pytest.raises(ValueError, match="must include 'collection' field"):
            service.execute_analysis({"filter": {}})
    
    def test_data_retrieval_connection_error(self):
        """Test error handling for data client connection failure."""
        # Setup
        data_client = MockDataClient(raise_error=ConnectionError("MongoDB unavailable"))
        ai_client = MockAIClient()
        service = AnalysisService(data_client, ai_client)
        
        # Execute & Verify
        with pytest.raises(ServiceError) as exc_info:
            service.execute_analysis({"collection": "test"})
        
        assert exc_info.value.step == "data_retrieval"
        assert "Failed to connect to data source" in exc_info.value.message
        assert "MongoDB unavailable" in exc_info.value.details
    
    def test_data_retrieval_value_error(self):
        """Test error handling for invalid query parameters."""
        # Setup
        data_client = MockDataClient(raise_error=ValueError("Invalid filter"))
        ai_client = MockAIClient()
        service = AnalysisService(data_client, ai_client)
        
        # Execute & Verify
        with pytest.raises(ServiceError) as exc_info:
            service.execute_analysis({"collection": "test"})
        
        assert exc_info.value.step == "data_retrieval"
        assert "Invalid query parameters" in exc_info.value.message
    
    def test_data_retrieval_generic_error(self):
        """Test error handling for generic data retrieval errors."""
        # Setup
        data_client = MockDataClient(raise_error=Exception("Database error"))
        ai_client = MockAIClient()
        service = AnalysisService(data_client, ai_client)
        
        # Execute & Verify
        with pytest.raises(ServiceError) as exc_info:
            service.execute_analysis({"collection": "test"})
        
        assert exc_info.value.step == "data_retrieval"
        assert "Failed to retrieve data" in exc_info.value.message
    
    def test_ai_analysis_connection_error(self):
        """Test error handling for AI client connection failure."""
        # Setup
        data_client = MockDataClient(return_data=[{"id": 1}])
        ai_client = MockAIClient(raise_error=ConnectionError("Azure AI unavailable"))
        service = AnalysisService(data_client, ai_client)
        
        # Execute & Verify
        with pytest.raises(ServiceError) as exc_info:
            service.execute_analysis({"collection": "test"})
        
        assert exc_info.value.step == "ai_analysis"
        assert "Failed to connect to AI service" in exc_info.value.message
        assert "Azure AI unavailable" in exc_info.value.details
    
    def test_ai_analysis_generic_error(self):
        """Test error handling for generic AI analysis errors."""
        # Setup
        data_client = MockDataClient(return_data=[{"id": 1}])
        ai_client = MockAIClient(raise_error=Exception("API rate limit"))
        service = AnalysisService(data_client, ai_client)
        
        # Execute & Verify
        with pytest.raises(ServiceError) as exc_info:
            service.execute_analysis({"collection": "test"})
        
        assert exc_info.value.step == "ai_analysis"
        assert "Failed to analyze data" in exc_info.value.message


class TestServiceError:
    """Test ServiceError exception class."""
    
    def test_service_error_creation(self):
        """Test ServiceError can be created with all parameters."""
        error = ServiceError(
            message="Test error",
            step="test_step",
            details="Additional details"
        )
        
        assert error.message == "Test error"
        assert error.step == "test_step"
        assert error.details == "Additional details"
        assert str(error) == "Test error"
    
    def test_service_error_without_details(self):
        """Test ServiceError can be created without details."""
        error = ServiceError(
            message="Test error",
            step="test_step"
        )
        
        assert error.message == "Test error"
        assert error.step == "test_step"
        assert error.details is None
