def process_emails(gmail_client: GmailClient, openai_client: OpenAIClient, excel_client: ExcelClient, batch_size: int = 10) -> None:
    """
    Process emails in batches and apply labels immediately.
    
    Args:
        gmail_client (GmailClient): Gmail client instance
        openai_client (OpenAIClient): OpenAI client instance
        excel_client (ExcelClient): Excel client instance
        batch_size (int): Number of emails to process at once
    """
    try:
        # Get emails in batches
        emails = gmail_client.get_emails(time_range='today', batch_size=batch_size)
        
        # Process each batch
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} of {(len(emails) + batch_size - 1)//batch_size}")
            
            # Process each email in the batch
            for email_data in batch:
                try:
                    # Categorize email
                    category = openai_client.categorize_email(
                        subject=email_data['subject'],
                        body=email_data['body'],
                        sender=email_data['sender']
                    )
                    
                    # Apply label immediately
                    label_name = f"{category}_automation"
                    gmail_client.apply_label(email_data['id'], label_name)
                    
                    # Update Excel with results
                    excel_client.save_data({
                        'Email': gmail_client.email,
                        'Date': email_data['date'],
                        'Sender': email_data['sender'],
                        'Subject': email_data['subject'],
                        'Category': category,
                        'Label': label_name
                    })
                    
                    logger.info(f"Processed email {email_data['id']} - Category: {category}")
                    
                except Exception as e:
                    logger.error(f"Error processing email {email_data['id']}: {str(e)}")
                    continue
            
            # Save intermediate results after each batch
            excel_client.save()
            logger.info(f"Saved intermediate results after batch {i//batch_size + 1}")
        
        logger.info("Completed processing all emails")
        
    except Exception as e:
        logger.error(f"Error in process_emails: {str(e)}")
        raise

def main():
    try:
        # Initialize clients
        gmail_client = GmailClient(email=GMAIL_EMAIL, password=GMAIL_PASSWORD)
        openai_client = OpenAIClient(api_key=OPENAI_API_KEY)
        excel_client = ExcelClient(file_path=EXCEL_FILE)
        
        # Process emails in batches
        process_emails(gmail_client, openai_client, excel_client, batch_size=10)
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise 