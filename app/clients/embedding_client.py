"""Client for text embedding generation services."""

import logging
import os

# Configure SSL certificates BEFORE importing requests
if not os.environ.get('SSL_CERT_FILE') and not os.environ.get('REQUESTS_CA_BUNDLE'):
    try:
        import certifi
        cert_path = certifi.where()
        os.environ['SSL_CERT_FILE'] = cert_path
        os.environ['REQUESTS_CA_BUNDLE'] = cert_path
    except ImportError:
        # Fallback to system certificates (for Docker/Linux)
        system_certs = [
            '/etc/ssl/certs/ca-certificates.crt',
            '/etc/ssl/certs/ca-bundle.crt',
            '/etc/pki/tls/certs/ca-bundle.crt'
        ]
        for cert_path in system_certs:
            if os.path.exists(cert_path):
                os.environ['SSL_CERT_FILE'] = cert_path
                os.environ['REQUESTS_CA_BUNDLE'] = cert_path
                break

import requests
from typing import List
from app.clients.interfaces import IEmbeddingClient

logger = logging.getLogger(__name__)


class EmbeddingClient(IEmbeddingClient):
    """Client for text-embedding-3-large service."""
    
    def __init__(self, api_key: str, endpoint: str, model_name: str = "text-embedding-3-large"):
        """Initialize the embedding client.
        
        Args:
            api_key: API key for authentication
            endpoint: API endpoint URL
            model_name: Name of the embedding model to use
            
        Raises:
            ValueError: If any parameter is empty or invalid
        """
        if not api_key:
            raise ValueError("api_key cannot be empty")
        if not endpoint:
            raise ValueError("endpoint cannot be empty")
        if not model_name:
            raise ValueError("model_name cannot be empty")
            
        self._api_key = api_key
        self._endpoint = endpoint
        self._model_name = model_name
        self._session = None
    
    def connect(self) -> None:
        """Initialize HTTP session with headers."""
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        })
        logger.info(f"Connected to embedding service: {self._endpoint} (model: {self._model_name})")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate single embedding vector."""
        if not text or not text.strip():
            raise ValueError("text cannot be empty")
        
        if self._session is None:
            raise ConnectionError("Not connected. Call connect() first.")
        
        payload = {"input": text, "model": self._model_name}
        
        response = self._session.post(self._endpoint, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        embedding = data["data"][0]["embedding"]
        
        logger.debug(f"Generated embedding for text (length: {len(text)} chars, vector dim: {len(embedding)})")
        return embedding
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            raise ValueError("texts list cannot be empty")
        
        if any(not text or not text.strip() for text in texts):
            raise ValueError("texts list contains empty or whitespace-only strings")
        
        if self._session is None:
            raise ConnectionError("Not connected. Call connect() first.")
        
        payload = {"input": texts, "model": self._model_name}
        
        response = self._session.post(self._endpoint, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]
        
        logger.debug(f"Generated {len(embeddings)} embeddings in batch (vector dim: {len(embeddings[0]) if embeddings else 0})")
        return embeddings
