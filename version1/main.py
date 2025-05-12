"""
Email Assistant - Main Script
============================

This script is the main orchestrator for the Email Assistant system. It manages the processing
of emails for multiple candidates, coordinating between Excel data storage, Gmail operations,
and AI-powered email categorization and response generation.

The system:
1. Reads candidate information from Excel
2. Connects to each candidate's Gmail account
3. Processes today's emails
4. Categorizes emails using AI
5. Applies Gmail labels
6. Generates responses when needed
7. Tracks all activities in Excel
"""

import logging
from datetime import datetime
import sys
import os
from typing import Dict, List
from email.utils import parsedate_to_datetime

# Import custom modules
from src.excel.client import ExcelClient
from src.gmail.client import GmailClient
from src.openai.client import OpenAIClient
from config.config import EMAIL_LABELS, EXCEL_FILE_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_assistant.log'),  # Log to file
        logging.StreamHandler(sys.stdout)            # Log to console
    ]
)
logger = logging.getLogger(__name__)

class EmailAssistant:
    """
    Main class that orchestrates the email processing system.
    
    This class manages:
    - Excel data storage and retrieval
    - Gmail account connections
    - AI-powered email processing
    - Response generation
    """
    
    def __init__(self):
        """
        Initialize the Email Assistant with required clients.
        
        Creates instances of:
        - ExcelClient: For data storage and retrieval
        - OpenAIClient: For email categorization and response generation
        - Gmail clients: Dictionary to store Gmail clients for each candidate
        """
        self.excel_client = ExcelClient(EXCEL_FILE_PATH)
        self.openai_client = OpenAIClient()
        self.gmail_clients = {}  # Dictionary to store Gmail clients for each candidate

    def get_gmail_client(self, candidate: Dict) -> GmailClient:
        """
        Get or create a Gmail client for a candidate.
        
        Args:
            candidate (Dict): Candidate information including email and password
            
        Returns:
            GmailClient: Authenticated Gmail client for the candidate
            
        Note:
            - Creates a new Gmail client if one doesn't exist for the candidate
            - Reuses existing client if already created
            - Handles authentication with Gmail servers
        """
        if candidate['Email'] not in self.gmail_clients:
            self.gmail_clients[candidate['Email']] = GmailClient(
                email=candidate['Email'],
                password=candidate['Password']
            )
        return self.gmail_clients[candidate['Email']]

    def process_candidate_emails(self, candidate: Dict, time_range: str = 'today') -> None:
        """
        Process emails for a single candidate.
        
        Args:
            candidate (Dict): Candidate information
            time_range (str): Time range to process ('today', 'yesterday', 'last_week', 'last_month')
            
        Note:
            - Fetches emails from Gmail
            - Categorizes using AI
            - Updates Excel records
            - Creates response drafts
        """
        try:
            # Get Gmail client for candidate
            gmail_client = self.get_gmail_client(candidate)
            
            # Get emails based on time range
            emails = gmail_client.get_emails(time_range)
            logger.info(f"Found {len(emails)} emails for candidate {candidate['Email']}")
            
            # Process each email
            for email in emails:
                try:
                    # Check if email already processed
                    if self.excel_client.email_records_df[
                        self.excel_client.email_records_df['GmailMessageId'] == email['id']
                    ].empty:
                        # Categorize email using AI
                        category = self.openai_client.categorize_email(email['body'])
                        
                        # Apply Gmail label
                        gmail_client.apply_label(email['id'], category)
                        
                        # Generate response if needed
                        response = self.openai_client.generate_response(email['body'], category)
                        
                        # Parse email date using email.utils.parsedate_to_datetime
                        received_at = parsedate_to_datetime(email['date'])
                        
                        # Store email record
                        email_data = {
                            'id': email['id'],
                            'subject': email['subject'],
                            'sender': email['sender'],
                            'category': category,
                            'received_at': received_at,
                            'response': response
                        }
                        self.excel_client.add_email_record(candidate['Id'], email_data)
                        
                        # Create draft response if generated
                        if response:
                            gmail_client.create_draft(
                                to=email['sender'],
                                subject=f"Re: {email['subject']}",
                                body=response
                            )
                        
                        logger.info(f"Successfully processed email {email['id']} for candidate {candidate['Email']}")
                    else:
                        logger.info(f"Email {email['id']} already processed")
                except Exception as e:
                    logger.error(f"Error processing individual email {email.get('id', 'unknown')} for candidate {candidate['Email']}: {str(e)}")
                    continue  # Continue with next email even if one fails
        
        except Exception as e:
            logger.error(f"Error processing emails for candidate {candidate['Email']}: {str(e)}")

    def run(self, time_range: str = 'today') -> None:
        """
        Main execution method.
        
        Args:
            time_range (str): Time range to process ('today', 'yesterday', 'last_week', 'last_month')
            
        Note:
            - Processes candidates in sequence
            - Logs all activities
            - Continues processing even if one candidate fails
        """
        try:
            # Fetch candidates from Excel
            candidates = self.excel_client.get_candidates()
            logger.info(f"Fetched {len(candidates)} candidates from Excel")
            
            # Process emails for each candidate
            for candidate in candidates:
                logger.info(f"Processing emails for candidate: {candidate['Email']}")
                self.process_candidate_emails(candidate, time_range)
            
            logger.info("Email processing completed successfully")
        
        except Exception as e:
            logger.error(f"Error in main execution: {str(e)}")

if __name__ == "__main__":
    # Create and run the email assistant
    assistant = EmailAssistant()
    # assistant.run('today')
    assistant.run('yesterday')
    # assistant.run('last_week')
    # assistant.run('last_month') 