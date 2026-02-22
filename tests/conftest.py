"""Pytest configuration and shared fixtures."""

import pytest
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration."""
    return {
        "mongodb_uri": os.getenv("MONGODB_URI"),
        "mongodb_database": os.getenv("MONGODB_DATABASE"),
        "aws_region": os.getenv("AWS_REGION", "us-east-1"),
        "aws_bedrock_model_id": os.getenv("AWS_BEDROCK_MODEL_ID"),
        "sendgrid_api_key": os.getenv("SENDGRID_API_KEY"),
        "sendgrid_from_email": os.getenv("SENDGRID_FROM_EMAIL"),
        "sendgrid_test_email": os.getenv("SENDGRID_TEST_EMAIL"),
        "embedding_api_key": os.getenv("EMBEDDING_API_KEY"),
        "embedding_endpoint": os.getenv("EMBEDDING_ENDPOINT"),
        "embedding_model_name": os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-3-large"),
        "api_base_url": os.getenv("API_BASE_URL", "http://localhost:8000")
    }


@pytest.fixture(scope="session")
def testing_collections():
    """Provide names of testing collections."""
    return {
        "executives": "testing_ejecutivos_border_cases",
        "memory": "testing_memory_embedding"
    }
