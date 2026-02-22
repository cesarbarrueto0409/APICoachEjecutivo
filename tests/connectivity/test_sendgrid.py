"""Tests for SendGrid connectivity."""

import pytest
from app.clients.email_client import SendGridEmailClient


def test_sendgrid_configuration(test_config):
    """Test SendGrid client can be configured."""
    client = SendGridEmailClient(
        api_key=test_config["sendgrid_api_key"],
        from_email=test_config["sendgrid_from_email"],
        is_testing=True,
        test_email_override=test_config["sendgrid_test_email"]
    )
    
    assert client is not None


def test_sendgrid_test_email(test_config):
    """Test SendGrid can send test emails."""
    client = SendGridEmailClient(
        api_key=test_config["sendgrid_api_key"],
        from_email=test_config["sendgrid_from_email"],
        is_testing=True,
        test_email_override=test_config["sendgrid_test_email"]
    )
    
    result = client.send_email(
        to_email="original@example.com",
        subject="Test Email",
        html_content="<p>This is a test email</p>"
    )
    
    assert result["success"] is True
    assert result["recipient"] == test_config["sendgrid_test_email"]
    assert result["original_recipient"] == "original@example.com"
