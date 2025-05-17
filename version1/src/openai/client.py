import openai
import logging
from typing import Dict, Optional
import sys
import os
from datetime import datetime
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import re

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.config import (
    OPENAI_API_KEY,
    CATEGORIZATION_PROMPT,
    INITIAL_CALL_RESPONSE_PROMPT,
    INTERVIEW_RESPONSE_PROMPT,
    APPLICATION_RESPONSE_PROMPT,
    ASSESSMENT_RESPONSE_PROMPT,
    OFFER_RESPONSE_PROMPT,
    REJECTION_RESPONSE_PROMPT,
    EMAIL_LABELS
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a file handler for AI interactions
ai_log_dir = 'logs'
if not os.path.exists(ai_log_dir):
    os.makedirs(ai_log_dir)

ai_log_file = os.path.join(ai_log_dir, 'ai_interactions.log')
ai_handler = logging.FileHandler(ai_log_file)
ai_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
logger.addHandler(ai_handler)

class OpenAIClient:
    def __init__(self):
        openai.api_key = OPENAI_API_KEY
        self.model = "gpt-4o-mini"  # Using the correct model name
        self.rate_limit_delay = 1  # Initial delay in seconds
        self.max_retries = 3
        self.tokens_used = 0
        self.last_reset_time = time.time()
        self.rate_limit_window = 60  # 1 minute window

    def _reset_token_count(self):
        """Reset token count if rate limit window has passed"""
        current_time = time.time()
        if current_time - self.last_reset_time >= self.rate_limit_window:
            self.tokens_used = 0
            self.last_reset_time = current_time

    def _update_token_count(self, tokens):
        """Update token count and check rate limit"""
        self._reset_token_count()
        self.tokens_used += tokens
        if self.tokens_used >= 200000:  # Rate limit threshold
            wait_time = self.rate_limit_window - (time.time() - self.last_reset_time)
            if wait_time > 0:
                logger.warning(f"Rate limit approaching. Waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                self._reset_token_count()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(openai.error.RateLimitError)
    )
    def _make_api_call(self, messages, temperature=0.7, max_tokens=50):
        """Make API call with rate limit handling"""
        try:
            self._reset_token_count()
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            # Estimate tokens used (rough estimation)
            estimated_tokens = len(str(messages)) // 4 + max_tokens
            self._update_token_count(estimated_tokens)
            return response
        except openai.error.RateLimitError as e:
            logger.warning(f"Rate limit hit: {str(e)}")
            wait_time = float(str(e).split("try again in ")[-1].split("ms")[0]) / 1000
            time.sleep(wait_time)
            raise
        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            raise

    def _log_ai_interaction(self, operation: str, input_data: str, output: str, error: Optional[str] = None) -> None:
        """
        Log AI interaction details to a dedicated log file.
        
        Args:
            operation (str): Type of operation (categorization/response)
            input_data (str): Input data sent to AI
            output (str): Output received from AI
            error (Optional[str]): Any error that occurred
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"\n{'='*80}\n"
        log_entry += f"Timestamp: {timestamp}\n"
        log_entry += f"Operation: {operation}\n"
        log_entry += f"Model: {self.model}\n"
        log_entry += f"\nInput:\n{'-'*40}\n{input_data}\n"
        log_entry += f"\nOutput:\n{'-'*40}\n{output}\n"
        if error:
            log_entry += f"\nError:\n{'-'*40}\n{error}\n"
        log_entry += f"{'='*80}\n"
        
        logger.info(log_entry)

    def categorize_email(self, email_content: str) -> str:
        """
        Categorize email content using ChatGPT.
        
        Args:
            email_content (str): The content of the email to categorize
            
        Returns:
            str: Category label (Application, Interview, Offer, Rejection, Other)
        """
        try:
            # Clean and prepare email content
            email_content = email_content.strip()
            if not email_content:
                logger.warning("Empty email content received, defaulting to 'Other'")
                return EMAIL_LABELS['OTHER']

            # Additional cleaning specific to categorization
            email_content = self._clean_for_categorization(email_content)

            prompt = CATEGORIZATION_PROMPT.format(email_content=email_content)
            
            response = self._make_api_call(
                messages=[
                    {"role": "system", "content": "You are an email categorization assistant. Your task is to analyze the cleaned email content and categorize it into one of the predefined categories. Focus on the main message and intent of the email, ignoring any technical elements or formatting. Respond with ONLY one of these exact labels: INITIAL_CALL, INTERVIEW, APPLICATION, ASSESSMENT, OFFER, REJECTION, OTHER."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=50
            )
            
            category = response.choices[0].message.content.strip()
            logger.info(f"Raw category response: {category}")
            
            # Map the base category to the automation label
            category_mapping = {
                'INITIAL_CALL': EMAIL_LABELS['INITIAL_CALL'],
                'INTERVIEW': EMAIL_LABELS['INTERVIEW'],
                'APPLICATION': EMAIL_LABELS['APPLICATION'],
                'ASSESSMENT': EMAIL_LABELS['ASSESSMENT'],
                'OFFER': EMAIL_LABELS['OFFER'],
                'REJECTION': EMAIL_LABELS['REJECTION'],
                'OTHER': EMAIL_LABELS['OTHER']
            }
            
            # Map the category to its automation label
            if category in category_mapping:
                category = category_mapping[category]
            else:
                logger.warning(f"Invalid category returned: {category}. Defaulting to 'Other'")
                category = EMAIL_LABELS['OTHER']
            
            # Log the AI interaction
            self._log_ai_interaction(
                operation="Email Categorization",
                input_data=email_content,
                output=f"Category: {category}\nRaw Response: {response.choices[0].message.content}"
            )
            
            logger.info(f"Successfully categorized email as: {category}")
            return category
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to categorize email: {error_msg}")
            # Log the error
            self._log_ai_interaction(
                operation="Email Categorization",
                input_data=email_content,
                output="Failed",
                error=error_msg
            )
            return EMAIL_LABELS['OTHER']

    def _clean_for_categorization(self, text: str) -> str:
        """
        Additional cleaning specific to email categorization.
        Ensures only plain text content is processed.
        
        Args:
            text (str): Text to clean
            
        Returns:
            str: Cleaned text optimized for categorization
        """
        try:
            # First, remove all HTML tags and their content
            text = re.sub(r'<[^>]+>', '', text)
            
            # Remove HTML entities
            text = re.sub(r'&[a-zA-Z]+;', '', text)
            
            # Remove any remaining technical elements
            text = re.sub(r'Content-Type:.*?\n', '', text, flags=re.DOTALL)
            text = re.sub(r'Content-Transfer-Encoding:.*?\n', '', text, flags=re.DOTALL)
            text = re.sub(r'MIME-Version:.*?\n', '', text, flags=re.DOTALL)
            
            # Remove any remaining quoted text
            text = re.sub(r'On.*wrote:.*', '', text, flags=re.DOTALL)
            
            # Remove any remaining signatures
            text = re.sub(r'--\s*\n.*', '', text, flags=re.DOTALL)
            
            # Remove any remaining headers
            text = re.sub(r'From:.*?\n', '', text, flags=re.DOTALL)
            text = re.sub(r'To:.*?\n', '', text, flags=re.DOTALL)
            text = re.sub(r'Subject:.*?\n', '', text, flags=re.DOTALL)
            text = re.sub(r'Date:.*?\n', '', text, flags=re.DOTALL)
            
            # Remove URLs
            text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
            
            # Remove email addresses
            text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '', text)
            
            # Remove multiple spaces and newlines
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n', text)
            
            # Remove any remaining special characters except basic punctuation
            text = re.sub(r'[^\w\s.,!?-]', '', text)
            
            # Final cleanup
            text = text.strip()
            
            # If the text is empty after cleaning, return a placeholder
            if not text:
                return "(No readable content)"
                
            return text
        except Exception as e:
            logger.warning(f"Failed to clean text for categorization: {str(e)}")
            return text

    def generate_response(self, email_content: str, category: str) -> Optional[str]:
        """
        Generate an appropriate response based on the email category.
        
        Args:
            email_content (str): The content of the email
            category (str): The category of the email
            
        Returns:
            Optional[str]: Generated response text or None if no response needed
        """
        try:
            if category == EMAIL_LABELS['OTHER']:
                return None

            # Select appropriate prompt based on category
            if category == EMAIL_LABELS['INITIAL_CALL']:
                prompt = INITIAL_CALL_RESPONSE_PROMPT
            elif category == EMAIL_LABELS['INTERVIEW']:
                prompt = INTERVIEW_RESPONSE_PROMPT
            elif category == EMAIL_LABELS['APPLICATION']:
                prompt = APPLICATION_RESPONSE_PROMPT
            elif category == EMAIL_LABELS['ASSESSMENT']:
                prompt = ASSESSMENT_RESPONSE_PROMPT
            elif category == EMAIL_LABELS['OFFER']:
                prompt = OFFER_RESPONSE_PROMPT
            elif category == EMAIL_LABELS['REJECTION']:
                prompt = REJECTION_RESPONSE_PROMPT
            else:
                return None

            prompt = prompt.format(email_content=email_content)
            
            response = self._make_api_call(
                messages=[
                    {"role": "system", "content": "You are an email response assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            generated_response = response.choices[0].message.content.strip()
            
            # Log the AI interaction
            self._log_ai_interaction(
                operation=f"Response Generation ({category})",
                input_data=email_content,
                output=generated_response
            )
            
            logger.info(f"Successfully generated response for {category} email")
            return generated_response
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to generate response: {error_msg}")
            # Log the error
            self._log_ai_interaction(
                operation=f"Response Generation ({category})",
                input_data=email_content,
                output="Failed",
                error=error_msg
            )
            return None 