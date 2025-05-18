"""
Email Assistant Main Module
==========================

This module provides the main functionality for processing candidate emails
and categorizing them using AI.
"""

import logging
from datetime import datetime
from src.excel.client import ExcelClient
from src.gmail.client import GmailClient
from src.openai.client import OpenAIClient
from config.config import EXCEL_FILE_PATH
# from count_labels import LabelCounter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class EmailAssistant:
    def __init__(self):
        self.excel_client = ExcelClient(EXCEL_FILE_PATH)
        self.openai_client = OpenAIClient()
        self.gmail_clients = {}
        logger.info("EmailAssistant initialized")

    def get_gmail_client(self, candidate):
        if candidate['candidateEmail__c'] not in self.gmail_clients:
            try:
                self.gmail_clients[candidate['candidateEmail__c']] = GmailClient(
                    email=candidate['candidateEmail__c'],
                    password=candidate['candidatePassword__c']
                )
                logger.info(f"Successfully created Gmail client for {candidate['candidateEmail__c']}")
            except Exception as e:
                logger.error(f"Failed to create Gmail client for {candidate['candidateEmail__c']}: {str(e)}")
                raise
        return self.gmail_clients[candidate['candidateEmail__c']]

    def process_candidate_emails(self, candidate, time_range='today'):
        try:
            gmail_client = self.get_gmail_client(candidate)
            emails = gmail_client.get_emails(time_range)
            
            for email in emails:
                try:
                    if not gmail_client.has_automation_label(email['id']):
                        category = self.openai_client.categorize_email(email['body'])
                        gmail_client.apply_label(email['id'], category)
                        logger.info(f"Successfully processed email {email['id']}")
                    else:
                        logger.info(f"Email {email['id']} already processed")
                except Exception as e:
                    logger.error(f"Error processing email {email['id']}: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error processing emails for {candidate['candidateEmail__c']}: {str(e)}")
            raise

    def run(self, time_range='today'):
        try:
            candidates = self.excel_client.get_candidates()
            logger.info(f"Found {len(candidates)} candidates")
            
            for candidate in candidates:
                try:
                    logger.info(f"Processing candidate: {candidate['candidateEmail__c']}")
                    self.process_candidate_emails(candidate, time_range)
                except Exception as e:
                    logger.error(f"Error processing candidate {candidate['candidateEmail__c']}: {str(e)}")
                    # Continue with next candidate instead of raising the exception
                    continue
            
            logger.info("Email processing completed successfully")
        
        except Exception as e:
            logger.error(f"Application error: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        assistant = EmailAssistant()
        assistant.run(time_range="last_week")
    except Exception as e:
        logger.error(f"Fatal error in main execution: {str(e)}")
        raise 