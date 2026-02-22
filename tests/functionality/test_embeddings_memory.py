"""Tests for embedding generation and memory system."""

import pytest
from app.clients.embedding_client import EmbeddingClient
from app.clients.mongodb_client import MongoDBClient
from app.services.recommendation_memory_store import RecommendationMemoryStore
from app.services.similarity_service import SimilarityService


def test_embedding_generation(test_config):
    """Test embedding generation produces valid vectors."""
    client = EmbeddingClient(
        test_config["embedding_api_key"],
        test_config["embedding_endpoint"],
        test_config["embedding_model_name"]
    )
    client.connect()
    
    text = "Llamar al cliente para revisar su situación de riesgo"
    embedding = client.generate_embedding(text)
    
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)


def test_similarity_computation(test_config):
    """Test similarity computation between embeddings."""
    client = EmbeddingClient(
        test_config["embedding_api_key"],
        test_config["embedding_endpoint"],
        test_config["embedding_model_name"]
    )
    client.connect()
    
    text1 = "Llamar al cliente para revisar riesgo"
    text2 = "Contactar al cliente para verificar riesgo"
    text3 = "Reunión para discutir nuevas oportunidades"
    
    emb1 = client.generate_embedding(text1)
    emb2 = client.generate_embedding(text2)
    emb3 = client.generate_embedding(text3)
    
    similarity_service = SimilarityService(similarity_threshold=0.85)
    
    # Similar texts should have high similarity
    sim_12 = similarity_service.cosine_similarity(emb1, emb2)
    assert sim_12 > 0.7  # Should be similar
    
    # Different texts should have lower similarity
    sim_13 = similarity_service.cosine_similarity(emb1, emb3)
    assert sim_13 < sim_12  # Should be less similar


def test_no_duplicate_recommendations(test_config, testing_collections):
    """Test that similar recommendations are filtered out."""
    mongo_client = MongoDBClient(
        test_config["mongodb_uri"],
        test_config["mongodb_database"]
    )
    mongo_client.connect()
    
    embedding_client = EmbeddingClient(
        test_config["embedding_api_key"],
        test_config["embedding_endpoint"],
        test_config["embedding_model_name"]
    )
    embedding_client.connect()
    
    memory_store = RecommendationMemoryStore(
        data_client=mongo_client,
        embedding_client=embedding_client
    )
    
    similarity_service = SimilarityService(
        similarity_threshold=0.85,
        cooldown_days=7
    )
    
    # Clear testing collection
    mongo_client._database[testing_collections["memory"]].delete_many({})
    
    # Store first recommendation
    rec1_text = "Llamar al cliente para revisar su situación de riesgo crítico"
    rec1_id = memory_store.store_recommendation(
        executive_id="TEST001",
        client_id="12345678",
        recommendation_text=rec1_text
    )
    
    assert rec1_id is not None
    
    # Try to store very similar recommendation
    rec2_text = "Contactar al cliente para verificar su situación de riesgo crítico"
    rec2_emb = embedding_client.generate_embedding(rec2_text)
    
    # Get historical recommendations
    historical = memory_store.get_historical_recommendations(
        executive_id="TEST001",
        client_id="12345678"
    )
    
    # Should have at least the one we just stored
    assert len(historical) >= 1
    # Find our stored recommendation
    stored_rec = next((r for r in historical if r.get("recommendation") == rec1_text), None)
    assert stored_rec is not None
    
    # Check if new recommendation should be filtered
    should_filter, matching = similarity_service.check_recommendation_similarity(
        new_recommendation={"recommendation": rec2_text, "embedding": rec2_emb},
        historical_recommendations=historical
    )
    
    assert should_filter is True  # Should be filtered due to high similarity
    
    # Cleanup
    mongo_client._database[testing_collections["memory"]].delete_many({})
    mongo_client.disconnect()


def test_memory_store_retrieval(test_config, testing_collections):
    """Test memory store can retrieve historical recommendations."""
    mongo_client = MongoDBClient(
        test_config["mongodb_uri"],
        test_config["mongodb_database"]
    )
    mongo_client.connect()
    
    embedding_client = EmbeddingClient(
        test_config["embedding_api_key"],
        test_config["embedding_endpoint"],
        test_config["embedding_model_name"]
    )
    embedding_client.connect()
    
    memory_store = RecommendationMemoryStore(
        data_client=mongo_client,
        embedding_client=embedding_client
    )
    
    # Clear testing collection
    mongo_client._database[testing_collections["memory"]].delete_many({})
    
    # Store multiple recommendations
    for i in range(5):
        memory_store.store_recommendation(
            executive_id="TEST002",
            client_id="87654321",
            recommendation_text=f"Recommendation {i+1}"
        )
    
    # Retrieve with limit
    historical = memory_store.get_historical_recommendations(
        executive_id="TEST002",
        client_id="87654321",
        limit=3
    )
    
    assert len(historical) == 3
    assert all("embedding" in rec for rec in historical)
    assert all("timestamp" in rec for rec in historical)
    
    # Cleanup
    mongo_client._database[testing_collections["memory"]].delete_many({})
    mongo_client.disconnect()
