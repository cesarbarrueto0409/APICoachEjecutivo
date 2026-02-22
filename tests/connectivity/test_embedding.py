"""Tests for Embedding service connectivity."""

import pytest
from app.clients.embedding_client import EmbeddingClient


def test_embedding_connection(test_config):
    """Test embedding service connection can be established."""
    client = EmbeddingClient(
        test_config["embedding_api_key"],
        test_config["embedding_endpoint"],
        test_config["embedding_model_name"]
    )
    
    # Should connect without errors
    client.connect()
    
    # Test embedding generation
    embedding = client.generate_embedding("Test text")
    
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)


def test_embedding_batch_generation(test_config):
    """Test embedding service can generate batch embeddings."""
    client = EmbeddingClient(
        test_config["embedding_api_key"],
        test_config["embedding_endpoint"],
        test_config["embedding_model_name"]
    )
    client.connect()
    
    texts = ["First text", "Second text", "Third text"]
    embeddings = client.generate_embeddings_batch(texts)
    
    assert isinstance(embeddings, list)
    assert len(embeddings) == 3
    assert all(isinstance(emb, list) for emb in embeddings)
    assert all(len(emb) > 0 for emb in embeddings)
