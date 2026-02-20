"""
Memory reset service for intelligent management of recommendation memory.

This service handles the intelligent reset of recommendation memory when there are
insufficient available clients for generating new recommendations. It implements
a tiered reset strategy based on client availability.

Reset Strategy:
    - 0 clients available: Full reset (delete all embeddings for executive)
    - 1-2 clients available: Partial reset (delete oldest embeddings to free up clients)
    - 3+ clients available: No action needed

Example:
    >>> reset_service = MemoryResetService(memory_store, mongodb_client)
    >>> result = reset_service.check_and_reset_if_needed(
    ...     executive_id="123",
    ...     available_clients=[{"id": "client1"}, {"id": "client2"}],
    ...     required_recommendations=3
    ... )
    >>> print(result["action"])  # "partial_reset"
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MemoryResetService:
    """Service for managing intelligent reset of recommendation memory.
    
    This service monitors client availability and performs strategic memory resets
    to ensure sufficient clients are available for generating recommendations.
    
    Attributes:
        _memory_store: Instance of RecommendationMemoryStore for memory operations
        _mongodb_client: MongoDB client for direct database access
    """
    
    def __init__(self, memory_store, mongodb_client):
        """Initialize the memory reset service.
        
        Args:
            memory_store: Instance of RecommendationMemoryStore
            mongodb_client: MongoDB client for direct database access
            
        Raises:
            ValueError: If either parameter is None
        """
        if memory_store is None:
            raise ValueError("memory_store cannot be None")
        if mongodb_client is None:
            raise ValueError("mongodb_client cannot be None")
            
        self._memory_store = memory_store
        self._mongodb_client = mongodb_client
    
    def check_and_reset_if_needed(
        self,
        executive_id: str,
        available_clients: List[Dict[str, Any]],
        required_recommendations: int = 3,
        days_threshold: int = 7,
        reference_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check client availability and perform memory reset if needed.
        
        Implements a tiered reset strategy:
        - 0 clients available: Delete ALL embeddings for the executive (full reset)
        - 1-2 clients available: Use available + delete oldest to complete (partial reset)
        - 3+ clients available: No action needed
        
        Args:
            executive_id: ID of the executive to check
            available_clients: List of currently available clients (after pre-filtering)
            required_recommendations: Number of recommendations required (default: 3)
            days_threshold: Cooldown period in days (default: 7)
            reference_date: Reference date for analysis (ISO format string)
            
        Returns:
            Dictionary with reset action details:
                {
                    "action": "none" | "partial_reset" | "full_reset",
                    "clients_available": int,
                    "clients_needed": int,
                    "embeddings_deleted": int,
                    "message": str
                }
                
        Example:
            >>> result = service.check_and_reset_if_needed(
            ...     executive_id="123",
            ...     available_clients=[{"id": "1"}, {"id": "2"}],
            ...     required_recommendations=3
            ... )
            >>> print(result["action"])  # "partial_reset"
            >>> print(result["embeddings_deleted"])  # 1
        """
        # Calculate availability metrics
        clients_available = len(available_clients)
        clients_needed = required_recommendations - clients_available
        
        logger.info(
            f"Checking memory for executive {executive_id}: "
            f"{clients_available} clients available, {required_recommendations} required"
        )
        
        # Case 1: Sufficient clients available - no action needed
        if clients_available >= required_recommendations:
            return {
                "action": "none",
                "clients_available": clients_available,
                "clients_needed": 0,
                "embeddings_deleted": 0,
                "message": f"Sufficient clients available ({clients_available})"
            }
        
        # Case 2: Zero clients available - perform full reset
        if clients_available == 0:
            logger.warning(
                f"Executive {executive_id}: 0 clients available. "
                f"Executing FULL RESET"
            )
            
            # Delete all embeddings for this executive
            deleted_count = self._delete_executive_embeddings(executive_id)
            
            return {
                "action": "full_reset",
                "clients_available": 0,
                "clients_needed": required_recommendations,
                "embeddings_deleted": deleted_count,
                "message": (
                    f"Full reset: deleted {deleted_count} embeddings. "
                    f"All clients now available."
                )
            }
        
        # Case 3: 1-2 clients available - perform partial reset
        logger.warning(
            f"Executive {executive_id}: Only {clients_available} clients available. "
            f"Executing PARTIAL RESET"
        )
        
        # Get recently recommended clients sorted by timestamp (oldest first)
        recommended_clients = self._get_recommended_clients_sorted(
            executive_id,
            days_threshold,
            reference_date
        )
        
        # Calculate how many embeddings to delete to free up clients
        embeddings_to_delete = clients_needed
        
        # Delete the oldest embeddings to free up clients
        deleted_count = self._delete_oldest_embeddings(
            executive_id,
            recommended_clients[:embeddings_to_delete]
        )
        
        return {
            "action": "partial_reset",
            "clients_available": clients_available,
            "clients_needed": clients_needed,
            "embeddings_deleted": deleted_count,
            "message": (
                f"Partial reset: deleted {deleted_count} oldest embeddings. "
                f"Now {clients_available + deleted_count} clients available."
            )
        }
    
    def _delete_executive_embeddings(self, executive_id: str) -> int:
        """Delete ALL embeddings for a specific executive.
        
        This is used for full reset when no clients are available.
        
        Args:
            executive_id: ID of the executive
            
        Returns:
            Number of embeddings deleted
            
        Example:
            >>> count = service._delete_executive_embeddings("123")
            >>> print(f"Deleted {count} embeddings")
        """
        try:
            # Access memory_embeddings collection directly
            collection = self._mongodb_client._database['memory_embeddings']
            
            # Delete all embeddings for this executive
            result = collection.delete_many({"executive_id": str(executive_id)})
            
            deleted_count = result.deleted_count
            logger.info(f"Deleted {deleted_count} embeddings for executive {executive_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting embeddings for executive {executive_id}: {str(e)}")
            return 0
    
    def _get_recommended_clients_sorted(
        self,
        executive_id: str,
        days_threshold: int,
        reference_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recently recommended clients sorted by timestamp (oldest first).
        
        Retrieves clients that were recommended within the cooldown period,
        sorted by their oldest recommendation timestamp.
        
        Args:
            executive_id: ID of the executive
            days_threshold: Cooldown period in days
            reference_date: Reference date for filtering (ISO format string)
            
        Returns:
            List of client dictionaries with timestamps, sorted by age:
                [
                    {
                        "client_id": str,
                        "oldest_timestamp": str,
                        "count": int
                    },
                    ...
                ]
                
        Example:
            >>> clients = service._get_recommended_clients_sorted("123", 7)
            >>> print(clients[0]["client_id"])  # Oldest recommended client
        """
        try:
            # Calculate cutoff date for cooldown period
            if reference_date:
                ref_dt = datetime.fromisoformat(reference_date.split('T')[0])
            else:
                ref_dt = datetime.utcnow()
            
            cutoff_date = ref_dt - timedelta(days=days_threshold)
            cutoff_str = cutoff_date.isoformat()
            
            # Access memory_embeddings collection
            collection = self._mongodb_client._database['memory_embeddings']
            
            # Aggregation pipeline to find recent recommendations
            pipeline = [
                # Filter: executive's recommendations within cooldown period
                {"$match": {"executive_id": str(executive_id), "timestamp": {"$gt": cutoff_str}}},
                # Sort by timestamp (oldest first)
                {"$sort": {"timestamp": 1}},
                # Group by client_id to get unique clients
                {"$group": {
                    "_id": "$client_id",
                    "client_id": {"$first": "$client_id"},
                    "oldest_timestamp": {"$first": "$timestamp"},
                    "count": {"$sum": 1}
                }}
            ]
            
            results = list(collection.aggregate(pipeline))
            logger.info(f"Found {len(results)} recently recommended clients for executive {executive_id}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving recommended clients: {str(e)}")
            return []
    
    def _delete_oldest_embeddings(
        self,
        executive_id: str,
        clients_to_free: List[Dict[str, Any]]
    ) -> int:
        """Delete embeddings for specified clients to free them up.
        
        Removes all embeddings associated with the given clients for the executive,
        making those clients available for new recommendations.
        
        Args:
            executive_id: ID of the executive
            clients_to_free: List of client dictionaries whose embeddings should be deleted
            
        Returns:
            Number of embeddings deleted
            
        Example:
            >>> clients = [{"client_id": "1"}, {"client_id": "2"}]
            >>> count = service._delete_oldest_embeddings("123", clients)
            >>> print(f"Freed {len(clients)} clients by deleting {count} embeddings")
        """
        if not clients_to_free:
            return 0
        
        try:
            # Access memory_embeddings collection
            collection = self._mongodb_client._database['memory_embeddings']
            
            # Extract client IDs from the list
            client_ids = [c['client_id'] for c in clients_to_free]
            
            # Delete embeddings for these specific clients
            result = collection.delete_many({
                "executive_id": str(executive_id),
                "client_id": {"$in": client_ids}
            })
            
            deleted_count = result.deleted_count
            logger.info(f"Deleted {deleted_count} embeddings from {len(client_ids)} clients for executive {executive_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting specific embeddings: {str(e)}")
            return 0
