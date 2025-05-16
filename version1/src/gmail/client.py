"""
Gmail Client Module
==================

This module provides functionality to interact with Gmail accounts using IMAP.
It handles email operations such as:
- Authentication with Gmail servers
- Fetching emails for different time ranges
- Applying labels
- Email categorization

The client supports:
- Multiple Gmail accounts
- Email categorization
- Label management
- Date-based email filtering

Author: Your Name
Date: 2024
"""

import email
import logging
import os
import sys
import imaplib
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
import html2text
import time
from typing import List, Dict

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.config import EMAIL_LABELS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GmailClient:
    """
    Client for interacting with Gmail accounts.
    
    This class provides methods to:
    - Authenticate with Gmail
    - Manage email labels
    - Fetch and process emails
    
    Attributes:
        email (str): Gmail address
        password (str): Gmail password or app password
        imap_server (str): IMAP server address
    """
    
    def __init__(self, email: str, password: str):
        """
        Initialize Gmail client with email and password.
        
        Args:
            email (str): Gmail address
            password (str): Gmail password or app password
            
        Note:
            - Cleans and validates password format
            - Tests authentication before proceeding
            - Creates required labels if they don't exist
        """
        self.email = email.strip()
        
        # Clean and validate password
        if not password:
            raise ValueError("Password cannot be empty")
            
        # Remove ALL whitespace and ensure it's a string
        self.password = ''.join(str(password).split())
        
        # Validate password format
        if len(self.password) != 16:
            raise ValueError(
                f"Invalid App Password length: {len(self.password)} characters. "
                "App Password must be exactly 16 characters. "
                "Please generate a new App Password at: https://myaccount.google.com/apppasswords"
            )
            
        if not all(c.isalnum() for c in self.password):
            raise ValueError(
                "App Password contains invalid characters. "
                "App Password should only contain letters and numbers. "
                "Please generate a new App Password at: https://myaccount.google.com/apppasswords"
            )
        
        self.imap_server = "imap.gmail.com"
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
        2. Provides specific error messages for common issues
        
        Raises:
            ValueError: If authentication fails with specific error message
        """
        try:
            # Test IMAP connection
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email, self.password)
            mail.logout()
            
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
        Create Gmail labels if they don't exist.
        
        Creates the following labels from config:
        - Initial Call Automation
        - Interview Automation
        - Application Automation
        - Assessment Automation
        - Offer Automation
        - Rejection Automation
        - Other Automation
        
        Note:
            - Uses Gmail's IMAP extensions
            - Properly formats label names
            - Verifies label creation
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
            
            # Create only missing labels from config
            labels = list(EMAIL_LABELS.values())
            for label in labels:
                if label not in existing_labels:
                    try:
                        # Create label using Gmail's IMAP extensions
                        result = mail.create(f'"{label}"')
                        if result[0] != 'OK':
                            # Check if the error is because the label already exists
                            if b'[ALREADYEXISTS]' in result[1]:
                                logger.info(f"Label {label} already exists, continuing...")
                                continue
                            else:
                                raise Exception(f"Failed to create label: {result[1]}")
                        logger.info(f"Created new label: {label}")
                    except Exception as e:
                        # If the error is about the label already existing, just log and continue
                        if 'ALREADYEXISTS' in str(e):
                            logger.info(f"Label {label} already exists, continuing...")
                            continue
                        else:
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

    def get_emails(self, time_range: str = 'today') -> List[Dict]:
        """
        Get emails based on specified time range.
        
        Args:
            time_range (str): Time range to fetch emails for:
                - 'today': Today's emails
                - 'yesterday': Yesterday's emails
                - 'last_week': Last 7 days
                - 'last_month': Last 30 days
                
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

            # Use the existing _get_emails_by_date_range method
            return self._get_emails_by_date_range(start_date, end_date)
            
        except Exception as e:
            logger.error(f"Failed to fetch emails: {str(e)}")
            raise

    def _get_emails_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        mail = None
        try:
            # Connect to IMAP server with timeout
            mail = imaplib.IMAP4_SSL(self.imap_server, timeout=30)
            mail.login(self.email, self.password)
            
            # Select inbox and verify connection
            status, data = mail.select('inbox')
            if status != 'OK':
                raise Exception(f"Failed to select inbox: {status}")
            
            # Format dates for IMAP search
            start_date_str = start_date.strftime("%d-%b-%Y")
            end_date_str = end_date.strftime("%d-%b-%Y")
            
            # Search for emails within date range
            status, messages = mail.search(None, f'(SINCE "{start_date_str}" BEFORE "{end_date_str}" ALL)')
            if status != 'OK':
                raise Exception(f"Failed to search emails: {status}")
            
            # Get total number of emails
            email_ids = messages[0].split()
            total_emails = len(email_ids)
            logger.info(f"Found {total_emails} emails to process")
            
            processed_emails = []
            for num in email_ids:
                try:
                    # Add a small delay between fetches to avoid rate limiting
                    time.sleep(0.5)  # 500ms delay
                    
                    # Fetch individual email with more detailed error handling
                    logger.debug(f"Attempting to fetch email {num.decode()}")
                    
                    # First, check if the email exists and is accessible
                    status, data = mail.fetch(num, '(FLAGS)')
                    if status != 'OK':
                        logger.error(f"Failed to check email {num.decode()}: Status {status}")
                        continue
                    
                    # Now fetch the full email with retry logic
                    max_retries = 3
                    retry_count = 0
                    email_body = None
                    
                    while retry_count < max_retries:
                        try:
                            # Reconnect if needed
                            if retry_count > 0:
                                try:
                                    mail.close()
                                    mail.logout()
                                except:
                                    pass
                                mail = imaplib.IMAP4_SSL(self.imap_server, timeout=30)
                                mail.login(self.email, self.password)
                                mail.select('inbox')
                            
                            status, msg = mail.fetch(num, '(RFC822)')
                            
                            if status != 'OK' or not msg or not isinstance(msg, list) or len(msg) == 0:
                                logger.error(f"Invalid response for email {num.decode()}: status={status}, msg_type={type(msg)}")
                                break

                            if not isinstance(msg[0], tuple) or len(msg[0]) < 2:
                                logger.error(f"Invalid message format for email {num.decode()}")
                                break

                            email_body = msg[0][1]
                            if not email_body:
                                logger.error(f"Empty email body for email {num.decode()}")
                                break

                            # If we get here, we have a valid email body
                            break
                            
                        except Exception as e:
                            retry_count += 1
                            if retry_count == max_retries:
                                logger.error(f"Failed to fetch email {num.decode()} after {max_retries} attempts: {str(e)}")
                                break
                            logger.warning(f"Retry {retry_count} for email {num.decode()}: {str(e)}")
                            time.sleep(1)  # Wait 1 second before retry
                            continue

                    if not email_body:
                        logger.error(f"Could not fetch email body for {num.decode()} after all retries")
                        continue

                    try:
                        email_message = email.message_from_bytes(email_body)
                    except Exception as e:
                        logger.error(f"Failed to parse email message for {num.decode()}: {str(e)}")
                        continue

                    # Get email details with better error handling
                    email_id = num.decode()
                    subject = email_message.get('subject', '(No Subject)')
                    sender = email_message.get('from', '(No Sender)')
                    date = email_message.get('date', datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000"))

                    # Get email body with improved handling
                    body = ""
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition", ""))
                            
                            # Skip attachments
                            if "attachment" in content_disposition:
                                continue
                                
                            # Get text content
                            if content_type == "text/plain":
                                try:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        body = payload.decode('utf-8', errors='replace')
                                        break
                                except Exception as e:
                                    logger.warning(f"Failed to decode text/plain part: {str(e)}")
                                    continue

                            elif content_type == "text/html":
                                try:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        html_content = payload.decode('utf-8', errors='replace')
                                        body = self._clean_html_content(html_content)
                                        break
                                except Exception as e:
                                    logger.warning(f"Failed to decode text/html part: {str(e)}")
                                    continue
                    else:
                        try:
                            payload = email_message.get_payload(decode=True)
                            if payload:
                                body = payload.decode('utf-8', errors='replace')
                        except Exception as e:
                            logger.warning(f"Failed to decode single part email: {str(e)}")
                            body = "(Failed to decode content)"
                    
                    # Clean up the body
                    body = body.strip() if body else "(No content)"
                    
                    email_data = {
                        'id': email_id,
                        'subject': subject,
                        'sender': sender,
                        'date': date,
                        'body': body
                    }
                    processed_emails.append(email_data)
                    logger.info(f"Successfully processed email {email_id}")

                except Exception as e:
                    logger.error(f"Failed to process email {num.decode()}: {str(e)}")
                    continue
            
            logger.info(f"Successfully processed all {len(processed_emails)} emails")
            return processed_emails
        
        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            raise
        finally:
            if mail:
                try:
                    mail.close()
                    mail.logout()
                except:
                    pass
    
    def apply_label(self, message_id: str, category: str) -> None:
        """
        Apply a label to an email using Gmail's IMAP extensions.
        
        Args:
            message_id (str): Gmail message ID
            category (str): Category from config (e.g., 'INTERVIEW', 'APPLICATION')
            
        Note:
            - Uses Gmail's X-GM-LABELS extension
            - Gets label name from config
            - Properly formats label name
            - Handles label application in a single operation
        """
        try:
            # Get label name from config
            if category not in EMAIL_LABELS:
                # If the category is a label value, find its key
                category_key = None
                for key, value in EMAIL_LABELS.items():
                    if value == category:
                        category_key = key
                        break
                
                if category_key is None:
                    raise ValueError(f"Invalid category: {category}. Must be one of {list(EMAIL_LABELS.keys())} or {list(EMAIL_LABELS.values())}")
                
                category = category_key
            
            label_name = EMAIL_LABELS[category]
            
            # Connect to Gmail
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.email, self.password)
            mail.select('INBOX')
            
            # Format label name properly
            formatted_label = label_name.strip()
            
            # Apply label using Gmail's X-GM-LABELS extension
            result = mail.store(message_id, '+X-GM-LABELS', f'"{formatted_label}"')
            
            if result[0] != 'OK':
                raise Exception(f"Failed to apply label: {result[1]}")
            
            logger.info(f"Successfully applied label {formatted_label} to email {message_id}")
            
        except Exception as e:
            logger.error(f"Failed to apply label: {str(e)}")
            raise
        finally:
            try:
                mail.close()
                mail.logout()
            except:
                pass