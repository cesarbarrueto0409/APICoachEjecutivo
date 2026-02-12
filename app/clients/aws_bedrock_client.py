"""AWS Bedrock client implementation."""

import os
import re
from typing import List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from app.clients.interfaces import IAIClient


class AWSBedrockClient(IAIClient):
    """AWS Bedrock implementation of the AI client interface."""
    
    def __init__(self, region: str, model_id: str):
        if not region:
            raise ValueError("AWS region cannot be empty")
        if not model_id:
            raise ValueError("AWS Bedrock model ID cannot be empty")
            
        self._region = region
        self._model_id = model_id
        
        # Pricing configuration
        self._input_price_per_1k_tokens = float(os.getenv("AWS_INPUT_PRICE_PER_1K_TOKENS", "0.0008"))
        self._output_price_per_1k_tokens = float(os.getenv("AWS_OUTPUT_PRICE_PER_1K_TOKENS", "0.0032"))
        
        # Validate model identifier
        self._validate_model_id(self._model_id)
        
        self._client: Optional[Any] = None
    
    def _validate_model_id(self, model_id: str) -> None:
        """Validate model id format."""
        if not model_id:
            raise ValueError(
                "AWS_BEDROCK_MODEL_ID is not set. Set it to the model ID or inference profile ARN."
            )
        
        # Accept both short model names and ARNs
        # Short format: amazon.nova-lite-v1:0
        # ARN format: arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1
        
        # If it's an ARN, validate basic structure
        if model_id.startswith("arn:"):
            if not model_id.startswith("arn:aws:bedrock:"):
                raise ValueError(
                    "AWS_BEDROCK_MODEL_ID does not look like a valid Bedrock ARN. "
                    "Expected format: arn:aws:bedrock:<region>::inference-profile/<name>."
                )
    
    def connect(self) -> None:
        """Establish connection to AWS Bedrock service."""
        try:
            # boto3 will automatically use AWS_BEARER_TOKEN_BEDROCK from environment
            # No need to pass credentials explicitly
            self._client = boto3.client(
                service_name="bedrock-runtime",
                region_name=self._region
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect to AWS Bedrock service: {str(e)}") from e
    
    def analyze(self, data: List[Dict[str, Any]], prompt: Optional[str] = None) -> Dict[str, Any]:
        """Send data to AWS Bedrock model for analysis."""
        if self._client is None:
            raise ConnectionError("Client not connected. Call connect() first.")
        
        try:
            messages = self._format_request(data, prompt)
            response = self._invoke_model(messages)
            return self._parse_response(response)
        except ClientError as e:
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            raise Exception(f"AWS Bedrock service error: {error_msg}") from e
        except Exception as e:
            raise Exception(f"Failed to analyze data: {str(e)}") from e
    
    def _format_request(self, data: List[Dict[str, Any]], prompt: Optional[str] = None) -> List[Dict[str, Any]]:
        """Format data and prompt for AWS Bedrock API."""
        default_prompt = "Analyze the following data and provide insights."
        analysis_prompt = prompt if prompt else default_prompt
        data_str = "\n".join([str(item) for item in data])
        
        # Format messages for Bedrock converse API
        messages = [
            {
                "role": "user",
                "content": [{"text": f"{analysis_prompt}\n\nData:\n{data_str}"}]
            }
        ]
        
        return messages
    
    def _invoke_model(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Invoke AWS Bedrock model using converse API."""
        system_prompt = """You are a data analysis assistant. Provide thorough, complete responses 
        and analyze the data comprehensively."""
        
        try:
            response = self._client.converse(
                modelId=self._model_id,
                messages=messages,
                system=[{"text": system_prompt}],
                inferenceConfig={
                    "maxTokens": 3000,
                    "temperature": 0.2
                }
            )
            return response
        except ClientError as e:
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            raise RuntimeError(
                f"AWS Bedrock Converse failed for model '{self._model_id}': {error_msg}"
            ) from e
    
    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AWS Bedrock response into standardized format."""
        try:
            # Extract text from response
            analysis_text = response["output"]["message"]["content"][0]["text"]
            
            # Clean markdown code blocks from JSON responses
            analysis_text = self._clean_markdown_json(analysis_text)
            
            # Extract metadata
            metadata = {
                "model": self._model_id,
                "region": self._region
            }
            
            # Extract token usage if available
            if "usage" in response:
                usage = response["usage"]
                metadata["tokens"] = {
                    "prompt": usage.get("inputTokens"),
                    "completion": usage.get("outputTokens"),
                    "total": usage.get("totalTokens")
                }
                
                # Calculate cost if token usage is available
                if "inputTokens" in usage and "outputTokens" in usage:
                    input_cost = (usage["inputTokens"] / 1000) * self._input_price_per_1k_tokens
                    output_cost = (usage["outputTokens"] / 1000) * self._output_price_per_1k_tokens
                    metadata["cost"] = {
                        "input": round(input_cost, 6),
                        "output": round(output_cost, 6),
                        "total": round(input_cost + output_cost, 6)
                    }
            
            return {
                "analysis": analysis_text,
                "confidence": None,
                "metadata": metadata
            }
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError("Unexpected response structure from Bedrock converse call") from e
    
    def _clean_markdown_json(self, text: str) -> str:
        """Remove markdown code block formatting from JSON responses."""
        # Remove ```json and ``` markers
        text = re.sub(r'^```json\s*\n', '', text, flags=re.MULTILINE)
        text = re.sub(r'^```\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n```\s*$', '', text, flags=re.MULTILINE)
        return text.strip()
