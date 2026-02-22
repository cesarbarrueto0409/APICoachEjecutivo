"""Tests for MongoDB connectivity."""

import pytest
from app.clients.mongodb_client import MongoDBClient


def test_mongodb_connection(test_config, testing_collections):
    """Test MongoDB connection can be established."""
    client = MongoDBClient(
        test_config["mongodb_uri"],
        test_config["mongodb_database"]
    )
    
    # Should connect without errors
    client.connect()
    
    # Should be able to query - using testing collection
    result = client.query({
        "collection": testing_collections["executives"],
        "filter": {},
        "limit": 1
    })
    
    assert isinstance(result, list)
    client.disconnect()


def test_mongodb_query_execution(test_config, testing_collections):
    """Test MongoDB can execute queries successfully."""
    client = MongoDBClient(
        test_config["mongodb_uri"],
        test_config["mongodb_database"]
    )
    client.connect()
    
    # Test simple query - using testing collection
    result = client.query({
        "collection": testing_collections["memory"],
        "filter": {},
        "limit": 5
    })
    
    assert isinstance(result, list)
    assert len(result) <= 5
    
    client.disconnect()


def test_mongodb_prompt_retrieval(test_config):
    """Test MongoDB can retrieve prompt templates."""
    client = MongoDBClient(
        test_config["mongodb_uri"],
        test_config["mongodb_database"]
    )
    client.connect()
    
    try:
        prompt_data = client.get_prompt_template("bedrock_analysis_prompt")
        assert "template" in prompt_data
        assert isinstance(prompt_data["template"], str)
        assert len(prompt_data["template"]) > 0
    except ValueError:
        # Prompt might not exist in test DB
        pytest.skip("Prompt template not found in database")
    finally:
        client.disconnect()
