"""
Client layer for external service integrations.
"""

from app.clients.interfaces import IDataClient, IAIClient, IEmbeddingClient
from app.clients.mongodb_client import MongoDBClient
from app.clients.aws_bedrock_client import AWSBedrockClient
from app.clients.email_client import IEmailClient, SendGridEmailClient
from app.clients.embedding_client import EmbeddingClient

__all__ = [
    'IDataClient',
    'IAIClient',
    'IEmbeddingClient',
    'MongoDBClient',
    'AWSBedrockClient',
    'IEmailClient',
    'SendGridEmailClient',
    'EmbeddingClient',
]
