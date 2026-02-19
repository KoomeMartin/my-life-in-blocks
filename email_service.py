"""
Email Service using Google Gmail API
Uses the same credentials as Google Calendar (credentials.json + token.json)
"""
import os
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger('EmailService')

class GmailEmailService:
    """Email service using Gmail API with OAuth2 authentication"""
    
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        """
        Initialize Gmail service using existing Google credentials
        
        Args:
            credentials_file: Path to credentials.json (same as Calendar)
            token_file: Path to token.json (same as Calendar)
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate using existing OAuth2 credentials"""
        try:
            creds = None
            
            # Scopes needed for Gmail
            SCOPES = [
                'https://www.googleapis.com/auth/calendar',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.readonly'
            ]
            
            # Load existing token if available
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(
                    self.token_file,
                    scopes=SCOPES
                )
                logger.info("✅ Loaded existing Gmail credentials from token.json")
            
            # Refresh token if expired
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                logger.info("✅ Refreshed expired Gmail credentials")
                
                # Save refreshed credentials
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
            
            # Build Gmail service
            if creds and creds.valid:
                self.service = build('gmail', 'v1', credentials=creds)
                logger.info("✅ Gmail API service initialized successfully")
            else:
                logger.error("❌ Gmail credentials not valid. Please re-authenticate.")
                logger.error("   Run: python reauth_gmail.py")
                raise ValueError("Gmail credentials not valid. Run 'python reauth_gmail.py' to re-authenticate.")
                
        except Exception as e:
            logger.error(f"❌ Failed to authenticate Gmail API: {e}")
            logger.error("   Run: python reauth_gmail.py")
            raise
    
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        from_email: Optional[str] = None
    ) -> bool:
        """
        Send an email using Gmail API
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body (for rich formatting)
            from_email: Optional sender email (defaults to authenticated user)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create message
            if html_body:
                message = MIMEMultipart('alternative')
                part1 = MIMEText(body, 'plain')
                part2 = MIMEText(html_body, 'html')
                message.attach(part1)
                message.attach(part2)
            else:
                message = MIMEText(body)
            
            message['To'] = to
            message['Subject'] = subject
            if from_email:
                message['From'] = from_email
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send message
            send_message = {'raw': raw_message}
            result = self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()
            
            logger.info(f"✅ Email sent successfully to {to} (Message ID: {result['id']})")
            return True
            
        except HttpError as error:
            logger.error(f"❌ Gmail API error: {error}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test Gmail API connection
        
        Returns:
            bool: True if connection is working, False otherwise
        """
        try:
            # Try to get user profile
            profile = self.service.users().getProfile(userId='me').execute()
            email = profile.get('emailAddress', 'Unknown')
            logger.info(f"✅ Gmail API connection successful. Authenticated as: {email}")
            return True
        except Exception as e:
            logger.error(f"❌ Gmail API connection test failed: {e}")
            return False


# Convenience function for quick email sending
def send_email(
    to: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None
) -> bool:
    """
    Quick function to send an email using Gmail API
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Plain text email body
        html_body: Optional HTML email body
    
    Returns:
        bool: True if email sent successfully
    """
    try:
        service = GmailEmailService()
        return service.send_email(to, subject, body, html_body)
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return False


if __name__ == "__main__":
    # Test the email service
    print("🧪 Testing Gmail Email Service...")
    print()
    
    try:
        # Initialize service
        print("1️⃣ Initializing Gmail service...")
        service = GmailEmailService()
        print("✅ Gmail service initialized")
        print()
        
        # Test connection
        print("2️⃣ Testing connection...")
        if service.test_connection():
            print("✅ Connection test passed")
        else:
            print("❌ Connection test failed")
            exit(1)
        print()
        
        # Send test email
        print("3️⃣ Sending test email...")
        test_email = input("Enter your email address to receive test email: ").strip()
        
        if test_email:
            success = service.send_email(
                to=test_email,
                subject="🧪 Test Email from My Life in Blocks",
                body="This is a test email from your REVIEWER agent!\n\nIf you're seeing this, the email integration is working correctly.",
                html_body="""
                <html>
                    <body style="font-family: Arial, sans-serif; padding: 20px;">
                        <h2 style="color: #667eea;">🧪 Test Email</h2>
                        <p>This is a test email from your <strong>REVIEWER agent</strong>!</p>
                        <p>If you're seeing this, the email integration is working correctly. ✅</p>
                        <hr style="border: 1px solid #eee; margin: 20px 0;">
                        <p style="color: #666; font-size: 12px;">
                            Sent from My Life in Blocks - Your AI-powered productivity assistant
                        </p>
                    </body>
                </html>
                """
            )
            
            if success:
                print("✅ Test email sent successfully!")
                print(f"📧 Check your inbox at {test_email}")
            else:
                print("❌ Failed to send test email")
        else:
            print("⚠️ No email address provided, skipping test email")
        
        print()
        print("=" * 60)
        print("✅ EMAIL SERVICE TEST COMPLETE")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
