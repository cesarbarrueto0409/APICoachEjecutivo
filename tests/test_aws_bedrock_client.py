"""
Unit tests for AWSBedrockClient implementation.

These tests verify the basic functionality of the AWSBedrockClient class,
including initialization, connection handling, and request/response formatting.
"""

import pytest
from app.clients.aws_bedrock_client import AWSBedrockClient


class TestAWSBedrockClientInitialization:
    """Test AWSBedrockClient initialization and validation."""
    
    def test_init_with_valid_credentials(self):
        """Test that client initializes with valid region and model ID."""
        client = AWSBedrockClient(
            region="us-east-1",
            model_id="arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1"
        )
        assert client._region == "us-east-1"
        assert client._model_id == "arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1"
        assert client._client is None  # Not connected yet
    
    def test_init_with_empty_region_raises_error(self):
        """Test that empty region raises ValueError."""
        with pytest.raises(ValueError, match="region cannot be empty"):
            AWSBedrockClient(
                region="",
                model_id="arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1"
            )
    
    def test_init_with_empty_model_id_raises_error(self):
        """Test that empty model ID raises ValueError."""
        with pytest.raises(ValueError, match="model ID cannot be empty"):
            AWSBedrockClient(region="us-east-1", model_id="")
    
    def test_init_with_short_model_name_raises_error(self):
        """Test that short model names are rejected."""
        with pytest.raises(ValueError, match="Invalid Bedrock model identifier"):
            AWSBedrockClient(region="us-east-1", model_id="amazon.nova-lite-v1")
    
    def test_init_with_invalid_arn_raises_error(self):
        """Test that invalid ARN format raises ValueError."""
        with pytest.raises(ValueError, match="does not look like a Bedrock ARN"):
            AWSBedrockClient(region="us-east-1", model_id="invalid-arn-format")


class TestAWSBedrockClientFormatRequest:
    """Test request formatting logic."""
    
    def test_format_request_with_default_prompt(self):
        """Test that _format_request creates proper structure with default prompt."""
        client = AWSBedrockClient(
            region="us-east-1",
            model_id="arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1"
        )
        
        data = [{"user": "john", "score": 85}]
        messages = client._format_request(data)
        
        assert isinstance(messages, list)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "content" in messages[0]
        assert isinstance(messages[0]["content"], list)
    
    def test_format_request_with_custom_prompt(self):
        """Test that _format_request uses custom prompt when provided."""
        client = AWSBedrockClient(
            region="us-east-1",
            model_id="arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1"
        )
        
        data = [{"user": "jane", "score": 92}]
        custom_prompt = "Analyze user performance"
        messages = client._format_request(data, prompt=custom_prompt)
        
        assert custom_prompt in messages[0]["content"][0]["text"]
    
    def test_format_request_includes_data(self):
        """Test that _format_request includes the data in the request."""
        client = AWSBedrockClient(
            region="us-east-1",
            model_id="arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1"
        )
        
        data = [{"id": 1, "value": "test"}]
        messages = client._format_request(data)
        
        # Data should be in the user message content
        user_content = messages[0]["content"][0]["text"]
        assert "id" in user_content or "1" in user_content


class TestAWSBedrockClientParseResponse:
    """Test response parsing logic."""
    
    def test_parse_response_with_valid_response(self):
        """Test that _parse_response extracts analysis text correctly."""
        client = AWSBedrockClient(
            region="us-east-1",
            model_id="arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1"
        )
        
        # Mock response object
        mock_response = {
            "output": {
                "message": {
                    "content": [{"text": "This is the analysis result"}]
                }
            },
            "usage": {
                "inputTokens": 100,
                "outputTokens": 50,
                "totalTokens": 150
            }
        }
        
        result = client._parse_response(mock_response)
        
        assert "analysis" in result
        assert result["analysis"] == "This is the analysis result"
        assert "confidence" in result
        assert "metadata" in result
        assert result["metadata"]["model"] == client._model_id
        assert "tokens" in result["metadata"]
        assert result["metadata"]["tokens"]["prompt"] == 100
        assert result["metadata"]["tokens"]["completion"] == 50
    
    def test_parse_response_with_cost_calculation(self):
        """Test that _parse_response calculates cost correctly."""
        client = AWSBedrockClient(
            region="us-east-1",
            model_id="arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1"
        )
        
        mock_response = {
            "output": {
                "message": {
                    "content": [{"text": "Analysis"}]
                }
            },
            "usage": {
                "inputTokens": 1000,
                "outputTokens": 500,
                "totalTokens": 1500
            }
        }
        
        result = client._parse_response(mock_response)
        
        assert "cost" in result["metadata"]
        assert "input" in result["metadata"]["cost"]
        assert "output" in result["metadata"]["cost"]
        assert "total" in result["metadata"]["cost"]


class TestAWSBedrockClientAnalyze:
    """Test analyze method behavior."""
    
    def test_analyze_without_connection_raises_error(self):
        """Test that analyze raises error when client is not connected."""
        client = AWSBedrockClient(
            region="us-east-1",
            model_id="arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1"
        )
        
        data = [{"test": "data"}]
        
        with pytest.raises(ConnectionError, match="not connected"):
            client.analyze(data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
