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
import base64
from supabase import create_client
import time
import glob
import tempfile

load_dotenv()
bill_count = 0

# Global variable to store captured PDFs
captured_pdfs = []

# Global temp directory - will be set in main()
TEMP_DIR = None

# Initialize Supabase client for direct PDF uploads
try:
    # Add the parent directory to sys.path to import backend modules
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from supabase_client import upload_pdf_to_bills_bucket
    BILLS_BUCKET = "bills"
    supabase_available = True
except Exception as e:
    print(f"Failed to import Supabase client: {e}", file=sys.stderr)
    supabase_available = False

def upload_pdf_to_supabase(pdf_bytes, filename, user_id):
    """Upload PDF directly to Supabase bills bucket"""
    if not supabase_available:
        raise Exception("Supabase client not available")
    
    try:
        return upload_pdf_to_bills_bucket(pdf_bytes, filename, user_id)
    except Exception as e:
        print(f"Supabase upload error: {e}", file=sys.stderr)
        raise

def write_real_time_result(result_data, temp_dir):
    """Write a result to a real-time results file"""
    real_time_file = os.path.join(temp_dir, 'real_time_results.json')
    
    # Read existing results
    existing_results = []
    if os.path.exists(real_time_file):
        try:
            with open(real_time_file, 'r') as f:
                existing_results = json.load(f)
        except Exception as e:
            print(f"Error reading real-time results: {e}", file=sys.stderr)
    
    # Add new result
    existing_results.append(result_data)
    
    # Write updated results
    try:
        with open(real_time_file, 'w') as f:
            json.dump(existing_results, f, indent=2)
    except Exception as e:
        print(f"Error writing real-time results: {e}", file=sys.stderr)

def capture_and_upload_pdf(browser_session, user_id, email, temp_dir):
    """Capture PDF from browser and upload to Supabase"""
    try:
        print(f"=== PDF CAPTURE DEBUG ===")
        print(f"Starting PDF capture for {email} with user_id: {user_id}")
        print(f"Temp directory: {temp_dir}")
        print(f"Supabase available: {supabase_available}")
        
        # Get the current page
        page = browser_session.page
        print(f"Got browser page: {page}")
        
        # Wait for any downloads to complete
        print("Waiting 3 seconds for downloads...")
        time.sleep(3)
        
        # Check if there's a PDF download in progress or completed
        downloads_path = os.path.expanduser('~/Downloads')
        print(f"Checking downloads path: {downloads_path}")
        
        if os.path.exists(downloads_path):
            # Look for recently created PDF files
            current_time = time.time()
            all_files = os.listdir(downloads_path)
            pdf_files = [f for f in all_files if f.endswith('.pdf')]
            print(f"All files in downloads: {all_files}")
            print(f"Found {len(pdf_files)} PDF files in downloads: {pdf_files}")
            
            for filename in pdf_files:
                file_path = os.path.join(downloads_path, filename)
                file_time = os.path.getctime(file_path)
                time_diff = current_time - file_time
                
                print(f"PDF file: {filename}, created {time_diff:.1f} seconds ago")
                
                # Check if file was created in the last 30 seconds (increased from 10)
                if time_diff < 30:
                    print(f"Processing recent PDF: {filename}")
                    try:
                        # Read the PDF file
                        with open(file_path, 'rb') as f:
                            pdf_bytes = f.read()
                        
                        print(f"Read PDF file, size: {len(pdf_bytes)} bytes")
                        
                        # Upload to Supabase
                        print("Uploading to Supabase...")
                        file_url = upload_pdf_to_supabase(pdf_bytes, filename, user_id)
                        
                        # Write real-time result
                        result_data = {
                            'email': email,
                            'status': 'success',
                            'error': None,
                            'file_url': file_url,
                            'filename': filename,
                            'timestamp': str(datetime.now())
                        }
                        write_real_time_result(result_data, temp_dir)
                        
                        print(f"PDF captured and uploaded to Supabase: {file_url}")
                        
                        # Remove local file
                        os.remove(file_path)
                        print(f"Removed local file: {file_path}")
                        
                        return {
                            'email': email,
                            'filename': filename,
                            'file_url': file_url,
                            'local_path': file_path
                        }
                        
                    except Exception as e:
                        print(f"Failed to process PDF {filename}: {e}", file=sys.stderr)
                        import traceback
                        traceback.print_exc()
                        # Remove corrupted file
                        try:
                            os.remove(file_path)
                        except:
                            pass
                else:
                    print(f"PDF file {filename} is too old ({time_diff:.1f} seconds)")
        else:
            print(f"Downloads directory does not exist: {downloads_path}")
        
        # If no PDF found in downloads, try to capture from current page
        print("No recent PDFs found, trying to capture from current page...")
        try:
            # Generate a unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"bill_{email.replace('@', '_at_')}_{timestamp}.pdf"
            
            print(f"Attempting to capture page as PDF: {filename}")
            
            # Try to get PDF content from current page
            pdf_content = page.pdf()
            
            if pdf_content:
                print(f"Page PDF captured, size: {len(pdf_content)} bytes")
                # Upload to Supabase
                file_url = upload_pdf_to_supabase(pdf_content, filename, user_id)
                
                # Write real-time result
                result_data = {
                    'email': email,
                    'status': 'success',
                    'error': None,
                    'file_url': file_url,
                    'filename': filename,
                    'timestamp': str(datetime.now())
                }
                write_real_time_result(result_data, temp_dir)
                
                print(f"PDF captured from page and uploaded to Supabase: {file_url}")
                
                return {
                    'email': email,
                    'filename': filename,
                    'file_url': file_url,
                    'local_path': None
                }
            else:
                print("No PDF content captured from page")
        
        except Exception as e:
            print(f"Failed to capture PDF from page: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        print("=== PDF CAPTURE COMPLETE - NO PDF FOUND ===")
        return None
        
    except Exception as e:
        print(f"Error in capture_and_upload_pdf: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return None

# Set up signal handler for graceful shutdown
def signal_handler(signum, frame):
    print("Received stop signal. Cleaning up...", file=sys.stderr)
    if TEMP_DIR:
        # Write completion signal
        completion_file = os.path.join(TEMP_DIR, 'browser_completion.json')
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
    if TEMP_DIR:
        error_file = os.path.join(TEMP_DIR, 'browser_error.json')
        os.makedirs(os.path.dirname(error_file), exist_ok=True)
        with open(error_file, 'w') as f:
            json.dump({
                'error': error_msg,
                'type': 'openai_error',
                'timestamp': str(datetime.now())
            }, f)
        
        # Write completion signal
        completion_file = os.path.join(TEMP_DIR, 'browser_completion.json')
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
    if TEMP_DIR:
        error_file = os.path.join(TEMP_DIR, 'browser_error.json')
        os.makedirs(os.path.dirname(error_file), exist_ok=True)
        with open(error_file, 'w') as f:
            json.dump({
                'error': error_msg,
                'type': 'env_error',
                'timestamp': str(datetime.now())
            }, f)
        
        # Write completion signal
        completion_file = os.path.join(TEMP_DIR, 'browser_completion.json')
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
    if TEMP_DIR:
        error_file = os.path.join(TEMP_DIR, 'browser_error.json')
        os.makedirs(os.path.dirname(error_file), exist_ok=True)
        with open(error_file, 'w') as f:
            json.dump({
                'error': error_msg,
                'type': 'csv_error',
                'timestamp': str(datetime.now())
            }, f)
        
        # Write completion signal
        completion_file = os.path.join(TEMP_DIR, 'browser_completion.json')
        with open(completion_file, 'w') as f:
            json.dump({
                'status': 'completed_with_error',
                'message': error_msg,
                'timestamp': str(datetime.now())
            }, f)
    
    sys.exit(1)

# Global results list
results = []

async def process_email(email, password, bill_count):
    """Process a single email/password combination"""
    try:
        print(f"Processing email: {email}")
        
        # Get user_id from environment
        user_id = os.getenv('USER_ID')
        if not user_id:
            print("Warning: USER_ID not found in environment, using default", file=sys.stderr)
            user_id = 'default_user'
        
        # Create simple browser session
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
   - Click it to view the bill (it may open in a new tab or download).
   - If the bill opens in a new tab, wait for it to load completely.
   - If it downloads, wait for the download to complete.
5. Wait at least 5 seconds after clicking to ensure the bill is loaded/downloaded.
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
- Only process 1 bill. Never more than 1
- Make sure to wait for any downloads to complete before proceeding
""",
            llm=llm,
            browser_session=browser_session,
            headless=True,
        )

        result = await agent.run()
        print(f"Success for {email}: {result}")
        
        print(f"=== STARTING PDF CAPTURE PROCESS ===")
        print(f"About to call capture_and_upload_pdf with:")
        print(f"  - user_id: {user_id}")
        print(f"  - email: {email}")
        print(f"  - temp_dir: {TEMP_DIR}")
        print(f"  - supabase_available: {supabase_available}")
        
        # Simple PDF capture and upload
        uploaded_file = capture_and_upload_pdf(browser_session, user_id, email, TEMP_DIR)
        print(f"=== PDF CAPTURE PROCESS COMPLETE ===")
        print(f"Uploaded file result: {uploaded_file}")
        
        # Record results based on uploaded file
        if uploaded_file:
            results.append({
                'email': email,
                'status': 'success',
                'error': None,
                'result': str(result),
                'file_url': uploaded_file['file_url'],
                'filename': uploaded_file['filename']
            })
            print(f"PDF uploaded to Supabase: {uploaded_file['file_url']}")
        else:
            # Record success without file URL if no PDF was found
            results.append({
                'email': email,
                'status': 'success',
                'error': None,
                'result': str(result)
            })
            print(f"No PDF found for {email}")
        
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
        if TEMP_DIR:
            error_file = os.path.join(TEMP_DIR, 'browser_error.json')
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
    """Main function to run the browser automation"""
    global TEMP_DIR
    
    print("=== BROWSER SCRIPT STARTED ===")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Environment variables:")
    print(f"  CSV_PATH: {os.getenv('CSV_PATH')}")
    print(f"  LOGIN_URL: {os.getenv('LOGIN_URL')}")
    print(f"  BILLING_URL: {os.getenv('BILLING_URL')}")
    print(f"  USER_ID: {os.getenv('USER_ID')}")
    print(f"  SESSION_ID: {os.getenv('SESSION_ID')}")
    print(f"  Supabase available: {supabase_available}")
    
    # Check if required environment variables are set
    csv_path = os.getenv('CSV_PATH')
    login_url = os.getenv('LOGIN_URL')
    billing_url = os.getenv('BILLING_URL')
    user_id = os.getenv('USER_ID')
    
    if not all([csv_path, login_url, billing_url, user_id]):
        print("Error: Missing required environment variables. Need CSV_PATH, LOGIN_URL, and BILLING_URL")
        sys.exit(1)
    
    # Initialize temp directory
    TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp', f'job_{os.getenv("SESSION_ID", "unknown")}')
    os.makedirs(TEMP_DIR, exist_ok=True)
    print(f"Using temp directory: {TEMP_DIR}")
    
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
            if TEMP_DIR:
                error_file = os.path.join(TEMP_DIR, 'browser_error.json')
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
    if TEMP_DIR:
        error_file = os.path.join(TEMP_DIR, 'browser_error.json')
        os.makedirs(os.path.dirname(error_file), exist_ok=True)
        with open(error_file, 'w') as f:
            json.dump({
                'error': error_msg,
                'type': 'asyncio_error',
                'timestamp': str(datetime.now()),
                'traceback': traceback.format_exc()
            }, f)

# Write final results summary
if TEMP_DIR:
    results_file = os.path.join(TEMP_DIR, 'browser_results.json')
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
    completion_file = os.path.join(TEMP_DIR, 'browser_completion.json')
    with open(completion_file, 'w') as f:
        # Determine completion status based on results
        has_errors = any(r['status'] == 'error' for r in results)
        completion_status = 'completed_with_error' if has_errors else 'completed'
        
        json.dump({
            'status': completion_status,
            'message': f'Processing complete. Processed {len(results)} emails.',
            'total_processed': len(results),
            'successful': len([r for r in results if r['status'] == 'success']),
            'failed': len([r for r in results if r['status'] == 'error']),
            'timestamp': str(datetime.now())
        }, f)

print(f"Processing complete. Processed {len(results)} emails.")
