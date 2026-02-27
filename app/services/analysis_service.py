"""Analysis service for orchestrating data retrieval and AI analysis."""

import logging
import asyncio
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from app.clients.interfaces import IDataClient, IAIClient
from app.services.batch_processor import BatchProcessor, BatchConfig

if TYPE_CHECKING:
    from app.clients.interfaces import IEmbeddingClient
    from app.services.recommendation_memory_store import RecommendationMemoryStore
    from app.services.similarity_service import SimilarityService

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Custom exception for service layer errors."""
    
    def __init__(self, message: str, step: str, details: Optional[str] = None):
        self.message = message
        self.step = step
        self.details = details
        super().__init__(self.message)


class AnalysisService:
    """Service orchestrating the analysis workflow."""
    
    def __init__(
        self,
        data_client: IDataClient,
        ai_client: IAIClient,
        embedding_client: Optional["IEmbeddingClient"] = None,
        memory_store: Optional["RecommendationMemoryStore"] = None,
        similarity_service: Optional["SimilarityService"] = None,
        memory_enabled: bool = True,
        batch_config: Optional[BatchConfig] = None
    ):
        if data_client is None:
            raise ValueError("data_client cannot be None")
        if ai_client is None:
            raise ValueError("ai_client cannot be None")
            
        self._data_client = data_client
        self._ai_client = ai_client
        
        # Memory system components (optional for backward compatibility)
        self._embedding_client = embedding_client
        self._memory_store = memory_store
        self._similarity_service = similarity_service
        self._memory_enabled = memory_enabled and all([
            embedding_client, memory_store, similarity_service
        ])
        
        # Batch processing configuration
        self._batch_processor = BatchProcessor(batch_config or BatchConfig())
        
        if self._memory_enabled:
            logger.info("AnalysisService initialized with memory system enabled")
        else:
            logger.info("AnalysisService initialized without memory system (backward compatibility mode)")
        
        logger.info(
            f"Batch processing configured: size={self._batch_processor._config.batch_size}, "
            f"parallel={self._batch_processor._config.enable_parallel}"
        )
    
    def execute_analysis(
        self,
        query_params: Dict[str, Any],
        analysis_prompt: Optional[str] = None,
        current_date: Optional[str] = None,
        use_batch_processing: bool = False
    ) -> Dict[str, Any]:
        """
        Execute complete analysis workflow.
        
        Args:
            query_params: MongoDB query parameters
            analysis_prompt: Optional custom prompt
            current_date: Optional current date for context
            use_batch_processing: If True, use batch processing for large datasets
            
        Returns:
            Analysis results
        """
        if not isinstance(query_params, dict):
            raise ValueError("query_params must be a dictionary")
        
        if "collection" not in query_params:
            raise ValueError("query_params must include 'collection' field")
        
        # Query MongoDB
        data = self._data_client.query(query_params)
        
        # Validate data
        if data is None:
            raise ServiceError("Data retrieval returned None", "data_validation", "Expected list but got None")
        
        if not isinstance(data, list):
            raise ServiceError("Data retrieval returned invalid type", "data_validation", f"Expected list but got {type(data).__name__}")
        
        data_count = len(data)
        
        if data_count == 0:
            return {
                "status": "success",
                "data_count": 0,
                "analysis": {"analysis": "No data found matching the query criteria.", "confidence": None, "metadata": {}},
                "query_params": query_params
            }
        
        # Apply pre-filtering if memory system is enabled
        if self._memory_enabled and current_date:
            import os
            prefilter_enabled = os.getenv("PREFILTER_ENABLED", "true").lower() == "true"
            if prefilter_enabled:
                prefilter_days = int(os.getenv("PREFILTER_DAYS_THRESHOLD", "7"))
                data = self._ai_client._prefilter_clients_by_memory(
                    data, 
                    days_threshold=prefilter_days,
                    reference_date=current_date
                )
                logger.info(f"Pre-filtering applied: {len(data)} executives after filtering")
        
        # Enhance prompt with current date if provided
        enhanced_prompt = analysis_prompt
        if current_date:
            date_context = f"Current date for analysis context: {current_date}. "
            enhanced_prompt = date_context + (analysis_prompt or "Analyze the provided data.")
        
        # Decide whether to use batch processing
        # Use batch processing if explicitly requested OR if data is large
        should_use_batches = use_batch_processing or data_count > 10
        
        if should_use_batches:
            logger.info(f"Using batch processing for {data_count} executives")
            ai_result = self._execute_analysis_with_batches(data, enhanced_prompt)
        else:
            logger.info(f"Using single-batch processing for {data_count} executives")
            ai_result = self._ai_client.analyze(data, prompt=enhanced_prompt)
        
        # Validate AI response
        if ai_result is None:
            raise ServiceError("AI analysis returned None", "ai_validation", "Expected analysis results but got None")
        
        if not isinstance(ai_result, dict):
            raise ServiceError("AI analysis returned invalid type", "ai_validation", f"Expected dict but got {type(ai_result).__name__}")
        
        return {
            "status": "success",
            "data_count": data_count,
            "analysis": ai_result,
            "query_params": query_params
        }
    
    async def _execute_analysis_with_batches_async(
        self,
        data: List[Dict[str, Any]],
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute analysis using batch processing (async version).
        
        Args:
            data: List of executive data
            prompt: Analysis prompt
            
        Returns:
            Consolidated analysis results
        """
        # Divide into batches
        batches = self._batch_processor.divide_into_batches(data)
        
        # Process batches asynchronously
        results = await self._batch_processor.process_batches_async(
            batches,
            self._ai_client.analyze_batch,
            prompt
        )
        
        # Consolidate results
        consolidated = self._batch_processor.consolidate_results(results)
        
        # Check for failures
        if consolidated["metadata"]["failed_batches"] > 0:
            logger.warning(
                f"Batch processing completed with {consolidated['metadata']['failed_batches']} failures"
            )
        
        # Format as standard analysis result
        ejecutivos = consolidated["data"]
        
        # Create analysis JSON
        import json
        analysis_json = {
            "fecha_analisis": prompt.split("Fecha de corte: ")[1].split("\n")[0] if "Fecha de corte:" in prompt else "N/A",
            "ejecutivos": ejecutivos
        }
        
        return {
            "analysis": json.dumps(analysis_json, ensure_ascii=False),
            "confidence": None,
            "metadata": {
                "model": "batch_processed",
                "batch_metadata": consolidated["metadata"]
            }
        }
    
    def _execute_analysis_with_batches(
        self,
        data: List[Dict[str, Any]],
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute analysis using batch processing (sync wrapper).
        
        Args:
            data: List of executive data
            prompt: Analysis prompt
            
        Returns:
            Consolidated analysis results
        """
        # Try to get existing event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an async context, we can't use run_until_complete
            # Instead, we need to create a task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(self._execute_analysis_with_batches_async(data, prompt))
                )
                return future.result()
        except RuntimeError:
            # No event loop running, safe to create one
            return asyncio.run(self._execute_analysis_with_batches_async(data, prompt))
    
    def execute_analysis_with_memory(
        self,
        executive_id: str,
        client_id: str,
        query_params: Dict[str, Any],
        analysis_prompt: Optional[str] = None,
        current_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute analysis workflow with memory filtering.
        
        Args:
            executive_id: ID of the executive
            client_id: ID of the client
            query_params: MongoDB query parameters
            analysis_prompt: Optional custom prompt
            current_date: Optional current date for context
            
        Returns:
            Analysis results with filtered recommendations
        """
        # Step 1: Retrieve historical recommendations if memory enabled
        historical_recs = []
        if self._memory_enabled:
            logger.debug(f"Retrieving historical recommendations for executive {executive_id}, client {client_id}")
            historical_recs = self._memory_store.get_historical_recommendations(
                executive_id=executive_id,
                client_id=client_id,
                limit=5
            )
            logger.info(f"Retrieved {len(historical_recs)} historical recommendations for context")
        else:
            logger.debug("Memory system disabled, skipping historical retrieval")
        
        # Step 2: Enhance prompt with historical context
        enhanced_prompt = self._build_enhanced_prompt(
            base_prompt=analysis_prompt,
            historical_recs=historical_recs,
            current_date=current_date
        )
        
        # Step 3: Execute standard analysis
        analysis_result = self.execute_analysis(
            query_params=query_params,
            analysis_prompt=enhanced_prompt,
            current_date=None  # Already included in enhanced_prompt
        )
        
        # Step 4: Extract recommendations from AI response
        recommendations = self._extract_recommendations(analysis_result)
        logger.info(f"Extracted {len(recommendations)} recommendations from AI response")
        
        # Step 5: Generate embeddings for new recommendations
        if self._memory_enabled and recommendations:
            logger.debug(f"Generating embeddings for {len(recommendations)} recommendations")
            for rec in recommendations:
                rec_text = rec.get("recommendation", "")
                if rec_text:
                    embedding = self._embedding_client.generate_embedding(rec_text)
                    rec["embedding"] = embedding
            logger.info(f"Successfully generated embeddings for all recommendations")
        
        # Step 6: Filter recommendations based on similarity
        filtered_recs = recommendations
        if self._memory_enabled and recommendations and historical_recs:
            logger.debug(f"Filtering {len(recommendations)} recommendations against {len(historical_recs)} historical ones")
            filtered_recs = self._similarity_service.filter_recommendations(
                new_recommendations=recommendations,
                historical_recommendations=historical_recs
            )
            logger.info(f"Filtered recommendations: {len(recommendations)} -> {len(filtered_recs)}")
        
        # Step 7: Store new recommendations
        if self._memory_enabled and filtered_recs:
            logger.debug(f"Storing {len(filtered_recs)} filtered recommendations")
            for rec in filtered_recs:
                self._memory_store.store_recommendation(
                    executive_id=executive_id,
                    client_id=client_id,
                    recommendation_text=rec.get("recommendation", ""),
                    metadata={
                        "status": rec.get("status", "new"),
                        "previous_timestamp": rec.get("previous_timestamp")
                    }
                )
        
        # Step 8: Return results with filtered recommendations
        analysis_result["recommendations"] = filtered_recs
        analysis_result["memory_enabled"] = self._memory_enabled
        
        logger.info(f"Analysis with memory completed (executive: {executive_id}, client: {client_id}, recommendations: {len(filtered_recs)})")
        return analysis_result

    def _build_enhanced_prompt(
        self,
        base_prompt: Optional[str],
        historical_recs: List[Dict[str, Any]],
        current_date: Optional[str]
    ) -> str:
        """Build enhanced prompt with historical context.
        
        Args:
            base_prompt: Base analysis prompt
            historical_recs: List of historical recommendations
            current_date: Current date for context
            
        Returns:
            Enhanced prompt with historical context
        """
        prompt_parts = []
        
        # Add current date context
        if current_date:
            prompt_parts.append(f"Current date for analysis context: {current_date}.")
        
        # Add historical recommendations context
        if historical_recs:
            prompt_parts.append("\nPrevious recommendations for this client:")
            for i, rec in enumerate(historical_recs[:5], 1):  # Limit to 5
                rec_text = rec.get("recommendation", "")
                rec_time = rec.get("timestamp", "")
                prompt_parts.append(f"{i}. [{rec_time}] {rec_text}")
            prompt_parts.append("\nPlease generate diverse recommendations that avoid repeating these previous suggestions.")
        
        # Add base prompt
        if base_prompt:
            prompt_parts.append(f"\n{base_prompt}")
        else:
            prompt_parts.append("\nAnalyze the provided data and generate recommendations.")
        
        return " ".join(prompt_parts)

    def _extract_recommendations(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract recommendations from AI analysis result.
        
        Args:
            analysis_result: Result from execute_analysis()
            
        Returns:
            List of recommendation dictionaries
        """
        # Get the analysis field from the result
        analysis = analysis_result.get("analysis", {})
        
        # If analysis is a dict and has recommendations field
        if isinstance(analysis, dict) and "recommendations" in analysis:
            recs = analysis["recommendations"]
            if isinstance(recs, list):
                return recs
        
        # If analysis itself is a list of recommendations
        if isinstance(analysis, list):
            return analysis
        
        # No recommendations found
        return []
