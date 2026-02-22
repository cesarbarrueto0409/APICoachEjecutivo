"""Tests for AWS Bedrock connectivity."""

import pytest
from app.clients.aws_bedrock_client import AWSBedrockClient


def test_bedrock_connection(test_config):
    """Test AWS Bedrock connection can be established."""
    client = AWSBedrockClient(
        test_config["aws_region"],
        test_config["aws_bedrock_model_id"]
    )
    
    # Should connect without errors
    client.connect()
    
    # Test simple analysis
    test_data = [{"test": "connection"}]
    result = client.analyze(test_data, prompt="Respond with: OK")
    
    assert "analysis" in result
    assert isinstance(result["analysis"], str)


def test_bedrock_analysis_response(test_config):
    """Test AWS Bedrock returns valid analysis responses."""
    client = AWSBedrockClient(
        test_config["aws_region"],
        test_config["aws_bedrock_model_id"]
    )
    client.connect()
    
    test_data = [
        {
            "id_ejecutivo": 1,
            "nombre_ejecutivo": "Test Executive",
            "ventas_total_mes": 1000000,
            "goal_mes": 1500000
        }
    ]
    
    result = client.analyze(
        test_data,
        prompt="Analyze this sales data and return a brief summary."
    )
    
    assert "analysis" in result
    assert "metadata" in result
    assert result["metadata"]["model"] == test_config["aws_bedrock_model_id"]
