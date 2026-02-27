"""
Batch processing service for handling large-scale AI analysis.

This service provides a scalable and extensible way to process large datasets
by dividing them into smaller batches and processing them in parallel.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    batch_size: int = 5  # Number of items per batch
    max_parallel_batches: int = 20  # Maximum concurrent batches (respects rate limits)
    enable_parallel: bool = True  # Enable/disable parallel processing
    
    def __post_init__(self):
        """Validate configuration."""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.max_parallel_batches <= 0:
            raise ValueError("max_parallel_batches must be positive")


@dataclass
class BatchResult:
    """Result from processing a single batch."""
    batch_num: int
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class BatchProcessor:
    """
    Service for processing large datasets in batches.
    
    This class provides a flexible and extensible way to:
    - Divide large datasets into manageable batches
    - Process batches in parallel (respecting rate limits)
    - Consolidate results from multiple batches
    - Handle errors gracefully
    
    Design principles:
    - Single Responsibility: Only handles batch processing logic
    - Open/Closed: Easy to extend with new processing strategies
    - Dependency Inversion: Depends on abstractions (callbacks) not implementations
    """
    
    def __init__(self, config: Optional[BatchConfig] = None):
        """
        Initialize batch processor.
        
        Args:
            config: Batch processing configuration. If None, uses defaults.
        """
        self._config = config or BatchConfig()
        self._logger = logger
    
    def divide_into_batches(self, data: List[Any]) -> List[List[Any]]:
        """
        Divide data into batches of configured size.
        
        Args:
            data: List of items to divide
            
        Returns:
            List of batches, where each batch is a list of items
        """
        batches = []
        batch_size = self._config.batch_size
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            batches.append(batch)
        
        self._logger.info(
            f"Divided {len(data)} items into {len(batches)} batches "
            f"(size: {batch_size})"
        )
        
        return batches
    
    async def process_batches_async(
        self,
        batches: List[List[Any]],
        process_fn: Callable[[List[Any], int], Any],
        *args,
        **kwargs
    ) -> List[BatchResult]:
        """
        Process batches asynchronously in parallel.
        
        Args:
            batches: List of batches to process
            process_fn: Function to process each batch. Should accept (batch_data, batch_num, *args, **kwargs)
            *args: Additional positional arguments to pass to process_fn
            **kwargs: Additional keyword arguments to pass to process_fn
            
        Returns:
            List of BatchResult objects
        """
        if not self._config.enable_parallel:
            return await self._process_batches_sequential(batches, process_fn, *args, **kwargs)
        
        self._logger.info(
            f"Processing {len(batches)} batches in parallel "
            f"(max concurrent: {self._config.max_parallel_batches})"
        )
        
        # Create semaphore to limit concurrent batches
        semaphore = asyncio.Semaphore(self._config.max_parallel_batches)
        
        async def process_with_semaphore(batch_data, batch_num):
            """Process batch with semaphore to limit concurrency."""
            async with semaphore:
                return await self._process_single_batch_async(
                    batch_data, batch_num, process_fn, *args, **kwargs
                )
        
        # Create tasks for all batches
        tasks = [
            process_with_semaphore(batch, i + 1)
            for i, batch in enumerate(batches)
        ]
        
        # Execute all tasks in parallel (respecting semaphore limit)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to BatchResult objects
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(BatchResult(
                    batch_num=i + 1,
                    success=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _process_batches_sequential(
        self,
        batches: List[List[Any]],
        process_fn: Callable[[List[Any], int], Any],
        *args,
        **kwargs
    ) -> List[BatchResult]:
        """Process batches sequentially (fallback for non-parallel mode)."""
        self._logger.info(f"Processing {len(batches)} batches sequentially")
        
        results = []
        for i, batch in enumerate(batches):
            result = await self._process_single_batch_async(
                batch, i + 1, process_fn, *args, **kwargs
            )
            results.append(result)
        
        return results
    
    async def _process_single_batch_async(
        self,
        batch_data: List[Any],
        batch_num: int,
        process_fn: Callable,
        *args,
        **kwargs
    ) -> BatchResult:
        """
        Process a single batch asynchronously.
        
        Args:
            batch_data: Data for this batch
            batch_num: Batch number (1-indexed)
            process_fn: Function to process the batch
            *args: Additional arguments for process_fn
            **kwargs: Additional keyword arguments for process_fn
            
        Returns:
            BatchResult object
        """
        import time
        
        self._logger.debug(f"[Batch {batch_num}] Starting processing...")
        start_time = time.time()
        
        try:
            # Run the synchronous process_fn in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                result = await loop.run_in_executor(
                    executor,
                    lambda: process_fn(batch_data, batch_num, *args, **kwargs)
                )
            
            duration = time.time() - start_time
            
            self._logger.info(
                f"[Batch {batch_num}] ✅ Completed in {duration:.2f}s"
            )
            
            return BatchResult(
                batch_num=batch_num,
                success=True,
                data=result,
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            
            self._logger.error(
                f"[Batch {batch_num}] ❌ Failed in {duration:.2f}s: {str(e)}"
            )
            
            return BatchResult(
                batch_num=batch_num,
                success=False,
                error=str(e),
                duration=duration
            )
    
    def consolidate_results(
        self,
        results: List[BatchResult],
        consolidate_fn: Optional[Callable[[List[Any]], Any]] = None
    ) -> Dict[str, Any]:
        """
        Consolidate results from multiple batches.
        
        Args:
            results: List of BatchResult objects
            consolidate_fn: Optional function to consolidate data. If None, uses default concatenation.
            
        Returns:
            Dictionary with consolidated results and metadata
        """
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        # Extract data from successful batches
        all_data = []
        for result in successful:
            if result.data is not None:
                all_data.append(result.data)
        
        # Consolidate data
        if consolidate_fn:
            consolidated_data = consolidate_fn(all_data)
        else:
            # Default: concatenate lists
            consolidated_data = []
            for data in all_data:
                if isinstance(data, list):
                    consolidated_data.extend(data)
                else:
                    consolidated_data.append(data)
        
        # Calculate statistics
        total_duration = sum(r.duration for r in results)
        avg_duration = total_duration / len(results) if results else 0
        
        return {
            "data": consolidated_data,
            "metadata": {
                "total_batches": len(results),
                "successful_batches": len(successful),
                "failed_batches": len(failed),
                "total_duration": total_duration,
                "avg_batch_duration": avg_duration,
                "failed_batch_numbers": [r.batch_num for r in failed]
            }
        }
