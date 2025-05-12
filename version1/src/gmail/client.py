"""
Gmail Client Module
==================

This module provides functionality to interact with Gmail accounts using IMAP and SMTP.
It handles email operations such as:
- Authentication with Gmail servers
- Fetching emails for different time ranges
- Applying labels
- Creating draft responses

The client supports:
- Multiple Gmail accounts
- Email categorization
- Label management
- Draft response creation
- Date-based email filtering

Author: Your Name
Date: 2024
"""

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import os
import pickle
from typing import List, Dict, Optional
import sys
import imaplib
import smtplib
from datetime import datetime, timedelta
import openai
import re
from bs4 import BeautifulSoup
import html2text

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.config import (
    GMAIL_CREDENTIALS_FILE,
    GMAIL_TOKEN_FILE,
    GMAIL_SCOPES,
    EMAIL_LABELS
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GmailClient:
    """
    Client for interacting with Gmail accounts.
    
    This class provides methods to:
    - Authenticate with Gmail
    - Manage email labels
    - Fetch and process emails
    - Create draft responses
    
    Attributes:
        email (str): Gmail address
        password (str): Gmail password or app password
        imap_server (str): IMAP server address
        smtp_server (str): SMTP server address
        smtp_port (int): SMTP server port
    """
    
    def __init__(self, email: str, password: str):
        """
        Initialize Gmail client with email and password.
        
        Args:
            email (str): Gmail address
            password (str): Gmail password or app password
            
        Note:
            - Cleans password of any non-ASCII characters
            - Tests authentication before proceeding
            - Creates required labels if they don't exist
        """
        self.email = email
        # Clean the password of any non-ASCII characters
        self.password = ''.join(char for char in password if ord(char) < 128)
        self.imap_server = "imap.gmail.com"
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.ignore_tables = False
        
        # Test authentication before proceeding
        self._test_authentication()
        
        # Create labels if they don't exist
        self._create_labels()
    
    def _test_authentication(self) -> None:
        """
        Test Gmail authentication and provide helpful error messages.
        
        This method:
        1. Tests IMAP connection
        2. Tests SMTP connection
        3. Provides specific error messages for common issues
        
        Raises:
            ValueError: If authentication fails with specific error message
        """
        try:
            # Test IMAP connection
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email, self.password)
            mail.logout()
            
            # Test SMTP connection
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email, self.password)
            server.quit()
            
            logger.info(f"Successfully authenticated Gmail account: {self.email}")
        
        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            if "Application-specific password required" in error_msg:
                raise ValueError(
                    f"Account {self.email} requires an App Password. "
                    "Please generate one at: https://support.google.com/accounts/answer/185833"
                )
            elif "Invalid credentials" in error_msg:
                raise ValueError(
                    f"Invalid credentials for account {self.email}. "
                    "Please check the password in the Excel file."
                )
            else:
                raise ValueError(f"Gmail authentication failed for {self.email}: {error_msg}")
        
        except Exception as e:
            raise ValueError(f"Failed to authenticate Gmail account {self.email}: {str(e)}")
    
    def _create_labels(self) -> None:
        """
        Create Gmail labels and their corresponding folders.
        
        Creates the following labels and folders:
        - Application
        - Assessment
        - Interview
        - Offer
        - Rejection
        - Other
        
        Note:
            - Creates both labels and folders
            - Ignores errors if they already exist
            - Sets up proper folder structure
        """
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email, self.password)
            
            # Get existing labels
            _, labels_response = mail.list()
            existing_labels = []
            for label in labels_response:
                try:
                    # Decode the label from bytes to string
                    label_str = label.decode('utf-8')
                    # Extract the label name from the response
                    label_name = label_str.split('"')[-2]
                    existing_labels.append(label_name)
                except Exception as e:
                    logger.warning(f"Failed to decode label: {str(e)}")
            
            # Create only missing labels
            labels = ['Application_automation', 'Interview_automation', 'Assessment_automation', 'Offer_automation', 'Rejection_automation', 'Other_automation']
            for label in labels:
                if label not in existing_labels:
                    try:
                        # Create label using bytes
                        mail.create(label.encode('utf-8'))
                        logger.info(f"Created new label: {label}")
                    except imaplib.IMAP4.error as e:
                        logger.error(f"Error creating label {label}: {str(e)}")
                        raise
                else:
                    logger.info(f"Label already exists: {label}")
            
            mail.logout()
            logger.info(f"Successfully verified Gmail labels for {self.email}")
        
        except Exception as e:
            logger.error(f"Error managing Gmail labels: {str(e)}")
            raise
    
    def _clean_html_content(self, html_content: str) -> str:
        """
        Clean HTML content and convert to plain text.
        
        Args:
            html_content (str): Raw HTML content
            
        Returns:
            str: Clean plain text content
        """
        try:
            # Convert HTML to plain text
            text = self.html_converter.handle(html_content)
            
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Remove email signatures
            text = re.sub(r'--\s*\n.*', '', text, flags=re.DOTALL)
            
            # Remove quoted text
            text = re.sub(r'On.*wrote:.*', '', text, flags=re.DOTALL)
            
            return text.strip()
        except Exception as e:
            logger.warning(f"Failed to clean HTML content: {str(e)}")
            return html_content

    def _get_emails_by_date_range(self, start_date: datetime, end_date: datetime, batch_size: int = 10) -> List[Dict]:
        """
        Get emails within a date range, processing in batches.
        
        Args:
            start_date (datetime): Start date for email search
            end_date (datetime): End date for email search
            batch_size (int): Number of emails to process at once
            
        Returns:
            List[Dict]: List of processed email dictionaries
        """
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email, self.password)
            
            # Select inbox
            mail.select('inbox')
            
            # Format dates for IMAP search
            start_date_str = start_date.strftime("%d-%b-%Y")
            end_date_str = end_date.strftime("%d-%b-%Y")
            
            # Search for emails within date range
            _, messages = mail.search(None, f'(SINCE "{start_date_str}" BEFORE "{end_date_str}" ALL)')
            
            # Get total number of emails
            total_emails = len(messages[0].split())
            logger.info(f"Found {total_emails} emails to process")
            
            processed_emails = []
            for i in range(0, total_emails, batch_size):
                batch = messages[0].split()[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} of {(total_emails + batch_size - 1)//batch_size}")
                
                batch_emails = []
                for num in batch:
                    _, msg = mail.fetch(num, '(RFC822)')
                    email_body = msg[0][1]
                    email_message = email.message_from_bytes(email_body)
                    
                    # Get email details
                    email_id = num.decode()
                    subject = email_message['subject'] or '(No Subject)'
                    sender = email_message['from']
                    date = email_message['date']
                    
                    # Get email body
                    body = ""
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            
                            # Skip attachments
                            if "attachment" in content_disposition:
                                continue
                                
                            # Get text content
                            if content_type == "text/plain":
                                try:
                                    payload = part.get_payload(decode=True)
                                    # Try different encodings in sequence
                                    for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                                        try:
                                            body = payload.decode(encoding)
                                            break
                                        except UnicodeDecodeError:
                                            continue
                                    if not body:  # If all encodings failed
                                        body = payload.decode('utf-8', errors='replace')
                                except Exception as e:
                                    logger.warning(f"Failed to decode text/plain part: {str(e)}")
                                    body = "(Failed to decode content)"
                            elif content_type == "text/html":
                                try:
                                    payload = part.get_payload(decode=True)
                                    # Try different encodings in sequence
                                    for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                                        try:
                                            html_content = payload.decode(encoding)
                                            body = self._clean_html_content(html_content)
                                            break
                                        except UnicodeDecodeError:
                                            continue
                                    if not body:  # If all encodings failed
                                        html_content = payload.decode('utf-8', errors='replace')
                                        body = self._clean_html_content(html_content)
                                except Exception as e:
                                    logger.warning(f"Failed to decode text/html part: {str(e)}")
                                    body = "(Failed to decode content)"
                    else:
                        try:
                            payload = email_message.get_payload(decode=True)
                            if email_message.get_content_type() == "text/html":
                                html_content = payload.decode('utf-8', errors='replace')
                                body = self._clean_html_content(html_content)
                            else:
                                body = payload.decode('utf-8', errors='replace')
                        except Exception as e:
                            logger.warning(f"Failed to decode email body: {str(e)}")
                    
                    # Clean up the body
                    body = body.strip()
                    if not body:
                        body = "(No content)"
                    
                    email_data = {
                        'id': email_id,
                        'subject': subject,
                        'sender': sender,
                        'date': date,
                        'body': body
                    }
                    batch_emails.append(email_data)
                
                # Process the batch
                processed_emails.extend(batch_emails)
                logger.info(f"Processed {len(batch_emails)} emails in current batch")
            
            mail.logout()
            logger.info(f"Successfully processed all {len(processed_emails)} emails from {start_date_str} to {end_date_str} for {self.email}")
            return processed_emails
        
        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            raise

    def get_emails(self, time_range: str = 'today', batch_size: int = 10) -> List[Dict]:
        """
        Get emails based on specified time range, processing in batches.
        
        Args:
            time_range (str): Time range to fetch emails for:
                - 'today': Today's emails
                - 'yesterday': Yesterday's emails
                - 'last_week': Last 7 days
                - 'last_month': Last 30 days
            batch_size (int): Number of emails to process at once
                
        Returns:
            List[Dict]: List of processed email data
        """
        try:
            # Calculate date range
            now = datetime.utcnow()
            if time_range == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = now
            elif time_range == 'yesterday':
                start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_range == 'last_week':
                start_date = (now - timedelta(days=7))
                end_date = now
            elif time_range == 'last_month':
                start_date = (now - timedelta(days=30))
                end_date = now
            else:
                raise ValueError(f"Invalid time range: {time_range}")

            # Use the existing _get_emails_by_date_range method with batch processing
            return self._get_emails_by_date_range(start_date, end_date, batch_size)
            
        except Exception as e:
            logger.error(f"Failed to fetch emails: {str(e)}")
            raise

    def get_today_emails(self) -> List[Dict]:
        """
        Get today's emails (for backward compatibility).
        
        Returns:
            List[Dict]: List of today's emails
        """
        return self.get_emails('today')

    def get_yesterday_emails(self) -> List[Dict]:
        """
        Get all emails received yesterday.
        
        Returns:
            List[Dict]: List of email dictionaries containing id, subject, sender, date, and body
        """
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        return self._get_emails_by_date_range(yesterday, today)

    def get_last_week_emails(self) -> List[Dict]:
        """
        Get all emails received in the last 7 days.
        
        Returns:
            List[Dict]: List of email dictionaries containing id, subject, sender, date, and body
        """
        today = datetime.now()
        last_week = today - timedelta(days=7)
        return self._get_emails_by_date_range(last_week, today)
    
    def apply_label(self, message_id: str, label_name: str) -> None:
        """
        Apply a label to an email and move it to the corresponding folder.
        
        Args:
            message_id (str): Gmail message ID
            label_name (str): Label to apply (Application/Interview/Offer/Rejection/Other)
            
        Note:
            - Connects to Gmail
            - Applies label to email
            - Moves email to the labeled folder
            - Handles connection cleanup
        """
        try:
            # Connect to Gmail
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email, self.password)
            mail.select('INBOX')
            
            # Apply label to email
            mail.store(message_id, '+X-GM-LABELS', label_name)
            
            # Copy email to labeled folder
            mail.copy(message_id, label_name)
            
            # Delete from inbox (optional - comment out if you want to keep in inbox)
            # mail.store(message_id, '+FLAGS', '\\Deleted')
            # mail.expunge()
            
            logger.info(f"Successfully applied label {label_name} and moved email {message_id} to {label_name} folder")
        except Exception as e:
            logger.error(f"Failed to apply label: {str(e)}")
            raise
        finally:
            try:
                mail.close()
                mail.logout()
            except:
                pass

    def _get_label_id(self, label_name: str) -> Optional[str]:
        """
        Get the ID of a Gmail label.
        
        Args:
            label_name (str): Name of the label
            
        Returns:
            Optional[str]: Label ID if found, None otherwise
        """
        try:
            # Connect to Gmail
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email, self.password)
            
            # List all labels
            response, data = mail.list()
            
            # Find the label
            for item in data:
                if label_name.encode() in item:
                    return item.split(b'"')[-2].decode()
            
            return None
        except Exception as e:
            logger.error(f"Failed to get label ID: {str(e)}")
            return None
        finally:
            try:
                mail.logout()
            except:
                pass
    
    def create_draft(self, to: str, subject: str, body: str) -> None:
        """
        Create a draft email without sending it.
        
        Args:
            to (str): Recipient email address
            subject (str): Email subject
            body (str): Email body content
            
        Note:
            - Creates a draft email in Gmail
            - Does not send the email
            - Uses IMAP to create the draft
        """
        try:
            # Create message
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            message['from'] = self.email
            
            # Add body
            message.attach(MIMEText(body, 'plain'))
            
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email, self.password)
            
            # Select the Drafts folder
            mail.select('[Gmail]/Drafts')
            
            # Append the message to Drafts
            mail.append('[Gmail]/Drafts', '', imaplib.Time2Internaldate(datetime.now()), str(message).encode())
            
            mail.logout()
            logger.info(f"Successfully created draft email to {to}")
        
        except Exception as e:
            logger.error(f"Error creating draft: {str(e)}")
            raise 