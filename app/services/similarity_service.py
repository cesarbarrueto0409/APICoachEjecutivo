"""Service for computing semantic similarity and applying cooldown logic."""

import logging
import math
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SimilarityService:
    """Service for computing semantic similarity and applying cooldown logic."""
    
    def __init__(self, similarity_threshold: float = 0.85, cooldown_days: int = 14):
        """Initialize SimilarityService with threshold and cooldown configuration.
        
        Args:
            similarity_threshold: Threshold for classifying recommendations as similar (0-1)
            cooldown_days: Number of days for cooldown period
            
        Raises:
            ValueError: If threshold is not in [0, 1] or cooldown_days is not positive
        """
        if not 0 <= similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")
        if cooldown_days <= 0:
            raise ValueError("cooldown_days must be positive")
            
        self._similarity_threshold = similarity_threshold
        self._cooldown_days = cooldown_days
        logger.info(f"SimilarityService initialized (threshold: {similarity_threshold}, cooldown: {cooldown_days} days)")
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors.
        
        Args:
            vec1: First embedding vector
            vec2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1
            
        Raises:
            ValueError: If vectors are invalid or have different dimensions
        """
        if not vec1 or not vec2:
            raise ValueError("Vectors cannot be empty")
        
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")
        
        # Compute dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        
        # Compute magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            raise ValueError("Vector magnitude cannot be zero")
        
        # Compute cosine similarity
        similarity = dot_product / (magnitude1 * magnitude2)
        
        # Clamp to [0, 1] range (handle floating point errors)
        clamped_similarity = max(0.0, min(1.0, similarity))
        logger.debug(f"Computed cosine similarity: {clamped_similarity:.4f}")
        return clamped_similarity
    
    def is_similar(self, vec1: List[float], vec2: List[float]) -> bool:
        """Check if two vectors are similar based on threshold.
        
        Args:
            vec1: First embedding vector
            vec2: Second embedding vector
            
        Returns:
            True if similarity exceeds threshold, False otherwise
        """
        similarity = self.cosine_similarity(vec1, vec2)
        return similarity >= self._similarity_threshold
    
    def check_recommendation_similarity(
        self,
        new_recommendation: Dict[str, Any],
        historical_recommendations: List[Dict[str, Any]]
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if a new recommendation is similar to any historical one.
        
        Args:
            new_recommendation: Dict with 'embedding' key
            historical_recommendations: List of dicts with 'embedding' and 'timestamp' keys
            
        Returns:
            Tuple of (should_filter, matching_recommendation)
            - should_filter: True if recommendation should be filtered out
            - matching_recommendation: The historical recommendation that matched (if any)
            
        Raises:
            ValueError: If recommendations don't have required fields
        """
        if "embedding" not in new_recommendation:
            raise ValueError("new_recommendation must have 'embedding' field")
        
        new_embedding = new_recommendation["embedding"]
        
        for historical in historical_recommendations:
            if "embedding" not in historical:
                continue  # Skip recommendations without embeddings
            
            if "timestamp" not in historical:
                continue  # Skip recommendations without timestamp
            
            historical_embedding = historical["embedding"]
            
            # Check similarity
            if self.is_similar(new_embedding, historical_embedding):
                # Check cooldown period
                historical_time = datetime.fromisoformat(historical["timestamp"])
                time_diff = datetime.utcnow() - historical_time
                
                if time_diff.days < self._cooldown_days:
                    # Within cooldown - filter out
                    logger.info(f"Recommendation filtered: similar to one from {time_diff.days} days ago (within {self._cooldown_days} day cooldown)")
                    return (True, historical)
                else:
                    # Outside cooldown - allow but mark as "sin cambios"
                    logger.info(f"Recommendation marked as 'repeated_no_change': similar to one from {time_diff.days} days ago (outside cooldown)")
                    return (False, historical)
        
        # No similar recommendation found
        return (False, None)
    
    def filter_recommendations(
        self,
        new_recommendations: List[Dict[str, Any]],
        historical_recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Filter new recommendations based on similarity to historical ones.
        
        Args:
            new_recommendations: List of new recommendations with embeddings
            historical_recommendations: List of historical recommendations with embeddings
            
        Returns:
            Filtered list of recommendations with 'status' field added:
            - 'new': Completely new recommendation
            - 'repeated_no_change': Similar to old recommendation outside cooldown
            
        Raises:
            ValueError: If recommendations are invalid
        """
        if not isinstance(new_recommendations, list):
            raise ValueError("new_recommendations must be a list")
        
        if not isinstance(historical_recommendations, list):
            raise ValueError("historical_recommendations must be a list")
        
        filtered = []
        
        for new_rec in new_recommendations:
            should_filter, matching_rec = self.check_recommendation_similarity(
                new_rec, historical_recommendations
            )
            
            if should_filter:
                # Skip this recommendation (within cooldown)
                logger.debug(f"Filtered recommendation due to similarity within cooldown period")
                continue
            
            # Add status field
            if matching_rec is not None:
                new_rec["status"] = "repeated_no_change"
                new_rec["previous_timestamp"] = matching_rec.get("timestamp")
            else:
                new_rec["status"] = "new"
            
            filtered.append(new_rec)
        
        # Ensure at least one recommendation if input was non-empty
        if new_recommendations and not filtered:
            # Return the first recommendation marked as forced
            logger.warning(f"All {len(new_recommendations)} recommendations were filtered - forcing first recommendation")
            first_rec = new_recommendations[0].copy()
            first_rec["status"] = "forced"
            filtered.append(first_rec)
        
        logger.info(f"Filtered recommendations: {len(new_recommendations)} -> {len(filtered)} (new: {sum(1 for r in filtered if r.get('status') == 'new')}, repeated: {sum(1 for r in filtered if r.get('status') == 'repeated_no_change')}, forced: {sum(1 for r in filtered if r.get('status') == 'forced')})")
        return filtered
