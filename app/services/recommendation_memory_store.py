"""Recommendation memory store for managing storage and retrieval of recommendations with embeddings."""

import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.clients.interfaces import IDataClient, IEmbeddingClient

logger = logging.getLogger(__name__)


class RecommendationMemoryStore:
    """Manages storage and retrieval of recommendations with embeddings."""
    
    def __init__(self, data_client: IDataClient, embedding_client: IEmbeddingClient):
        """Initialize the recommendation memory store.
        
        Args:
            data_client: Client for MongoDB operations
            embedding_client: Client for generating embeddings
            
        Raises:
            ValueError: If either client is None
        """
        if data_client is None:
            raise ValueError("data_client cannot be None")
        if embedding_client is None:
            raise ValueError("embedding_client cannot be None")
            
        self._data_client = data_client
        self._embedding_client = embedding_client
        self._collection_name = "memory_embeddings"  # Exclusive collection for memory system
        logger.info(f"RecommendationMemoryStore initialized (collection: {self._collection_name})")
    
    def store_recommendation(
        self,
        executive_id: str,
        client_id: str,
        recommendation_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a recommendation with its embedding.
        
        Args:
            executive_id: ID of the executive
            client_id: ID of the client
            recommendation_text: Text of the recommendation
            metadata: Additional metadata to store
            
        Returns:
            ID of the stored recommendation
            
        Raises:
            ValueError: If required parameters are invalid
            ConnectionError: If storage fails after retries
        """
        if not executive_id:
            raise ValueError("executive_id cannot be empty")
        if not client_id:
            raise ValueError("client_id cannot be empty")
        if not recommendation_text or not recommendation_text.strip():
            raise ValueError("recommendation_text cannot be empty")
        
        # Generate embedding
        logger.debug(f"Generating embedding for recommendation (executive: {executive_id}, client: {client_id})")
        embedding = self._embedding_client.generate_embedding(recommendation_text)
        logger.debug(f"Embedding generated successfully (dimension: {len(embedding)})")
        
        # Prepare document for memory_embeddings collection
        doc = {
            "executive_id": executive_id,
            "client_id": client_id,
            "recommendation": recommendation_text,
            "embedding": embedding,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        # Store in MongoDB with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.debug(f"Storing recommendation (attempt {attempt + 1}/{max_retries})")
                result_id = self._data_client.insert_one(self._collection_name, doc)
                logger.info(f"Recommendation stored successfully (id: {result_id}, executive: {executive_id}, client: {client_id})")
                return result_id
            except Exception as e:
                if attempt == max_retries - 1:
                    raise ConnectionError(f"Failed to store recommendation after {max_retries} attempts: {str(e)}")
                wait_time = 2 ** attempt
                logger.warning(f"Storage attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                time.sleep(wait_time)
    
    def get_historical_recommendations(
        self,
        executive_id: str,
        client_id: str,
        days_back: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve historical recommendations for a specific executive and client.
        
        Args:
            executive_id: ID of the executive
            client_id: ID of the client
            days_back: Optional number of days to look back
            limit: Optional maximum number of recommendations to return
            
        Returns:
            List of recommendation documents with embeddings, ordered by timestamp (newest first)
            
        Raises:
            ValueError: If parameters are invalid
            ConnectionError: If retrieval fails
        """
        if not executive_id:
            raise ValueError("executive_id cannot be empty")
        if not client_id:
            raise ValueError("client_id cannot be empty")
        
        # Build filter for memory_embeddings collection
        filter_doc = {
            "executive_id": executive_id,
            "client_id": client_id
        }
        
        # Add time range filter if specified
        if days_back is not None:
            if days_back <= 0:
                raise ValueError("days_back must be positive")
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            filter_doc["timestamp"] = {"$gte": cutoff_date.isoformat()}
        
        # Build query parameters
        query_params = {
            "collection": self._collection_name,
            "filter": filter_doc,
            "projection": None  # Return all fields including embedding
        }
        
        if limit is not None:
            if limit <= 0:
                raise ValueError("limit must be positive")
            query_params["limit"] = limit
        
        try:
            logger.debug(f"Retrieving historical recommendations (executive: {executive_id}, client: {client_id}, days_back: {days_back}, limit: {limit})")
            results = self._data_client.query(query_params)
            
            # Sort by timestamp descending (newest first)
            results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            logger.info(f"Retrieved {len(results)} historical recommendations (executive: {executive_id}, client: {client_id})")
            return results
        except Exception as e:
            raise ConnectionError(f"Failed to retrieve historical recommendations: {str(e)}")
