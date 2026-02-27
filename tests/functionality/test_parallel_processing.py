"""
Tests for parallel batch processing functionality.

This module tests the parallel processing system that divides executives
into batches and processes them concurrently for improved performance.
"""

import pytest
import os
import time
from typing import List, Dict, Any
from app.services.batch_processor import BatchProcessor, BatchConfig
from app.clients.aws_bedrock_client import AWSBedrockClient


class TestBatchConfiguration:
    """Tests for BatchConfig class."""
    
    def test_batch_config_from_env(self, monkeypatch):
        """Test that BatchConfig loads correctly from environment variables."""
        monkeypatch.setenv("BATCH_SIZE", "10")
        monkeypatch.setenv("MAX_PARALLEL_BATCHES", "5")
        monkeypatch.setenv("ENABLE_PARALLEL_BATCHES", "true")
        
        config = BatchConfig()
        
        assert config.batch_size == 10
        assert config.max_parallel_batches == 5
        assert config.enable_parallel is True
    
    def test_batch_config_defaults(self, monkeypatch):
        """Test that BatchConfig uses defaults when env vars are not set."""
        # Clear env vars
        monkeypatch.delenv("BATCH_SIZE", raising=False)
        monkeypatch.delenv("MAX_PARALLEL_BATCHES", raising=False)
        monkeypatch.delenv("ENABLE_PARALLEL_BATCHES", raising=False)
        
        config = BatchConfig()
        
        assert config.batch_size == 5
        assert config.max_parallel_batches == 20
        assert config.enable_parallel is True
    
    def test_batch_config_disable_parallel(self, monkeypatch):
        """Test disabling parallel processing."""
        monkeypatch.setenv("ENABLE_PARALLEL_BATCHES", "false")
        
        config = BatchConfig()
        
        assert config.enable_parallel is False


class TestBatchDivision:
    """Tests for dividing executives into batches."""
    
    def test_divide_76_executives_into_batches(self):
        """Test dividing 76 executives into batches of 5."""
        # Create mock data for 76 executives
        executives = [{"id": i, "name": f"Exec {i}"} for i in range(76)]
        
        config = BatchConfig(batch_size=5)
        processor = BatchProcessor(config, None)  # No AI client needed for this test
        
        batches = processor._divide_into_batches(executives)
        
        # Should create 16 batches (15 with 5 executives, 1 with 1 executive)
        assert len(batches) == 16
        assert len(batches[0]) == 5
        assert len(batches[-1]) == 1
        
        # Verify no executives are lost
        total_executives = sum(len(batch) for batch in batches)
        assert total_executives == 76
    
    def test_divide_exact_multiple(self):
        """Test dividing when total is exact multiple of batch size."""
        executives = [{"id": i} for i in range(20)]
        
        config = BatchConfig(batch_size=5)
        processor = BatchProcessor(config, None)
        
        batches = processor._divide_into_batches(executives)
        
        assert len(batches) == 4
        assert all(len(batch) == 5 for batch in batches)
    
    def test_divide_less_than_batch_size(self):
        """Test dividing when total is less than batch size."""
        executives = [{"id": i} for i in range(3)]
        
        config = BatchConfig(batch_size=5)
        processor = BatchProcessor(config, None)
        
        batches = processor._divide_into_batches(executives)
        
        assert len(batches) == 1
        assert len(batches[0]) == 3


class TestParallelProcessing:
    """Tests for parallel batch processing."""
    
    @pytest.mark.integration
    def test_parallel_processing_integrity(self, test_config):
        """Test that parallel processing maintains data integrity."""
        # This test requires actual AWS Bedrock connection
        if not test_config.get("aws_bearer_token"):
            pytest.skip("AWS credentials not configured")
        
        # Create AI client
        ai_client = AWSBedrockClient(
            region=test_config["aws_region"],
            model_id=test_config["aws_model_id"],
            bearer_token=test_config["aws_bearer_token"]
        )
        ai_client.connect()
        
        # Create processor
        config = BatchConfig(batch_size=5, max_parallel_batches=4)
        processor = BatchProcessor(config, ai_client)
        
        # Create mock data for 20 executives
        executives = [
            {
                "id_ejecutivo": i,
                "nombre_ejecutivo": f"Ejecutivo {i}",
                "cartera_detallada": [
                    {"rut_key": f"{j}", "nombre": f"Cliente {j}"}
                    for j in range(5)
                ]
            }
            for i in range(20)
        ]
        
        # Process in parallel
        result = processor.process_batches(
            executives=executives,
            prompt="Analiza y genera 3 recomendaciones por ejecutivo.",
            current_date="2026-02-25"
        )
        
        # Verify all executives are in result
        assert len(result["ejecutivos"]) == 20
        
        # Verify no duplicates
        exec_ids = [e["id_ejecutivo"] for e in result["ejecutivos"]]
        assert len(exec_ids) == len(set(exec_ids))
        
        # Verify each has recommendations
        for ejecutivo in result["ejecutivos"]:
            assert "sugerencias_clientes" in ejecutivo
            assert len(ejecutivo["sugerencias_clientes"]) <= 3
        
        ai_client.disconnect()
    
    @pytest.mark.performance
    def test_parallel_speedup(self, test_config):
        """Test that parallel processing is faster than sequential."""
        if not test_config.get("aws_bearer_token"):
            pytest.skip("AWS credentials not configured")
        
        ai_client = AWSBedrockClient(
            region=test_config["aws_region"],
            model_id=test_config["aws_model_id"],
            bearer_token=test_config["aws_bearer_token"]
        )
        ai_client.connect()
        
        # Create small dataset for testing
        executives = [
            {
                "id_ejecutivo": i,
                "nombre_ejecutivo": f"Ejecutivo {i}",
                "cartera_detallada": [{"rut_key": f"{j}", "nombre": f"Cliente {j}"} for j in range(3)]
            }
            for i in range(12)
        ]
        
        prompt = "Analiza y genera 3 recomendaciones."
        
        # Test parallel processing
        config_parallel = BatchConfig(batch_size=3, max_parallel_batches=4, enable_parallel=True)
        processor_parallel = BatchProcessor(config_parallel, ai_client)
        
        start_parallel = time.time()
        result_parallel = processor_parallel.process_batches(executives, prompt, "2026-02-25")
        time_parallel = time.time() - start_parallel
        
        # Test sequential processing
        config_sequential = BatchConfig(batch_size=3, max_parallel_batches=1, enable_parallel=False)
        processor_sequential = BatchProcessor(config_sequential, ai_client)
        
        start_sequential = time.time()
        result_sequential = processor_sequential.process_batches(executives, prompt, "2026-02-25")
        time_sequential = time.time() - start_sequential
        
        # Verify speedup
        speedup = time_sequential / time_parallel
        print(f"\nSpeedup: {speedup:.2f}x (Sequential: {time_sequential:.2f}s, Parallel: {time_parallel:.2f}s)")
        
        # Parallel should be at least 2x faster
        assert speedup > 2.0, f"Expected speedup > 2x, got {speedup:.2f}x"
        
        # Verify results are equivalent
        assert len(result_parallel["ejecutivos"]) == len(result_sequential["ejecutivos"])
        
        ai_client.disconnect()


class TestErrorHandling:
    """Tests for error handling in parallel processing."""
    
    def test_partial_batch_failure(self):
        """Test that other batches continue when one fails."""
        # This would require mocking AI client to simulate failures
        # Implementation depends on specific error handling strategy
        pass
    
    def test_all_batches_fail(self):
        """Test behavior when all batches fail."""
        # Implementation depends on error handling strategy
        pass


class TestEmailTestingMode:
    """Tests for email testing mode with test_correo field."""
    
    @pytest.mark.integration
    def test_test_correo_field_preserved(self, test_config):
        """Test that test_correo field is preserved through analysis."""
        # This test requires MongoDB connection
        if not test_config.get("mongodb_uri"):
            pytest.skip("MongoDB not configured")
        
        # Make API call with is_testing=true
        import requests
        
        response = requests.post(
            f"{test_config['api_base_url']}/api/analyze",
            json={"current_date": "2026-02-25", "is_testing": True},
            timeout=300
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check email notifications
        email_notif = data.get("email_notifications", {})
        
        # Should have some skipped (executives without test_correo)
        assert email_notif.get("total_skipped", 0) > 0
        
        # If there are executives with test_correo, they should be sent
        if email_notif.get("total_sent", 0) > 0:
            # Verify sent notifications have test_correo
            sent_notifications = [
                n for n in email_notif.get("notifications", [])
                if n.get("status") == "success"
            ]
            
            for notif in sent_notifications:
                assert notif.get("test_correo") is not None
                assert notif.get("test_mode") is True
    
    def test_testing_mode_filters_correctly(self, test_config):
        """Test that testing mode only sends to executives with test_correo."""
        if not test_config.get("mongodb_uri"):
            pytest.skip("MongoDB not configured")
        
        import requests
        
        response = requests.post(
            f"{test_config['api_base_url']}/api/analyze",
            json={"current_date": "2026-02-25", "is_testing": True},
            timeout=300
        )
        
        assert response.status_code == 200
        data = response.json()
        
        email_notif = data.get("email_notifications", {})
        total_sent = email_notif.get("total_sent", 0)
        total_skipped = email_notif.get("total_skipped", 0)
        
        # In testing mode, most should be skipped
        assert total_skipped > total_sent
        
        # All sent emails should have test_mode=True
        for notif in email_notif.get("notifications", []):
            if notif.get("status") == "success":
                assert notif.get("test_mode") is True


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return {
        "mongodb_uri": os.getenv("MONGODB_URI"),
        "aws_region": os.getenv("AWS_REGION", "us-east-1"),
        "aws_model_id": os.getenv("AWS_BEDROCK_MODEL_ID"),
        "aws_bearer_token": os.getenv("AWS_BEARER_TOKEN_BEDROCK"),
        "api_base_url": os.getenv("API_BASE_URL", "http://localhost:8000")
    }
