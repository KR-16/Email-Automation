import logging
import imaplib
import pandas as pd
from datetime import datetime
import os
from email.utils import parsedate_tz, mktime_tz
import unicodedata
from src.excel.client import ExcelClient
from config.config import EXCEL_FILE_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Consistent label casing (match exactly what's in Gmail)
LABELS = [
    'Initial_Call_Automation',
    'Interview_Automation',
    'Assessment_Automation',
    'Application_Automation',
    'Rejection_Automation',
    'Offer_Automation',
    'Other_Automation'
]

class LabelCounter:
    def __init__(self, excel_file_path):
        self.excel_client = ExcelClient(excel_file_path)
        # IMAP timeout settings (seconds)
        self.imap_timeout = 30
        self.max_retries = 3

    def _normalize_label(self, label):
        """Normalize label name by removing non-ASCII chars and normalizing spaces"""
        # Convert to ASCII, ignoring non-ASCII chars, then normalize whitespace
        label = unicodedata.normalize('NFKD', label)
        label = label.encode('ascii', 'ignore').decode('ascii')
        return ' '.join(label.strip().split())

    def _connect_imap(self, email, password):
        """Establish IMAP connection with error handling"""
        for attempt in range(self.max_retries):
            try:
                mail = imaplib.IMAP4_SSL('imap.gmail.com', timeout=self.imap_timeout)
                mail.login(email, password)
                logger.info(f"Successfully connected to Gmail for {email}")
                return mail
            except Exception as e:
                logger.warning(f"IMAP connection attempt {attempt + 1} failed for {email}: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
        return None

    def get_label_count(self, email, password, label):
        mail = None
        try:
            mail = self._connect_imap(email, password)
            if not mail:
                logger.error(f"Failed to connect to Gmail for {email}")
                return 0

            normalized_label = self._normalize_label(label)
            quoted_label = f'"{normalized_label}"' if ' ' in normalized_label else normalized_label
            
            logger.info(f"Attempting to select label: {quoted_label} for {email}")
            status, _ = mail.select(quoted_label, readonly=True)
            
            if status != 'OK':
                logger.warning(f"Label {quoted_label} not found or inaccessible for {email}")
                return 0

            status, data = mail.search(None, 'ALL')
            if status != 'OK':
                logger.warning(f"Failed to search emails in label {quoted_label} for {email}")
                return 0

            email_count = len(data[0].split())
            logger.info(f"Found {email_count} emails in label {quoted_label} for {email}")
            return email_count

        except Exception as e:
            logger.error(f"IMAP error for {email} label {label}: {str(e)}")
            return 0
        finally:
            if mail:
                try:
                    mail.logout()
                except:
                    pass

    def run(self):
        candidates = self.excel_client.get_candidates()
        logger.info(f"Fetched {len(candidates)} candidates from Excel")
        
        # Create a list to store the data
        output_data = []
        
        for idx, candidate in enumerate(candidates, 1):
            name = candidate['Name']
            email = candidate['candidateEmail__c']
            password = candidate['candidatePassword__c']
            
            logger.info(f"Processing candidate {idx}/{len(candidates)}: {email}")
            
            # Create a row for this candidate
            row = {
                'Name': name,
                'Email': email,
                'Last Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Get counts for each label
            for label in LABELS:
                count = self.get_label_count(email, password, label)
                row[label] = count
                if count > 0:
                    logger.info(f"Added {count} emails for label {label} for {email}")
                else:
                    logger.info(f"No emails found for label {label} for {email}")
            
            output_data.append(row)

        if output_data:
            # Convert to DataFrame
            df = pd.DataFrame(output_data)
            
            # Ensure all label columns exist (in case some have no emails)
            for label in LABELS:
                if label not in df.columns:
                    df[label] = 0
            
            # Reorder columns to match desired format
            columns = ['Name', 'Email'] + LABELS + ['Last Updated']
            df = df[columns]
            
            output_dir = os.path.dirname(EXCEL_FILE_PATH)
            os.makedirs(output_dir, exist_ok=True)  # Ensure output directory exists
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"label_counts_{timestamp}.xlsx")
            
            try:
                df.to_excel(output_path, index=False)
                logger.info(f"Successfully saved results to: {output_path}")
                return output_path
            except Exception as e:
                logger.error(f"Failed to save results: {str(e)}")
                raise
        else:
            logger.warning("No data collected - output file not created")
            return None

if __name__ == "__main__":
    counter = LabelCounter(EXCEL_FILE_PATH)
    result_file = counter.run()
    if result_file:
        print(f"Results saved to: {result_file}")
    else:
        print("No results were generated")