"""
Settings template file.
Copy this file to settings.py and add your actual API keys.
DO NOT commit settings.py to version control.
"""

# OpenAI Configuration
OPENAI_API_KEY = "your-api-key-here"  # Replace with your actual API key

# Excel Configuration
EXCEL_FILE_PATH = 'data/candidates.xlsx'

# Gmail Configuration
GMAIL_CREDENTIALS_FILE = 'credentials.json'
GMAIL_TOKEN_FILE = 'token.json'
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels'
] 