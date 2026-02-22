"""
Unit tests for the Settings configuration class.

These tests verify that the Settings class correctly loads configuration
from environment variables and validates required values.
"""

import os
import pytest
from app.config.settings import Settings


class TestSettings:
    """Test suite for Settings class."""
    
    def test_settings_initialization(self, monkeypatch):
        """Test that Settings initializes with environment variables."""
        # Set up test environment variables
        monkeypatch.setenv('MONGODB_URI', 'mongodb://testhost:27017')
        monkeypatch.setenv('MONGODB_DATABASE', 'test_db')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('AWS_BEDROCK_MODEL_ID', 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1')
        monkeypatch.setenv('API_HOST', '127.0.0.1')
        monkeypatch.setenv('API_PORT', '9000')
        
        # Create settings instance
        settings = Settings()
        
        # Verify all values are loaded correctly
        assert settings.mongodb_uri == 'mongodb://testhost:27017'
        assert settings.mongodb_database == 'test_db'
        assert settings.aws_region == 'us-east-1'
        assert settings.aws_bedrock_model_id == 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1'
        assert settings.api_host == '127.0.0.1'
        assert settings.api_port == 9000
    
    def test_settings_defaults(self, monkeypatch):
        """Test that Settings uses default values for optional config."""
        # Set only required environment variables
        monkeypatch.setenv('MONGODB_URI', 'mongodb://testhost:27017')
        monkeypatch.setenv('MONGODB_DATABASE', 'test_db')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('AWS_BEDROCK_MODEL_ID', 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1')
        
        # Create settings instance
        settings = Settings()
        
        # Verify default values are used
        assert settings.api_host == '0.0.0.0'
        assert settings.api_port == 8000
        assert settings.aws_region == 'us-east-1'
    
    def test_validate_success(self, monkeypatch):
        """Test that validate() passes with all required config present."""
        # Set up complete environment
        monkeypatch.setenv('MONGODB_URI', 'mongodb://testhost:27017')
        monkeypatch.setenv('MONGODB_DATABASE', 'test_db')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('AWS_BEDROCK_MODEL_ID', 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1')
        monkeypatch.setenv('SENDGRID_API_KEY', 'SG.test_key')
        monkeypatch.setenv('MEMORY_ENABLED', 'false')
        
        settings = Settings()
        
        # Should not raise any exception
        settings.validate()
    
    def test_validate_missing_mongodb_uri(self, monkeypatch):
        """Test that validate() raises error when MONGODB_URI is missing."""
        monkeypatch.setenv('MONGODB_URI', '')  # Empty string to override .env
        monkeypatch.setenv('MONGODB_DATABASE', 'test_db')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('AWS_BEDROCK_MODEL_ID', 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1')
        monkeypatch.setenv('SENDGRID_API_KEY', 'SG.test_key')
        monkeypatch.setenv('MEMORY_ENABLED', 'false')
        
        settings = Settings()
        
        with pytest.raises(ValueError) as exc_info:
            settings.validate()
        
        assert 'MONGODB_URI' in str(exc_info.value)
        assert 'Missing required configuration' in str(exc_info.value)
    
    def test_validate_missing_mongodb_database(self, monkeypatch):
        """Test that validate() raises error when MONGODB_DATABASE is missing."""
        monkeypatch.setenv('MONGODB_URI', 'mongodb://testhost:27017')
        monkeypatch.setenv('MONGODB_DATABASE', '')  # Empty string to override .env
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('AWS_BEDROCK_MODEL_ID', 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1')
        monkeypatch.setenv('SENDGRID_API_KEY', 'SG.test_key')
        monkeypatch.setenv('MEMORY_ENABLED', 'false')
        
        settings = Settings()
        
        with pytest.raises(ValueError) as exc_info:
            settings.validate()
        
        assert 'MONGODB_DATABASE' in str(exc_info.value)
        assert 'Missing required configuration' in str(exc_info.value)
    
    def test_validate_missing_aws_region(self, monkeypatch):
        """Test that validate() raises error when AWS_REGION is missing."""
        monkeypatch.setenv('MONGODB_URI', 'mongodb://testhost:27017')
        monkeypatch.setenv('MONGODB_DATABASE', 'test_db')
        monkeypatch.setenv('AWS_REGION', '')  # Empty string to override default
        monkeypatch.setenv('AWS_BEDROCK_MODEL_ID', 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1')
        monkeypatch.setenv('SENDGRID_API_KEY', 'SG.test_key')
        monkeypatch.setenv('MEMORY_ENABLED', 'false')
        
        settings = Settings()
        
        with pytest.raises(ValueError) as exc_info:
            settings.validate()
        
        assert 'AWS_REGION' in str(exc_info.value)
        assert 'Missing required configuration' in str(exc_info.value)
    
    def test_validate_missing_aws_bedrock_model_id(self, monkeypatch):
        """Test that validate() raises error when AWS_BEDROCK_MODEL_ID is missing."""
        monkeypatch.setenv('MONGODB_URI', 'mongodb://testhost:27017')
        monkeypatch.setenv('MONGODB_DATABASE', 'test_db')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('AWS_BEDROCK_MODEL_ID', '')  # Empty string to override default
        monkeypatch.setenv('SENDGRID_API_KEY', 'SG.test_key')
        monkeypatch.setenv('MEMORY_ENABLED', 'false')
        
        settings = Settings()
        
        with pytest.raises(ValueError) as exc_info:
            settings.validate()
        
        assert 'AWS_BEDROCK_MODEL_ID' in str(exc_info.value)
        assert 'Missing required configuration' in str(exc_info.value)
    
    def test_validate_multiple_missing(self, monkeypatch):
        """Test that validate() reports all missing required config values."""
        # Set all to empty strings to override .env
        monkeypatch.setenv('MONGODB_URI', '')
        monkeypatch.setenv('MONGODB_DATABASE', '')
        monkeypatch.setenv('AWS_REGION', '')
        monkeypatch.setenv('AWS_BEDROCK_MODEL_ID', '')
        monkeypatch.setenv('SENDGRID_API_KEY', '')
        monkeypatch.setenv('MEMORY_ENABLED', 'false')
        
        settings = Settings()
        
        with pytest.raises(ValueError) as exc_info:
            settings.validate()
        
        error_message = str(exc_info.value)
        assert 'MONGODB_URI' in error_message
        assert 'MONGODB_DATABASE' in error_message
        assert 'AWS_REGION' in error_message
        assert 'AWS_BEDROCK_MODEL_ID' in error_message
        assert 'SENDGRID_API_KEY' in error_message
        assert 'Missing required configuration' in error_message
    
    def test_repr_shows_configuration(self, monkeypatch):
        """Test that __repr__ shows configuration values."""
        monkeypatch.setenv('MONGODB_URI', 'mongodb://testhost:27017')
        monkeypatch.setenv('MONGODB_DATABASE', 'test_db')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('AWS_BEDROCK_MODEL_ID', 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1')
        
        settings = Settings()
        repr_str = repr(settings)
        
        # Verify configuration data is present
        assert 'mongodb://testhost:27017' in repr_str
        assert 'test_db' in repr_str
        assert 'us-east-1' in repr_str


class TestSendGridConfiguration:
    """Test suite for SendGrid configuration in Settings class."""
    
    def test_sendgrid_environment_variables_loaded(self, monkeypatch):
        """Test loading of SendGrid environment variables."""
        # Set up all environment variables including SendGrid
        monkeypatch.setenv('MONGODB_URI', 'mongodb://testhost:27017')
        monkeypatch.setenv('MONGODB_DATABASE', 'test_db')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('AWS_BEDROCK_MODEL_ID', 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1')
        monkeypatch.setenv('SENDGRID_API_KEY', 'SG.test_api_key_12345')
        monkeypatch.setenv('SENDGRID_ENDPOINT', 'https://test.sendgrid.com/v3/mail/send')
        monkeypatch.setenv('SENDGRID_FROM_EMAIL', 'noreply@test.local')
        monkeypatch.setenv('SENDGRID_TEST_EMAIL', 'testuser@test.local')
        
        settings = Settings()
        
        # Verify SendGrid configuration is loaded correctly
        assert settings.sendgrid_api_key == 'SG.test_api_key_12345'
        assert settings.sendgrid_endpoint == 'https://test.sendgrid.com/v3/mail/send'
        assert settings.sendgrid_from_email == 'noreply@test.local'
        assert settings.sendgrid_test_email == 'testuser@test.local'
    
    def test_sendgrid_default_values(self, monkeypatch):
        """Test default values for optional SendGrid variables."""
        # Set only required environment variables (not SendGrid optional ones)
        monkeypatch.setenv('MONGODB_URI', 'mongodb://testhost:27017')
        monkeypatch.setenv('MONGODB_DATABASE', 'test_db')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('AWS_BEDROCK_MODEL_ID', 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1')
        monkeypatch.setenv('SENDGRID_API_KEY', 'SG.test_api_key')
        
        settings = Settings()
        
        # Verify default values are used for optional SendGrid config
        assert settings.sendgrid_endpoint == 'https://api.sendgrid.com/v3/mail/send'
        # from_email and test_email come from .env, so we just verify they're loaded
        assert isinstance(settings.sendgrid_from_email, str)
        assert isinstance(settings.sendgrid_test_email, str)
    
    def test_validate_missing_sendgrid_api_key(self, monkeypatch):
        """Test validation raises error for missing SENDGRID_API_KEY."""
        # Set all required config except SENDGRID_API_KEY
        monkeypatch.setenv('MONGODB_URI', 'mongodb://testhost:27017')
        monkeypatch.setenv('MONGODB_DATABASE', 'test_db')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('AWS_BEDROCK_MODEL_ID', 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1')
        # Set SENDGRID_API_KEY to empty string to simulate missing
        monkeypatch.setenv('SENDGRID_API_KEY', '')
        
        settings = Settings()
        
        # Verify validation fails with appropriate error
        with pytest.raises(ValueError) as exc_info:
            settings.validate()
        
        assert 'SENDGRID_API_KEY' in str(exc_info.value)
        assert 'Missing required configuration' in str(exc_info.value)
    
    def test_validate_success_with_sendgrid(self, monkeypatch):
        """Test validation passes with all required config including SendGrid."""
        # Set up complete environment including SendGrid
        monkeypatch.setenv('MONGODB_URI', 'mongodb://testhost:27017')
        monkeypatch.setenv('MONGODB_DATABASE', 'test_db')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('AWS_BEDROCK_MODEL_ID', 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1')
        monkeypatch.setenv('SENDGRID_API_KEY', 'SG.test_api_key')
        monkeypatch.setenv('MEMORY_ENABLED', 'false')
        
        settings = Settings()
        
        # Should not raise any exception
        settings.validate()
    
    def test_sendgrid_api_key_empty_string_fails_validation(self, monkeypatch):
        """Test that empty string for SENDGRID_API_KEY fails validation."""
        # Set all required config with empty SENDGRID_API_KEY
        monkeypatch.setenv('MONGODB_URI', 'mongodb://testhost:27017')
        monkeypatch.setenv('MONGODB_DATABASE', 'test_db')
        monkeypatch.setenv('AWS_REGION', 'us-east-1')
        monkeypatch.setenv('AWS_BEDROCK_MODEL_ID', 'arn:aws:bedrock:us-east-1::inference-profile/amazon-nova-lite-v1')
        monkeypatch.setenv('SENDGRID_API_KEY', '')
        
        settings = Settings()
        
        # Verify validation fails for empty API key
        with pytest.raises(ValueError) as exc_info:
            settings.validate()
        
        assert 'SENDGRID_API_KEY' in str(exc_info.value)
        assert 'Missing required configuration' in str(exc_info.value)
