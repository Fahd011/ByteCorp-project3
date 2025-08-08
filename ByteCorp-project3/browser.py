from browser_use.llm import ChatOpenAI
from browser_use import Agent
from dotenv import load_dotenv
from browser_use.browser import BrowserSession, BrowserProfile
import pandas as pd
import asyncio
import os
import uuid
import sys
import signal
import json
import traceback
from datetime import datetime

load_dotenv()
bill_count = 0

# Set up signal handler for graceful shutdown
def signal_handler(signum, frame):
    print("Received stop signal. Cleaning up...", file=sys.stderr)
    # Write completion signal
    completion_file = os.path.join(os.path.dirname(__file__), 'temp', 'browser_completion.json')
    os.makedirs(os.path.dirname(completion_file), exist_ok=True)
    with open(completion_file, 'w') as f:
        json.dump({
            'status': 'interrupted',
            'message': 'Process interrupted by signal',
            'timestamp': str(datetime.now())
        }, f)
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Initialize LLM with error handling
try:
    llm = ChatOpenAI(model="gpt-4.1-mini")
    # Note: We'll test the LLM when it's actually used in the agent
except Exception as e:
    error_msg = f"OpenAI API Error: {str(e)}"
    if "insufficient_quota" in str(e).lower() or "quota" in str(e).lower():
        error_msg = "OpenAI API Error: Insufficient tokens/quota. Please add more tokens to continue."
    elif "invalid_api_key" in str(e).lower() or "authentication" in str(e).lower():
        error_msg = "OpenAI API Error: Invalid API key. Please check your OpenAI API key."
    else:
        error_msg = f"OpenAI API Error: {str(e)}"
    
    # Write error to a file that agent_runner can read
    error_file = os.path.join(os.path.dirname(__file__), 'temp', 'browser_error.json')
    os.makedirs(os.path.dirname(error_file), exist_ok=True)
    with open(error_file, 'w') as f:
        json.dump({
            'error': error_msg,
            'type': 'openai_error',
            'timestamp': str(datetime.now())
        }, f)
    
    # Write completion signal
    completion_file = os.path.join(os.path.dirname(__file__), 'temp', 'browser_completion.json')
    with open(completion_file, 'w') as f:
        json.dump({
            'status': 'completed_with_error',
            'message': error_msg,
            'timestamp': str(datetime.now())
        }, f)
    
    print(error_msg, file=sys.stderr)
    sys.exit(1)

# Get required environment variables
csv_path = os.getenv('CSV_PATH')
loginURL = os.getenv('LOGIN_URL')
billingURL = os.getenv('BILLING_URL')

# Validate required environment variables
if not all([csv_path, loginURL, billingURL]):
    error_msg = "Error: Missing required environment variables. Need CSV_PATH, LOGIN_URL, and BILLING_URL"
    print(error_msg, file=sys.stderr)
    
    # Write error to file
    error_file = os.path.join(os.path.dirname(__file__), 'temp', 'browser_error.json')
    os.makedirs(os.path.dirname(error_file), exist_ok=True)
    with open(error_file, 'w') as f:
        json.dump({
            'error': error_msg,
            'type': 'env_error',
            'timestamp': str(datetime.now())
        }, f)
    
    # Write completion signal
    completion_file = os.path.join(os.path.dirname(__file__), 'temp', 'browser_completion.json')
    with open(completion_file, 'w') as f:
        json.dump({
            'status': 'completed_with_error',
            'message': error_msg,
            'timestamp': str(datetime.now())
        }, f)
    
    sys.exit(1)

# Read credentials from the CSV file
try:
    creds = pd.read_csv(csv_path, skipinitialspace=True)
    usernames = creds['cred_username']
    passwords = creds['cred_password']
except Exception as e:
    error_msg = f"Error reading credentials from {csv_path}: {str(e)}"
    print(error_msg, file=sys.stderr)
    
    # Write error to file
    error_file = os.path.join(os.path.dirname(__file__), 'temp', 'browser_error.json')
    os.makedirs(os.path.dirname(error_file), exist_ok=True)
    with open(error_file, 'w') as f:
        json.dump({
            'error': error_msg,
            'type': 'csv_error',
            'timestamp': str(datetime.now())
        }, f)
    
    # Write completion signal
    completion_file = os.path.join(os.path.dirname(__file__), 'temp', 'browser_completion.json')
    with open(completion_file, 'w') as f:
        json.dump({
            'status': 'completed_with_error',
            'message': error_msg,
            'timestamp': str(datetime.now())
        }, f)
    
    sys.exit(1)

# Track results for each email
results = []

async def process_email(email, password, bill_count):
    """Process a single email with proper error handling"""
    try:
        # Unique user data dir to isolate sessions
        unique_profile_path = f'/tmp/browser_profiles/{uuid.uuid4()}'
        os.makedirs(unique_profile_path, exist_ok=True)

        browser_session = BrowserSession(
            browser_profile=BrowserProfile(
                downloads_path=os.path.expanduser('~/Downloads'),
                user_data_dir=unique_profile_path,
            )
        )

        agent = Agent(
            task = f"""
1. Go to {loginURL}.
2. Log in using:
   - Email: {email}
   - Password: {password}
3. After successful login, go to "Billing and Payment Activity".
   - If unsure, navigate directly to {billingURL}.
4. On the billing history page:
   - Find the first "View Bill" button.
   - Click it to download the bill (the download may happen silently).
5. Wait at least 5 seconds after clicking to ensure the download is triggered.
6. Now, go to the top right corner of the page.
   - Click the user icon (showing {email}).
   - Select "Sign out" from the dropdown.
7. Confirm that you are signed out:
   - You should be redirected to the **main homepage**.
   - After reaching the homepage and confirming logout, do not click or navigate anywhere. 
     The task is finished. Do not revisit any links or pages after logout. Do not open new tabs.
8. If you see a page that says "Something went wrong", stop the task.

Important:
- Do not revisit the billing history page after logout.
- Do not click on "Pay My Bill" or similar options.
- If no elements are interactable, wait 5 seconds — the page might still be loading. Repeat until page has loaded
- Only download 1 pdf. Never more than 1
""",
            llm=llm,
            browser_session=browser_session,
            headless=True,
        )

        result = await agent.run()
        print(f"Success for {email}: {result}")
        
        # Record success
        results.append({
            'email': email,
            'status': 'success',
            'error': None,
            'result': str(result)
        })
        
        return True
        
    except Exception as e:
        error_msg = f"Error processing {email}: {str(e)}"
        print(error_msg, file=sys.stderr)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        
        # Record error
        results.append({
            'email': email,
            'status': 'error',
            'error': str(e),
            'result': None
        })
        
        # Write error to file for agent_runner to read
        error_file = os.path.join(os.path.dirname(__file__), 'temp', 'browser_error.json')
        os.makedirs(os.path.dirname(error_file), exist_ok=True)
        with open(error_file, 'w') as f:
            json.dump({
                'error': error_msg,
                'type': 'processing_error',
                'email': email,
                'timestamp': str(datetime.now()),
                'traceback': traceback.format_exc()
            }, f)
        
        return False

async def main():
    """Main async function to process all emails"""
    global bill_count
    
    for email, password in zip(usernames, passwords):
        try:
            success = await process_email(email, password, bill_count)
            if success:
                bill_count += 1
        except Exception as e:
            error_msg = f"Critical error in main loop for {email}: {str(e)}"
            print(error_msg, file=sys.stderr)
            print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
            
            # Write error to file
            error_file = os.path.join(os.path.dirname(__file__), 'temp', 'browser_error.json')
            os.makedirs(os.path.dirname(error_file), exist_ok=True)
            with open(error_file, 'w') as f:
                json.dump({
                    'error': error_msg,
                    'type': 'critical_error',
                    'email': email,
                    'timestamp': str(datetime.now()),
                    'traceback': traceback.format_exc()
                }, f)

# Run the main async function
try:
    asyncio.run(main())
except Exception as e:
    error_msg = f"Critical error in asyncio.run: {str(e)}"
    print(error_msg, file=sys.stderr)
    print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
    
    # Write error to file
    error_file = os.path.join(os.path.dirname(__file__), 'temp', 'browser_error.json')
    os.makedirs(os.path.dirname(error_file), exist_ok=True)
    with open(error_file, 'w') as f:
        json.dump({
            'error': error_msg,
            'type': 'asyncio_error',
            'timestamp': str(datetime.now()),
            'traceback': traceback.format_exc()
        }, f)

# Write final results summary
results_file = os.path.join(os.path.dirname(__file__), 'temp', 'browser_results.json')
os.makedirs(os.path.dirname(results_file), exist_ok=True)
with open(results_file, 'w') as f:
    json.dump({
        'results': results,
        'total_processed': len(results),
        'successful': len([r for r in results if r['status'] == 'success']),
        'failed': len([r for r in results if r['status'] == 'error']),
        'timestamp': str(datetime.now())
    }, f)

# Write completion signal
completion_file = os.path.join(os.path.dirname(__file__), 'temp', 'browser_completion.json')
with open(completion_file, 'w') as f:
    json.dump({
        'status': 'completed',
        'message': f'Processing complete. Processed {len(results)} emails.',
        'total_processed': len(results),
        'successful': len([r for r in results if r['status'] == 'success']),
        'failed': len([r for r in results if r['status'] == 'error']),
        'timestamp': str(datetime.now())
    }, f)

print(f"Processing complete. Processed {len(results)} emails.")