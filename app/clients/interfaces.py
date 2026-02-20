"""
Client interfaces for external service integrations.

This module defines abstract base classes (interfaces) for all external service clients
used in the application. These interfaces ensure consistent behavior across different
implementations and facilitate dependency injection and testing.

The module provides three main interfaces:
    - IDataClient: For database operations (MongoDB)
    - IAIClient: For AI model interactions (AWS Bedrock)
    - IEmbeddingClient: For text embedding generation (OpenAI)

Example:
    Implementing a custom data client:
    
    >>> class CustomDataClient(IDataClient):
    ...     def connect(self) -> None:
    ...         # Custom connection logic
    ...         pass
    ...     
    ...     def query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    ...         # Custom query logic
    ...         return []
    ...     
    ...     def disconnect(self) -> None:
    ...         # Custom disconnection logic
    ...         pass
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class IDataClient(ABC):
    """
    Abstract interface for data retrieval clients.
    
    This interface defines the contract for all data source clients in the application.
    Implementations must provide methods for connecting, querying, and disconnecting
    from data sources.
    
    Typical implementations include:
        - MongoDB clients for document databases
        - SQL clients for relational databases
        - API clients for external data services
    
    Example:
        Using a data client implementation:
        
        >>> client = MongoDBClient("mongodb://localhost", "mydb")
        >>> client.connect()
        >>> results = client.query({"collection": "users", "filter": {"active": True}})
        >>> print(f"Found {len(results)} active users")
        >>> client.disconnect()
    """
    
    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to the data source.
        
        This method should initialize the connection to the underlying data source
        and verify that the connection is successful. It should be called before
        any query operations.
        
        Raises:
            ConnectionError: If connection cannot be established
            
        Example:
            >>> client = MongoDBClient("mongodb://localhost", "mydb")
            >>> client.connect()  # Establishes connection
        """
        pass
    
    @abstractmethod
    def query(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a query and return results.
        
        This method executes a query against the data source using the provided
        parameters. The structure of query_params depends on the implementation
        but typically includes collection/table name and filter criteria.
        
        Args:
            query_params: Dictionary containing query parameters. Common keys:
                - collection: Name of the collection/table to query
                - filter: Filter criteria for the query
                - projection: Fields to include/exclude in results
                - limit: Maximum number of results to return
                - pipeline: Aggregation pipeline (for MongoDB)
        
        Returns:
            List of dictionaries representing query results. Each dictionary
            represents one document/row from the data source.
        
        Raises:
            ConnectionError: If not connected to data source
            ValueError: If query_params are invalid
            Exception: If query execution fails
            
        Example:
            Simple query:
            >>> results = client.query({
            ...     "collection": "users",
            ...     "filter": {"age": {"$gt": 18}},
            ...     "limit": 10
            ... })
            
            Aggregation pipeline:
            >>> results = client.query({
            ...     "collection": "sales",
            ...     "pipeline": [
            ...         {"$match": {"year": 2024}},
            ...         {"$group": {"_id": "$region", "total": {"$sum": "$amount"}}}
            ...     ]
            ... })
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """
        Close connection to the data source.
        
        This method should cleanly close the connection and release any resources
        held by the client. It should be called when the client is no longer needed.
        
        Example:
            >>> client.disconnect()  # Closes connection and cleans up resources
        """
        pass


class IAIClient(ABC):
    """
    Abstract interface for AI service clients.
    
    This interface defines the contract for AI model clients that perform
    data analysis and generate insights. Implementations interact with
    various AI services like AWS Bedrock, OpenAI, or custom models.
    
    The interface focuses on analysis operations where structured data
    is sent to an AI model along with a prompt, and the model returns
    analysis results.
    
    Example:
        Using an AI client implementation:
        
        >>> client = AWSBedrockClient("us-east-1", "amazon-nova-lite-v1")
        >>> client.connect()
        >>> data = [{"sales": 1000, "region": "North"}]
        >>> prompt = "Analyze sales performance by region"
        >>> result = client.analyze(data, prompt)
        >>> print(result["analysis"])
    """
    
    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to the AI service.
        
        This method initializes the connection to the AI service and verifies
        authentication credentials. It should be called before any analysis
        operations.
        
        Raises:
            ConnectionError: If connection cannot be established
            
        Example:
            >>> client = AWSBedrockClient("us-east-1", "model-id")
            >>> client.connect()  # Initializes boto3 client
        """
        pass
    
    @abstractmethod
    def analyze(self, data: List[Dict[str, Any]], prompt: str = None) -> Dict[str, Any]:
        """
        Send data to AI model for analysis.
        
        This method sends structured data along with an optional prompt to the
        AI model and returns the analysis results. The model processes the data
        according to the prompt and generates insights, recommendations, or
        structured responses.
        
        Args:
            data: List of dictionaries containing the data to analyze. Each
                dictionary represents one data point or record. The structure
                depends on the use case but should be JSON-serializable.
            prompt: Optional text prompt providing instructions to the AI model.
                If not provided, a default analysis prompt may be used.
        
        Returns:
            Dictionary containing analysis results with the following structure:
                {
                    "analysis": str or dict,  # The AI-generated analysis
                    "confidence": float or None,  # Confidence score if available
                    "metadata": {
                        "model": str,  # Model identifier
                        "tokens": dict,  # Token usage statistics
                        "cost": dict  # Cost breakdown if available
                    }
                }
        
        Raises:
            ConnectionError: If not connected to AI service
            ValueError: If data or prompt are invalid
            Exception: If analysis fails
            
        Example:
            Basic analysis:
            >>> data = [
            ...     {"executive": "John", "sales": 50000, "target": 60000},
            ...     {"executive": "Jane", "sales": 75000, "target": 70000}
            ... ]
            >>> prompt = "Analyze sales performance and provide recommendations"
            >>> result = client.analyze(data, prompt)
            >>> print(result["analysis"])
            
            With metadata:
            >>> result = client.analyze(data, prompt)
            >>> print(f"Tokens used: {result['metadata']['tokens']['total']}")
            >>> print(f"Cost: ${result['metadata']['cost']['total']}")
        """
        pass


class IEmbeddingClient(ABC):
    """
    Abstract interface for embedding generation services.
    
    This interface defines the contract for text embedding clients that convert
    text into high-dimensional vector representations. These embeddings are used
    for semantic similarity comparisons, clustering, and recommendation systems.
    
    Implementations typically use pre-trained language models like:
        - OpenAI's text-embedding-3-large (3072 dimensions)
        - Sentence transformers
        - Custom embedding models
    
    Example:
        Using an embedding client:
        
        >>> client = EmbeddingClient(api_key="key", endpoint="https://api.openai.com/v1/embeddings")
        >>> client.connect()
        >>> embedding = client.generate_embedding("Call the client urgently")
        >>> print(f"Embedding dimension: {len(embedding)}")  # 3072
        >>> print(f"First 5 values: {embedding[:5]}")
    """
    
    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to the embedding service.
        
        This method initializes the HTTP session and verifies authentication
        with the embedding service. It should be called before generating
        any embeddings.
        
        Raises:
            ConnectionError: If connection cannot be established
            
        Example:
            >>> client = EmbeddingClient(api_key="key", endpoint="https://api.openai.com/v1/embeddings")
            >>> client.connect()  # Initializes HTTP session with auth headers
        """
        pass
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for the given text.
        
        This method converts input text into a high-dimensional vector representation
        that captures semantic meaning. The resulting embedding can be used for:
            - Semantic similarity comparisons (cosine similarity)
            - Clustering similar texts
            - Recommendation filtering
            - Duplicate detection
        
        Args:
            text: Input text to embed. Should be non-empty and meaningful.
                Typical inputs include:
                - Recommendation text: "Call client urgently about risk"
                - Search queries: "high-value clients with claims"
                - Document content: "Client has 3 active complaints..."
            
        Returns:
            List of floats representing the embedding vector. The dimension
            depends on the model:
                - text-embedding-3-large: 3072 dimensions
                - text-embedding-ada-002: 1536 dimensions
                - sentence-transformers: 384-768 dimensions
            
        Raises:
            ConnectionError: If not connected to service
            ValueError: If text is empty or invalid
        """
        pass
    
    @abstractmethod
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            ConnectionError: If not connected to service
            ValueError: If texts list is empty or contains invalid entries
        """
        pass
