from src.openai.mock_client import MockOpenAIClient

def test_email_processing():
    # Create mock client
    client = MockOpenAIClient()
    
    # Test emails
    test_emails = [
        {
            "subject": "Initial Screening Call",
            "content": """
            Dear Candidate,
            
            Thank you for your interest in the Software Engineer position.
            We would like to schedule an initial screening call to discuss your experience.
            Please let us know your availability for this week.
            
            Best regards,
            HR Team
            """
        },
        {
            "subject": "Interview Invitation",
            "content": """
            Dear Candidate,
            
            We would like to invite you for an interview for the Software Engineer position.
            Please let us know your availability for next week.
            
            Best regards,
            HR Team
            """
        },
        {
            "subject": "Application Received",
            "content": """
            Dear Candidate,
            
            We have received your application for the Software Engineer position.
            Please find attached the job description and next steps in the process.
            
            Best regards,
            HR Team
            """
        },
        {
            "subject": "Technical Assessment",
            "content": """
            Dear Candidate,
            
            As part of our selection process, we would like you to complete a technical assessment.
            Please find the instructions and deadline in the attached document.
            
            Best regards,
            HR Team
            """
        },
        {
            "subject": "Job Offer",
            "content": """
            Congratulations!
            
            We are pleased to offer you the position of Software Engineer at our company.
            Please review the attached offer letter and let us know your decision.
            
            Best regards,
            HR Team
            """
        },
        {
            "subject": "Application Status",
            "content": """
            Dear Candidate,
            
            Unfortunately, we have decided to move forward with other candidates for the position.
            We appreciate your interest in our company.
            
            Best regards,
            HR Team
            """
        }
    ]
    
    # Process each test email
    for email in test_emails:
        print(f"\nProcessing email: {email['subject']}")
        print("-" * 50)
        
        # Categorize email
        category = client.categorize_email(email['content'])
        print(f"Category: {category}")
        
        # Generate response
        response = client.generate_response(email['content'], category)
        if response:
            print("\nGenerated Response:")
            print(response)
        
        print("-" * 50)

if __name__ == "__main__":
    test_email_processing() 