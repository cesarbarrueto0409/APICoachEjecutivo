"""Tests for MongoDB query execution and data retrieval."""

import pytest
from datetime import datetime
from app.clients.mongodb_client import MongoDBClient
from app.config.queries import get_queries, get_analysis_prompt


def test_query_generation(test_config):
    """Test query generation with current date."""
    current_date = "2026-02-18"
    queries = get_queries(current_date)
    
    assert isinstance(queries, list)
    assert len(queries) > 0
    assert "collection" in queries[0]
    assert "pipeline" in queries[0]


def test_prompt_generation(test_config):
    """Test prompt generation with date variables."""
    current_date = "2026-02-18"
    prompt = get_analysis_prompt(current_date)
    
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "2026-02-18" in prompt or "2026" in prompt


def test_mongodb_data_structure(test_config, testing_collections):
    """Test MongoDB returns expected data structure."""
    client = MongoDBClient(
        test_config["mongodb_uri"],
        test_config["mongodb_database"]
    )
    client.connect()
    
    # Use testing collection - read only from production collections
    result = client.query({
        "collection": "clientes_por_ejecutivo",
        "filter": {},
        "limit": 1
    })
    
    assert isinstance(result, list)
    if len(result) > 0:
        exec_data = result[0]
        assert "id_ejecutivo" in exec_data
        assert "nombre_ejecutivo" in exec_data
    
    client.disconnect()


def test_sales_data_retrieval(test_config, testing_collections):
    """Test sales data can be retrieved correctly - READ ONLY."""
    client = MongoDBClient(
        test_config["mongodb_uri"],
        test_config["mongodb_database"]
    )
    client.connect()
    
    # Read only from production collection - no modifications
    result = client.query({
        "collection": "sales_last_month",
        "filter": {},
        "limit": 10
    })
    
    assert isinstance(result, list)
    client.disconnect()
