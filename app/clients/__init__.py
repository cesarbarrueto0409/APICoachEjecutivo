"""
Client layer for external service integrations.
"""

from app.clients.interfaces import IDataClient, IAIClient
from app.clients.mongodb_client import MongoDBClient
from app.clients.aws_bedrock_client import AWSBedrockClient
from app.clients.email_client import IEmailClient, SendGridEmailClient

__all__ = [
    'IDataClient',
    'IAIClient',
    'MongoDBClient',
    'AWSBedrockClient',
    'IEmailClient',
    'SendGridEmailClient',
]
