# import pandas as pd
# from datetime import datetime, timedelta
# import logging
# import imaplib
# import os
# from src.excel.client import ExcelClient
# from config.config import EXCEL_FILE_PATH

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[logging.StreamHandler()]
# )
# logger = logging.getLogger(__name__)

# LABELS = [
#     'Initial_Call_Automation',
#     'Interview_Automation',
#     'Assessment_Automation',
#     'Application_Automation',
#     'Rejection_Automation',
#     'Offer_Automation',
#     'Other_Automation'
# ]

# class LabelCounter:
#     def __init__(self, excel_file_path):
#         self.excel_client = ExcelClient(excel_file_path)
#         self.imap_timeout = 30
#         self.max_retries = 3

#     def _normalize_label(self, label):
#         """Format label for display"""
#         return label.replace('_Automation', '').replace('_', ' ').title()

#     def _connect_imap(self, email, password):
#         """IMAP connection with retries"""
#         for attempt in range(self.max_retries):
#             try:
#                 mail = imaplib.IMAP4_SSL('imap.gmail.com', timeout=self.imap_timeout)
#                 mail.login(email, password)
#                 return mail
#             except Exception as e:
#                 logger.warning(f"Attempt {attempt + 1} failed for {email}: {str(e)}")
#                 if attempt == self.max_retries - 1:
#                     raise
#         return None

#     def get_label_count(self, email, password, label, date=None):
#         """Count emails in a label for a specific date"""
#         mail = None
#         try:
#             mail = self._connect_imap(email, password)
#             if not mail:
#                 return 0

#             status, _ = mail.select(f'"{label}"', readonly=True)
#             if status != 'OK':
#                 return 0

#             search_query = f'ON "{date}"' if date else 'ALL'
#             status, data = mail.search(None, search_query)
#             return len(data[0].split()) if data[0] else 0

#         except Exception as e:
#             logger.error(f"Error counting {label} for {email}: {str(e)}")
#             return 0
#         finally:
#             if mail:
#                 try:
#                     mail.close()
#                     mail.logout()
#                 except:
#                     pass

#     def run(self):
#         candidates = self.excel_client.get_candidates()
#         if not candidates:
#             logger.warning("No candidates found")
#             return None

#         # Generate date headers for last 7 days
#         date_headers = []
#         date_formats = {}
#         today = datetime.now()
        
#         for i in range(7):
#             date = today - timedelta(days=i)
#             date_str = date.strftime("%Y-%m-%d")
#             date_headers.append(date_str)
#             date_formats[date_str] = date.strftime("%d-%b-%Y").upper()

#         output_data = []
        
#         for candidate in candidates:
#             name = candidate['Name']
#             email = candidate['candidateEmail__c']
#             password = candidate['candidatePassword__c']

#             for label in LABELS:
#                 row = {
#                     'Name': name,
#                     'Email': email,
#                     'Label': self._normalize_label(label),
#                     'Total': self.get_label_count(email, password, label)
#                 }
                
#                 # Add daily counts
#                 for date_header in date_headers:
#                     row[date_header] = self.get_label_count(
#                         email, password, label,
#                         date=date_formats[date_header]
#                     )
                
#                 row['Last Updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#                 output_data.append(row)

#         if output_data:
#             df = pd.DataFrame(output_data)
            
#             # Reorder columns
#             columns = ['Name', 'Email', 'Label'] + date_headers + ['Total', 'Last Updated']
#             df = df[columns]
            
#             # Save to Excel
#             output_dir = os.path.dirname(EXCEL_FILE_PATH)
#             os.makedirs(output_dir, exist_ok=True)
            
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             output_path = os.path.join(output_dir, f"email_counts_{timestamp}.xlsx")
            
#             df.to_excel(output_path, index=False)
#             logger.info(f"Saved results to: {output_path}")
#             return output_path
#         return None

# if __name__ == "__main__":
#     counter = LabelCounter(EXCEL_FILE_PATH)
#     result_file = counter.run()
#     if result_file:
#         print(f"Results saved to: {result_file}")

import pandas as pd
from datetime import datetime, timedelta
import logging
import imaplib
import os
from src.excel.client import ExcelClient
from config.config import EXCEL_FILE_PATH

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Create a log file with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f'email_counts_{timestamp}.log')

# Configure logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Only these 4 labels will be processed
# SELECTED_LABELS = {
#     'Application_Automation': 'Application',
#     'Assessment_Automation': 'Assessment',
#     'Initial_Call_Automation': 'Initial Call',
#     'Interview_Automation': 'Interview'
# }

SELECTED_LABELS = {
    'Application_Automation': 'Application',
    'Assessment_Automation': 'Assessment',
    'Initial_Call_Automation': 'Initial Call',
    'Interview_Automation': 'Interview',
    'Rejection_Automation': 'Rejection',
    'Offer_Automation': 'Offer',
    'Other_Automation': 'Other'
}

class LabelCounter:
    def __init__(self, excel_file_path):
        logger.info(f"Initializing LabelCounter with Excel file: {excel_file_path}")
        self.excel_client = ExcelClient(excel_file_path)
        self.imap_timeout = 30
        self.max_retries = 3
        logger.info("LabelCounter initialized successfully")

    def _connect_imap(self, email, password):
        """IMAP connection with retries"""
        logger.info(f"Attempting IMAP connection for {email}")
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Connection attempt {attempt + 1} of {self.max_retries}")
                mail = imaplib.IMAP4_SSL('imap.gmail.com', timeout=self.imap_timeout)
                mail.login(email, password)
                logger.info(f"Successfully connected to IMAP for {email}")
                return mail
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {email}: {str(e)}")
                if attempt == self.max_retries - 1:
                    logger.error(f"All connection attempts failed for {email}")
                    raise
        return None

    # def get_label_count(self, email, password, label, date=None):
    #     """Count emails in a label for a specific date"""
    #     mail = None
    #     try:
    #         mail = self._connect_imap(email, password)
    #         if not mail:
    #             return 0

    #         status, _ = mail.select(f'"{label}"', readonly=True)
    #         if status != 'OK':
    #             return 0

    #         search_query = f'ON "{date}"' if date else 'ALL'
    #         status, data = mail.search(None, search_query)
    #         return len(data[0].split()) if data[0] else 0

    #     except Exception as e:
    #         logger.error(f"Error counting {label} for {email}: {str(e)}")
    #         return 0
    #     finally:
    #         if mail:
    #             try:
    #                 mail.close()
    #                 mail.logout()
    #             except:
    #                 pass
    def get_label_count(self, email, password, label, date=None):
        """Count unique email threads in a label"""
        logger.info(f"Counting emails for {email} in label {label}" + (f" on {date}" if date else ""))
        mail = None
        try:
            mail = self._connect_imap(email, password)
            if not mail:
                logger.warning(f"No IMAP connection established for {email}")
                return 0

            logger.debug(f"Selecting label {label}")
            status, _ = mail.select(f'"{label}"', readonly=True)
            if status != 'OK':
                logger.warning(f"Failed to select label {label} for {email}")
                return 0

            # First get all message IDs
            search_query = f'ON "{date}"' if date else 'ALL'
            logger.debug(f"Searching with query: {search_query}")
            status, msg_ids = mail.search(None, search_query)
            if not msg_ids[0]:
                logger.info(f"No messages found for {email} in {label}" + (f" on {date}" if date else ""))
                return 0

            # Fetch thread IDs for each message
            thread_ids = set()
            total_messages = len(msg_ids[0].split())
            logger.debug(f"Processing {total_messages} messages for thread IDs")
            
            for msg_id in msg_ids[0].split():
                status, data = mail.fetch(msg_id, '(X-GM-THRID)')
                if status == 'OK' and data and data[0]:
                    # Extract thread ID from: b'1 (X-GM-THRID 1234567890123456789)'
                    thread_id = data[0].decode().split()[-1].strip(')')
                    thread_ids.add(thread_id)

            unique_threads = len(thread_ids)
            logger.info(f"Found {unique_threads} unique threads for {email} in {label}" + (f" on {date}" if date else ""))
            return unique_threads

        except Exception as e:
            logger.error(f"Error counting {label} for {email}: {str(e)}")
            return 0
        finally:
            if mail:
                try:
                    mail.close()
                    mail.logout()
                    logger.debug(f"Closed IMAP connection for {email}")
                except Exception as e:
                    logger.warning(f"Error closing IMAP connection for {email}: {str(e)}")

    def run(self):
        logger.info("Starting email count process")
        candidates = self.excel_client.get_candidates()
        if not candidates:
            logger.warning("No candidates found in Excel file")
            return None

        logger.info(f"Processing {len(candidates)} candidates")
        
        # Generate date headers for last 7 days
        date_headers = []
        date_formats = {}
        today = datetime.now()
        
        for i in range(7):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            date_headers.append(date_str)
            date_formats[date_str] = date.strftime("%d-%b-%Y").upper()
        
        logger.info(f"Generated date range: {date_headers[0]} to {date_headers[-1]}")

        output_data = []
        
        for candidate in candidates:
            name = candidate['Name']
            email = candidate['candidateEmail__c']
            password = candidate['candidatePassword__c']
            logger.info(f"Processing candidate: {name} ({email})")

            for imap_label, display_label in SELECTED_LABELS.items():
                logger.info(f"Counting {display_label} emails for {name}")
                row = {
                    'Name': name,
                    'Email': email,
                    'Label': display_label,
                    'Total': self.get_label_count(email, password, imap_label)
                }
                
                # Add daily counts
                for date_header in date_headers:
                    logger.debug(f"Counting {display_label} emails for {name} on {date_header}")
                    row[date_header] = self.get_label_count(
                        email, password, imap_label,
                        date=date_formats[date_header]
                    )
                
                row['Last Updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                output_data.append(row)
                logger.info(f"Completed counting {display_label} emails for {name}")

        if output_data:
            logger.info("Creating DataFrame from collected data")
            df = pd.DataFrame(output_data)
            
            # Reorder columns
            columns = ['Name', 'Email', 'Label'] + date_headers + ['Total', 'Last Updated']
            df = df[columns]
            
            # Save to Excel
            output_dir = os.path.dirname(EXCEL_FILE_PATH)
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"email_counts_{timestamp}.xlsx")
            
            logger.info(f"Saving results to: {output_path}")
            df.to_excel(output_path, index=False)
            logger.info(f"Successfully saved results to: {output_path}")
            return output_path
        
        logger.warning("No data collected to save")
        return None

if __name__ == "__main__":
    logger.info("Starting email count script")
    counter = LabelCounter(EXCEL_FILE_PATH)
    result_file = counter.run()
    if result_file:
        logger.info(f"Script completed successfully. Results saved to: {result_file}")
    else:
        logger.error("Script completed with no results")