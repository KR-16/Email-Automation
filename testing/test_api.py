import openai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment
# api_key = os.getenv('OPENAI_API_KEY')
api_key = "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"
if not api_key:
    print("Error: OPENAI_API_KEY not found in environment variables")
    exit(1)

# Set the API key
openai.api_key = api_key

def test_api():
    try:
        # Try a simple completion
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # Use a known working model
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello!"}
            ],
            max_tokens=10
        )
        print("API Test Successful!")
        print("Response:", response.choices[0].message.content)
    except Exception as e:
        print("API Test Failed!")
        print("Error:", str(e))

if __name__ == "__main__":
    test_api() 