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
            self.gmail_clients[candidate['candidateEmail__c']] = GmailClient(
                email=candidate['candidateEmail__c'],
                password=candidate['candidatePassword__c']
            )
        return self.gmail_clients[candidate['candidateEmail__c']]

    def process_candidate_emails(self, candidate, time_range='today'):
        gmail_client = self.get_gmail_client(candidate)
        emails = gmail_client.get_emails(time_range)
        logger.info(f"Found {len(emails)} emails for candidate {candidate['candidateEmail__c']}")
        for email in emails:
            # Check if email already has an automation label
            if gmail_client.has_automation_label(email['id']):
                logger.info(f"Email {email['id']} already categorized, skipping")
                continue
                
            body = email.get('body')
            if not body:
                continue
            category = self.openai_client.categorize_email(body)
            gmail_client.apply_label(email['id'], category)
            logger.info(f"Categorized and labeled email {email['id']} as {category}")

    def run(self, time_range='today'):
        candidates = self.excel_client.get_candidates()
        for candidate in candidates:
            self.process_candidate_emails(candidate, time_range)
        # After all categorization and labeling, call the label counting/report
        # logger.info("All email categorization and labeling complete. Generating label count report...")
        # counter = LabelCounter(EXCEL_FILE_PATH)
        # counter.run()
        # logger.info("Label count report generated.")

if __name__ == "__main__":
    assistant = EmailAssistant()
    assistant.run(time_range="last_week") 