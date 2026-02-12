"""Email client interface and SendGrid implementation."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


class IEmailClient(ABC):
    """Interface for email client implementations."""
    
    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        from_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            from_email: Optional sender email (overrides default)
            
        Returns:
            Dict with keys: success (bool), status_code (int), message (str)
            
        Raises:
            ConnectionError: If cannot connect to email service
            ValueError: If parameters are invalid
        """
        pass


class SendGridEmailClient(IEmailClient):
    """SendGrid implementation of IEmailClient."""
    
    def __init__(
        self,
        api_key: str,
        from_email: str,
        is_testing: bool = False,
        test_email_override: Optional[str] = None
    ):
        """
        Initialize SendGrid client.
        
        Args:
            api_key: SendGrid API key
            from_email: Default sender email
            is_testing: If True, redirect all emails to test_email_override
            test_email_override: Email address for testing mode
            
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        if not api_key:
            raise ValueError("api_key cannot be empty")
        if not from_email:
            raise ValueError("from_email cannot be empty")
        if is_testing and not test_email_override:
            raise ValueError("test_email_override required when is_testing=True")
            
        self._api_key = api_key
        self._from_email = from_email
        self._is_testing = is_testing
        self._test_email_override = test_email_override
        self._client = SendGridAPIClient(api_key)
        self._logger = logging.getLogger(__name__)
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        from_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send email via SendGrid.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            from_email: Optional sender email (overrides default)
            
        Returns:
            Dict with keys:
                - success: bool indicating if email was sent
                - status_code: HTTP status code from SendGrid
                - message: Success or error message
                - recipient: Actual recipient email
                - original_recipient: Original recipient (if in testing mode)
        """
        try:
            # Determine actual recipient
            actual_recipient = to_email
            original_recipient = None
            
            if self._is_testing:
                original_recipient = to_email
                actual_recipient = self._test_email_override
                subject = f"[TEST] {subject}"
                # Add original recipient info to body
                html_content = f"""
                <div style="background-color: #fff3cd; padding: 10px; margin-bottom: 20px; border: 1px solid #ffc107;">
                    <strong>MODO TEST:</strong> Este correo originalmente iba dirigido a: {original_recipient}
                </div>
                {html_content}
                """
            
            # Create message
            message = Mail(
                from_email=from_email or self._from_email,
                to_emails=actual_recipient,
                subject=subject,
                html_content=html_content
            )
            
            # Send via SendGrid
            response = self._client.send(message)
            
            self._logger.info(
                f"Email sent successfully to {actual_recipient} "
                f"(original: {original_recipient or 'N/A'}), "
                f"status: {response.status_code}"
            )
            
            return {
                "success": True,
                "status_code": response.status_code,
                "message": "Email sent successfully",
                "recipient": actual_recipient,
                "original_recipient": original_recipient
            }
            
        except Exception as e:
            self._logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return {
                "success": False,
                "status_code": None,
                "message": str(e),
                "recipient": to_email,
                "original_recipient": None
            }
