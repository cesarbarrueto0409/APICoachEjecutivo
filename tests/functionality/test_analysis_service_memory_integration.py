"""
Integration tests for AnalysisService with memory system.

These tests verify that the AnalysisService correctly integrates with
the memory system components (EmbeddingClient, RecommendationMemoryStore, SimilarityService).
"""

import pytest
from typing import List, Dict, Any
from app.services.analysis_service import AnalysisService
from app.clients.interfaces import IDataClient, IAIClient, IEmbeddingClient


class MockDataClient(IDataClient):
    """Mock data client for testing."""
    
    def __init__(self, return_data: List[Dict[str, Any]] = None):
        self.return_data = return_data if return_data is not None else []
        self.connected = False
        self.inserted_docs = []
    
    def connect(self) -> None:
        self.connected = True
    
    def query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.return_data
    
    def disconnect(self) -> None:
        self.connected = False
    
    def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        self.inserted_docs.append(document)
        return "mock_id_123"


class MockAIClient(IAIClient):
    """Mock AI client for testing."""
    
    def __init__(self, recommendations: List[Dict[str, Any]] = None):
        self.recommendations = recommendations or []
        self.connected = False
    
    def connect(self) -> None:
        self.connected = True
    
    def analyze(self, data: List[Dict[str, Any]], prompt: str = None) -> Dict[str, Any]:
        return {
            "analysis": "Mock analysis",
            "recommendations": self.recommendations,
            "confidence": 0.95
        }


class MockEmbeddingClient(IEmbeddingClient):
    """Mock embedding client for testing."""
    
    def __init__(self):
        self.connected = False
        self.embedding_counter = 0
    
    def connect(self) -> None:
        self.connected = True
    
    def generate_embedding(self, text: str) -> List[float]:
        # Generate a simple mock embedding based on text length
        self.embedding_counter += 1
        return [float(len(text)) / 100.0 + self.embedding_counter * 0.01] * 10
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.generate_embedding(text) for text in texts]


class TestAnalysisServiceMemoryIntegration:
    """Test AnalysisService integration with memory system."""
    
    def test_initialization_with_memory_components(self):
        """Test that AnalysisService can be initialized with memory components."""
        from app.services.recommendation_memory_store import RecommendationMemoryStore
        from app.services.similarity_service import SimilarityService
        
        data_client = MockDataClient()
        ai_client = MockAIClient()
        embedding_client = MockEmbeddingClient()
        memory_store = RecommendationMemoryStore(data_client, embedding_client)
        similarity_service = SimilarityService()
        
        service = AnalysisService(
            data_client=data_client,
            ai_client=ai_client,
            embedding_client=embedding_client,
            memory_store=memory_store,
            similarity_service=similarity_service,
            memory_enabled=True
        )
        
        assert service._memory_enabled is True
        assert service._embedding_client is embedding_client
        assert service._memory_store is memory_store
        assert service._similarity_service is similarity_service
    
    def test_initialization_with_memory_disabled(self):
        """Test that AnalysisService works with memory disabled."""
        data_client = MockDataClient()
        ai_client = MockAIClient()
        
        service = AnalysisService(
            data_client=data_client,
            ai_client=ai_client,
            memory_enabled=False
        )
        
        assert service._memory_enabled is False
    
    def test_execute_analysis_with_memory_basic_flow(self):
        """Test basic flow of execute_analysis_with_memory."""
        from app.services.recommendation_memory_store import RecommendationMemoryStore
        from app.services.similarity_service import SimilarityService
        
        # Setup
        test_data = [{"id": 1, "name": "Test Client"}]
        recommendations = [
            {"recommendation": "Contact client for renewal"},
            {"recommendation": "Schedule follow-up meeting"}
        ]
        
        data_client = MockDataClient(return_data=test_data)
        ai_client = MockAIClient(recommendations=recommendations)
        embedding_client = MockEmbeddingClient()
        memory_store = RecommendationMemoryStore(data_client, embedding_client)
        similarity_service = SimilarityService()
        
        service = AnalysisService(
            data_client=data_client,
            ai_client=ai_client,
            embedding_client=embedding_client,
            memory_store=memory_store,
            similarity_service=similarity_service,
            memory_enabled=True
        )
        
        # Execute
        result = service.execute_analysis_with_memory(
            executive_id="exec_1",
            client_id="client_1",
            query_params={"collection": "test"},
            analysis_prompt="Analyze client data"
        )
        
        # Verify
        assert result["status"] == "success"
        assert "recommendations" in result
        assert result["memory_enabled"] is True
        assert len(result["recommendations"]) > 0
    
    def test_execute_analysis_with_memory_disabled_fallback(self):
        """Test that execute_analysis_with_memory works when memory is disabled."""
        test_data = [{"id": 1, "name": "Test Client"}]
        recommendations = [{"recommendation": "Test recommendation"}]
        
        data_client = MockDataClient(return_data=test_data)
        ai_client = MockAIClient(recommendations=recommendations)
        
        service = AnalysisService(
            data_client=data_client,
            ai_client=ai_client,
            memory_enabled=False
        )
        
        # Execute
        result = service.execute_analysis_with_memory(
            executive_id="exec_1",
            client_id="client_1",
            query_params={"collection": "test"}
        )
        
        # Verify - should work without memory system
        assert result["status"] == "success"
        assert result["memory_enabled"] is False
    
    def test_build_enhanced_prompt_with_historical_context(self):
        """Test that _build_enhanced_prompt includes historical recommendations."""
        from app.services.recommendation_memory_store import RecommendationMemoryStore
        from app.services.similarity_service import SimilarityService
        
        data_client = MockDataClient()
        ai_client = MockAIClient()
        embedding_client = MockEmbeddingClient()
        memory_store = RecommendationMemoryStore(data_client, embedding_client)
        similarity_service = SimilarityService()
        
        service = AnalysisService(
            data_client=data_client,
            ai_client=ai_client,
            embedding_client=embedding_client,
            memory_store=memory_store,
            similarity_service=similarity_service,
            memory_enabled=True
        )
        
        historical_recs = [
            {
                "recommendation": "Previous recommendation 1",
                "timestamp": "2024-01-01T00:00:00"
            },
            {
                "recommendation": "Previous recommendation 2",
                "timestamp": "2024-01-02T00:00:00"
            }
        ]
        
        enhanced_prompt = service._build_enhanced_prompt(
            base_prompt="Analyze the data",
            historical_recs=historical_recs,
            current_date="2024-01-15"
        )
        
        # Verify prompt includes historical context
        assert "Previous recommendations for this client:" in enhanced_prompt
        assert "Previous recommendation 1" in enhanced_prompt
        assert "Previous recommendation 2" in enhanced_prompt
        assert "2024-01-01T00:00:00" in enhanced_prompt
        assert "Current date for analysis context: 2024-01-15" in enhanced_prompt
        assert "Analyze the data" in enhanced_prompt
    
    def test_extract_recommendations_from_analysis_result(self):
        """Test that _extract_recommendations correctly extracts recommendations."""
        data_client = MockDataClient()
        ai_client = MockAIClient()
        
        service = AnalysisService(
            data_client=data_client,
            ai_client=ai_client
        )
        
        # Test with recommendations in analysis dict
        analysis_result = {
            "status": "success",
            "analysis": {
                "recommendations": [
                    {"recommendation": "Rec 1"},
                    {"recommendation": "Rec 2"}
                ]
            }
        }
        
        recs = service._extract_recommendations(analysis_result)
        assert len(recs) == 2
        assert recs[0]["recommendation"] == "Rec 1"
        
        # Test with no recommendations
        analysis_result_empty = {
            "status": "success",
            "analysis": {"text": "Some analysis"}
        }
        
        recs_empty = service._extract_recommendations(analysis_result_empty)
        assert len(recs_empty) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
