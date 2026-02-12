"""
Tests for the main application module.

This module contains tests for application initialization, dependency injection,
and lifecycle management.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app, setup_dependencies
from app.config.settings import Settings


class TestApplicationCreation:
    """Tests for application factory function."""
    
    def test_create_app_with_valid_config_returns_fastapi_app(self):
        """Test that create_app returns a FastAPI application with valid config."""
        # Mock environment variables
        with patch.dict(os.environ, {
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DATABASE': 'test_db',
            'AWS_REGION': 'us-east-1',
            'AWS_BEDROCK_MODEL_ID': 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1',
            'API_HOST': '0.0.0.0',
            'API_PORT': '8000'
        }):
            app = create_app()
            
            assert isinstance(app, FastAPI)
            assert app.title == "AWS Bedrock API Service"
            assert app.version == "1.0.0"
    
    def test_create_app_without_config_raises_value_error(self):
        """Test that create_app raises ValueError when config is missing."""
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing required configuration"):
                create_app()
    
    def test_create_app_includes_api_routes(self):
        """Test that created app includes API routes."""
        with patch.dict(os.environ, {
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DATABASE': 'test_db',
            'AWS_REGION': 'us-east-1',
            'AWS_BEDROCK_MODEL_ID': 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1'
        }):
            app = create_app()
            
            # Check that routes are registered
            routes = [route.path for route in app.routes]
            assert '/api/analyze' in routes
            assert '/api/health' in routes
    
    def test_create_app_configures_cors_middleware(self):
        """Test that CORS middleware is configured."""
        with patch.dict(os.environ, {
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DATABASE': 'test_db',
            'AWS_REGION': 'us-east-1',
            'AWS_BEDROCK_MODEL_ID': 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1'
        }):
            app = create_app()
            
            # Check that middleware is present (FastAPI wraps it)
            assert len(app.user_middleware) > 0


class TestDependencySetup:
    """Tests for dependency injection setup."""
    
    def test_setup_dependencies_creates_clients(self):
        """Test that setup_dependencies creates MongoDB and AWS Bedrock clients."""
        app = FastAPI()
        
        # Create mock settings
        settings = Mock(spec=Settings)
        settings.mongodb_uri = 'mongodb://localhost:27017'
        settings.mongodb_database = 'test_db'
        settings.aws_region = 'us-east-1'
        settings.aws_bedrock_model_id = 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1'
        
        # Mock the client constructors to avoid actual connections
        with patch('app.main.MongoDBClient') as mock_mongo_client, \
             patch('app.main.AWSBedrockClient') as mock_ai_client, \
             patch('app.main.AnalysisService') as mock_service, \
             patch('app.main.set_analysis_service') as mock_set_service:
            
            setup_dependencies(app, settings)
            
            # Verify clients were created with correct parameters
            mock_mongo_client.assert_called_once_with(
                connection_string='mongodb://localhost:27017',
                database_name='test_db'
            )
            
            mock_ai_client.assert_called_once_with(
                region='us-east-1',
                model_id='arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1'
            )
            
            # Verify service was created with clients
            mock_service.assert_called_once()
            
            # Verify service was set for dependency injection
            mock_set_service.assert_called_once()
    
    def test_setup_dependencies_configures_analysis_service(self):
        """Test that setup_dependencies configures the analysis service."""
        app = FastAPI()
        
        settings = Mock(spec=Settings)
        settings.mongodb_uri = 'mongodb://localhost:27017'
        settings.mongodb_database = 'test_db'
        settings.aws_region = 'us-east-1'
        settings.aws_bedrock_model_id = 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1'
        
        with patch('app.main.MongoDBClient'), \
             patch('app.main.AWSBedrockClient'), \
             patch('app.main.AnalysisService') as mock_service, \
             patch('app.main.set_analysis_service') as mock_set_service:
            
            mock_service_instance = Mock()
            mock_service.return_value = mock_service_instance
            
            setup_dependencies(app, settings)
            
            # Verify the service instance was passed to set_analysis_service
            mock_set_service.assert_called_once_with(mock_service_instance)


class TestApplicationLifecycle:
    """Tests for application lifecycle management."""
    
    def test_lifespan_connects_clients_on_startup(self):
        """Test that lifespan context manager connects clients on startup."""
        with patch.dict(os.environ, {
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DATABASE': 'test_db',
            'AWS_REGION': 'us-east-1',
            'AWS_BEDROCK_MODEL_ID': 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1'
        }):
            # Mock the client connect methods
            with patch('app.main.MongoDBClient') as mock_mongo_client, \
                 patch('app.main.AWSBedrockClient') as mock_ai_client:
                
                mock_mongo_instance = Mock()
                mock_ai_instance = Mock()
                mock_mongo_client.return_value = mock_mongo_instance
                mock_ai_client.return_value = mock_ai_instance
                
                app = create_app()
                
                # Use TestClient to trigger lifespan events
                with TestClient(app) as client:
                    # Verify connect was called on both clients
                    mock_mongo_instance.connect.assert_called_once()
                    mock_ai_instance.connect.assert_called_once()
                
                # After context exit, verify disconnect was called
                mock_mongo_instance.disconnect.assert_called_once()
    
    def test_lifespan_disconnects_clients_on_shutdown(self):
        """Test that lifespan context manager disconnects clients on shutdown."""
        with patch.dict(os.environ, {
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DATABASE': 'test_db',
            'AWS_REGION': 'us-east-1',
            'AWS_BEDROCK_MODEL_ID': 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1'
        }):
            with patch('app.main.MongoDBClient') as mock_mongo_client, \
                 patch('app.main.AWSBedrockClient') as mock_ai_client:
                
                mock_mongo_instance = Mock()
                mock_ai_instance = Mock()
                mock_mongo_client.return_value = mock_mongo_instance
                mock_ai_client.return_value = mock_ai_instance
                
                app = create_app()
                
                with TestClient(app) as client:
                    pass  # Just enter and exit the context
                
                # Verify disconnect was called
                mock_mongo_instance.disconnect.assert_called_once()
    
    def test_lifespan_handles_connection_errors_gracefully(self):
        """Test that lifespan handles connection errors during startup."""
        with patch.dict(os.environ, {
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DATABASE': 'test_db',
            'AWS_REGION': 'us-east-1',
            'AWS_BEDROCK_MODEL_ID': 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1'
        }):
            with patch('app.main.MongoDBClient') as mock_mongo_client, \
                 patch('app.main.AWSBedrockClient') as mock_ai_client:
                
                mock_mongo_instance = Mock()
                mock_mongo_instance.connect.side_effect = ConnectionError("Connection failed")
                mock_mongo_client.return_value = mock_mongo_instance
                
                mock_ai_instance = Mock()
                mock_ai_client.return_value = mock_ai_instance
                
                app = create_app()
                
                # Attempting to start the app should raise the connection error
                with pytest.raises(ConnectionError, match="Connection failed"):
                    with TestClient(app) as client:
                        pass


class TestHealthEndpoint:
    """Tests for health check endpoint through main app."""
    
    def test_health_endpoint_accessible_through_main_app(self):
        """Test that health endpoint is accessible through the main app."""
        with patch.dict(os.environ, {
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DATABASE': 'test_db',
            'AWS_REGION': 'us-east-1',
            'AWS_BEDROCK_MODEL_ID': 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1'
        }):
            with patch('app.main.MongoDBClient') as mock_mongo_client, \
                 patch('app.main.AWSBedrockClient') as mock_ai_client:
                
                # Mock clients to avoid actual connections
                mock_mongo_instance = Mock()
                mock_ai_instance = Mock()
                mock_mongo_client.return_value = mock_mongo_instance
                mock_ai_client.return_value = mock_ai_instance
                
                app = create_app()
                
                with TestClient(app) as client:
                    response = client.get("/api/health")
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "healthy"
                    assert data["service"] == "AWS Bedrock API Service"


class TestConfigurationValidation:
    """Tests for configuration validation during app creation."""
    
    def test_missing_mongodb_uri_raises_error(self):
        """Test that missing MONGODB_URI raises descriptive error."""
        with patch.dict(os.environ, {
            'MONGODB_DATABASE': 'test_db',
            'AWS_REGION': 'us-east-1',
            'AWS_BEDROCK_MODEL_ID': 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1'
        }, clear=True):
            with pytest.raises(ValueError, match="MONGODB_URI"):
                create_app()
    
    def test_missing_aws_bedrock_model_id_raises_error(self):
        """Test that missing AWS_BEDROCK_MODEL_ID raises descriptive error."""
        with patch.dict(os.environ, {
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DATABASE': 'test_db',
            'AWS_REGION': 'us-east-1'
        }, clear=True):
            with pytest.raises(ValueError, match="AWS_BEDROCK_MODEL_ID"):
                create_app()
    
    def test_all_required_config_present_succeeds(self):
        """Test that app creation succeeds with all required config."""
        with patch.dict(os.environ, {
            'MONGODB_URI': 'mongodb://localhost:27017',
            'MONGODB_DATABASE': 'test_db',
            'AWS_REGION': 'us-east-1',
            'AWS_BEDROCK_MODEL_ID': 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1'
        }):
            app = create_app()
            assert isinstance(app, FastAPI)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
