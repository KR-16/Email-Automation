import os
from .settings import (
    OPENAI_API_KEY,
    EXCEL_FILE_PATH,
    GMAIL_CREDENTIALS_FILE,
    GMAIL_TOKEN_FILE,
    GMAIL_SCOPES
)

# Email Labels
EMAIL_LABELS = {
    'INITIAL_CALL': 'Initial Call Automation',
    'INTERVIEW': 'Interview Automation  ',
    'APPLICATION': 'Application Automation',
    'ASSESSMENT': 'Assessment Automation',
    'OFFER': 'Offer Automation',
    'REJECTION': 'Rejection Automation',
    'OTHER': 'Other Automation'
}

# ChatGPT Prompts
CATEGORIZATION_PROMPT = """
You are an expert at categorizing job-related emails. Analyze the following email content and respond with EXACTLY ONE of the following labels and NOTHING ELSE:

• Initial Call
  – If the email is about:
  - First contact with candidate
  - Schedule initial screening
  - Basic qualification check
  - Introduction to the role and company

• Interview
  – If the email is about:
  - Interview scheduling
  - Interview confirmation
  - Interview preparation details
  - Interview feedback
  - Interview follow-up

• Application
  – If the email is about:
  - Application received confirmation
  - Application status updates
  - Request for additional information
  - Document collection
  - Application review process

• Assessment
  – If the email is about:
  - Technical assessment instructions
  - Assessment deadline reminders
  - Assessment feedback
  - Next steps after assessment
  - Assessment results communication

• Offer
  – If the email contains:
  - Job offer details
  - Salary/compensation discussion
  - Benefits information
  - Start date confirmation
  - Offer acceptance/negotiation
  - Onboarding preparation

• Rejection
  – If the email:
  - Declines the application
  - Indicates the candidate wasn't selected
  - Suggests applying for other positions
  - Provides feedback on the application
  - Professional closure

• Other
  – If the email doesn't clearly fit the above categories or is about:
  - General company information
  - Networking
  - Job alerts
  - Newsletter
  - Marketing content

Respond with EXACTLY ONE of these labels and NOTHING ELSE:
- Initial Call
- Interview
- Application
- Assessment
- Offer
- Rejection
- Other

Email content:
{email_content}
"""

# Response Generation Prompts
INITIAL_CALL_RESPONSE_PROMPT = """
You are a professional job candidate. Based on the following initial contact email, draft a concise and professional response that:

1. Acknowledges receipt of the initial contact
2. Expresses interest in the opportunity
3. Confirms availability for initial screening
4. Asks any relevant clarifying questions
5. Maintains a professional and enthusiastic tone

Keep the response under 150 words and focus on being clear and direct.

Email content:
{email_content}
"""

INTERVIEW_RESPONSE_PROMPT = """
You are a professional job candidate. Based on the following interview-related email, draft a concise and professional response email that:

1. Acknowledges receipt of the interview details
2. Confirms availability for the scheduled time
3. Asks any relevant clarifying questions
4. Expresses enthusiasm for the opportunity
5. Maintains a professional and courteous tone

Keep the response under 150 words and focus on being clear and direct.

Email content:
{email_content}
"""

APPLICATION_RESPONSE_PROMPT = """
You are a professional job candidate. Based on the following application-related email, draft a professional response that:

1. Acknowledges receipt of the application request/status
2. Confirms understanding of the requirements
3. Provides requested information or documents
4. Asks any relevant clarifying questions
5. Maintains a professional and proactive tone

Keep the response under 150 words and focus on being thorough and responsive.

Email content:
{email_content}
"""

ASSESSMENT_RESPONSE_PROMPT = """
You are a professional job candidate. Based on the following assessment-related email, draft a professional response that:

1. Acknowledges receipt of the assessment details
2. Confirms understanding of the requirements
3. Asks any relevant clarifying questions
4. Expresses readiness to proceed
5. Maintains a professional and confident tone

Keep the response under 150 words and focus on being prepared and professional.

Email content:
{email_content}
"""

OFFER_RESPONSE_PROMPT = """
You are a professional job candidate. Based on the following job offer email, draft a professional response that:

1. Expresses genuine gratitude for the offer
2. Acknowledges receipt of all offer details
3. Requests a specific timeframe to review the offer (e.g., "I would appreciate 2-3 business days to review the details")
4. Mentions any specific points you'd like to discuss
5. Maintains a positive and professional tone

Keep the response under 150 words and focus on being appreciative while requesting time to consider.

Email content:
{email_content}
"""

REJECTION_RESPONSE_PROMPT = """
You are a professional job candidate. Based on the following rejection email, draft a polite and professional response that:

1. Expresses genuine gratitude for the opportunity
2. Acknowledges the decision professionally
3. Maintains a positive tone
4. Keeps the door open for future opportunities
5. Shows appreciation for the time and consideration

Keep the response under 100 words and focus on maintaining a positive relationship.

Email content:
{email_content}
""" 