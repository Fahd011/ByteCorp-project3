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

print("=== BROWSER SCRIPT INITIALIZATION STARTED ===")

# Fix Unicode encoding issues on Windows
import sys
import os
import logging

if sys.platform == "win32":
    # Set console to UTF-8 on Windows
    os.system("chcp 65001 > nul")
    # Set environment variable for Python
    os.environ["PYTHONIOENCODING"] = "utf-8"
    
    # Disable ALL logging to prevent Unicode errors
    logging.disable(logging.CRITICAL)
    logging.getLogger().setLevel(logging.CRITICAL)
    logging.getLogger("browser_use").setLevel(logging.CRITICAL)
    logging.getLogger("bubus").setLevel(logging.CRITICAL)
    logging.getLogger("browser_use.tokens").setLevel(logging.CRITICAL)

print("Unicode encoding setup completed")

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
    print("Supabase client imported successfully")
except Exception as e:
    print(f"Failed to import Supabase client: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    supabase_available = False

print(f"Supabase availability: {supabase_available}")

def upload_pdf_to_supabase(pdf_bytes, filename, user_id):
    """Upload PDF directly to Supabase bills bucket with retry logic"""
    if not supabase_available:
        raise Exception("Supabase client not available")
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            result = upload_pdf_to_bills_bucket(pdf_bytes, filename, user_id)
            return result
        except Exception as e:
            retry_count += 1
            error_msg = str(e)
            print(f"Supabase upload attempt {retry_count} failed: {error_msg}")
            
            # Check if it's an SSL error
            if "EOF occurred in violation of protocol" in error_msg or "ssl" in error_msg.lower() or "connection" in error_msg.lower():
                if retry_count < max_retries:
                    print(f"SSL/Connection error detected. Retrying in 3 seconds... (attempt {retry_count}/{max_retries})")
                    time.sleep(3)
                    continue
                else:
                    print(f"Supabase upload failed after {max_retries} attempts due to SSL/connection issues", file=sys.stderr)
                    import traceback
                    traceback.print_exc()
                    raise
            else:
                # Non-SSL error, don't retry
                print(f"Non-SSL Supabase upload error: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
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

# Removed monitor_downloads_and_upload function - no longer needed

def capture_and_upload_pdf(browser_session, user_id, email, temp_dir):
    """Capture PDF from browser and upload to Supabase"""
    try:
        print(f"=== PDF CAPTURE DEBUG ===")
        print(f"Starting PDF capture for {email} with user_id: {user_id}")
        print(f"Temp directory: {temp_dir}")
        print(f"Supabase available: {supabase_available}")
        
        # Check if browser session is still valid
        if not browser_session or not hasattr(browser_session, 'page'):
            print("ERROR: Browser session is not valid or has no page")
            return None
        
        # Get the current page and check all contexts/tabs
        page = browser_session.page
        print(f"Got browser page: {page}")
        
        # Check if page is still valid
        try:
            current_url = page.url
            print(f"Current page URL: {current_url}")
            
            # Check if we're on a bill page (look for common bill-related URLs)
            if 'bill' in current_url.lower() or 'statement' in current_url.lower() or 'invoice' in current_url.lower():
                print(f"Current page appears to be a bill page: {current_url}")
            else:
                print(f"Current page doesn't appear to be a bill page: {current_url}")
                # Try to find a bill page in other tabs/contexts
                try:
                    contexts = browser_session.contexts
                    print(f"Found {len(contexts)} browser contexts")
                    for i, context in enumerate(contexts):
                        pages = context.pages
                        print(f"Context {i} has {len(pages)} pages")
                        for j, p in enumerate(pages):
                            try:
                                url = p.url
                                print(f"  Page {j} URL: {url}")
                                if 'bill' in url.lower() or 'statement' in url.lower() or 'invoice' in url.lower():
                                    print(f"Found bill page in context {i}, page {j}: {url}")
                                    page = p
                                    current_url = url
                                    break
                            except Exception as e:
                                print(f"Error getting page {j} URL: {e}")
                        if 'bill' in current_url.lower() or 'statement' in current_url.lower() or 'invoice' in current_url.lower():
                            break
                except Exception as e:
                    print(f"Error checking contexts: {e}")
                    
        except Exception as e:
            print(f"ERROR: Cannot get page URL: {e}")
            return None
        
        # Wait for any downloads to complete
        print("Waiting 5 seconds for downloads...")
        time.sleep(5)
        
        # ONLY: Try to capture from current page (no downloads folder backup)
        print("Attempting to capture PDF from current page ONLY...")
        try:
            # Generate a unique filename - ensure it's safe for storage
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_email = (email.strip()
                        .replace('"', '')
                        .replace("'", '')
                        .replace(' ', '_')
                        .replace('@', '_at_')
                        .replace('/', '_')
                        .replace('\\', '_')
                        .replace(':', '_')
                        .replace('*', '_')
                        .replace('?', '_')
                        .replace('<', '_')
                        .replace('>', '_')
                        .replace('|', '_')
                        .replace('+', '_')
                        .replace('[', '_')
                        .replace(']', '_')
                        .replace('(', '_')
                        .replace(')', '_'))
            
            # Ensure the filename is not too long
            if len(safe_email) > 50:
                safe_email = safe_email[:50]
            
            filename = f"bill_{safe_email}_{timestamp}.pdf"
            
            print(f"Attempting to capture page as PDF: {filename}")
            print(f"Current page URL: {page.url}")
            
            # Try to get PDF content from current page
            print("Calling page.pdf()...")
            pdf_content = page.pdf()
            print(f"page.pdf() returned: {type(pdf_content)}, length: {len(pdf_content) if pdf_content else 0}")
            
            if pdf_content and len(pdf_content) > 0:
                print(f"Page PDF captured, size: {len(pdf_content)} bytes")
                print("First 100 bytes of PDF:", pdf_content[:100])
                
                # Validate that this looks like a real PDF (check for PDF header)
                if pdf_content.startswith(b'%PDF'):
                    print("PDF header validation passed - this looks like a real PDF")
                    
                    # Upload to Supabase
                    print("Calling upload_pdf_to_supabase...")
                    try:
                        file_url = upload_pdf_to_supabase(pdf_content, filename, user_id)
                        print(f"Upload successful, got URL: {file_url}")
                        
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
                    except Exception as upload_error:
                        print(f"Upload to Supabase failed: {upload_error}", file=sys.stderr)
                        import traceback
                        traceback.print_exc()
                else:
                    print("WARNING: Captured content does not have PDF header - not a valid PDF")
                    print("First 20 bytes:", pdf_content[:20])
            else:
                print("No PDF content captured from page - content is empty or None")
        
        except Exception as e:
            print(f"Failed to capture PDF from page: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        print("=== PDF CAPTURE COMPLETE - NO VALID PDF FOUND ===")
        print("NOTE: No downloads folder backup check - only capturing from browser page")
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
    print("Initializing OpenAI LLM...")
    llm = ChatOpenAI(model="gpt-4.1-mini")
    print("OpenAI LLM initialized successfully")
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
    print(f"Reading credentials from CSV: {csv_path}")
    creds = pd.read_csv(csv_path, skipinitialspace=True)
    usernames = creds['cred_username']
    passwords = creds['cred_password']
    print(f"Successfully read {len(usernames)} credentials from CSV")
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
        
        # Create simple browser session with SSL handling
        unique_profile_path = f'/tmp/browser_profiles/{uuid.uuid4()}'
        os.makedirs(unique_profile_path, exist_ok=True)

        browser_session = BrowserSession(
            browser_profile=BrowserProfile(
                user_data_dir=unique_profile_path,
                # Add SSL handling options
                args=[
                    '--ignore-ssl-errors',
                    '--ignore-certificate-errors',
                    '--disable-web-security',
                    '--allow-running-insecure-content',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
        )

                # Create a custom task that captures PDF directly from the browser
        custom_task = f"""
1. Go to {loginURL}.
2. Log in using:
   - Email: {email}
   - Password: {password}
3. After successful login, go to "Billing and Payment Activity".
   - If unsure, navigate directly to {billingURL}.
4. On the billing history page:
   - Find the first "View Bill" button.
    - Click it to view the bill (it may open in a new tab).
    - If the bill opens in a new tab, wait for it to load completely.
    - IMPORTANT: After clicking "View Bill", wait 10 seconds for the bill to fully load.
    - If the bill opens in a new tab, make sure you're on the bill page before proceeding.
5. Once you're on the bill page (either in same tab or new tab):
    - Wait 5 seconds to ensure the bill is fully loaded.
    - IMPORTANT: Do NOT sign out yet - stay on the bill page.
    - The task will be paused here for PDF capture.
6. After PDF capture is complete, then:
    - Go to the top right corner of the page.
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
- Stay on the bill page until you're ready to sign out
- Do not download any files - we will capture the PDF directly from the browser
"""

        agent = Agent(
            task = custom_task,
            llm=llm,
            browser_session=browser_session,
            headless=True,
        )

        # Run the agent and capture PDF directly with retry logic
        print(f"Starting browser automation for {email}...")
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                result = await agent.run()
                break  # Success, exit retry loop
            except Exception as agent_error:
                retry_count += 1
                error_msg = str(agent_error)
                print(f"Agent run attempt {retry_count} failed: {error_msg}")
                
                # Check if it's an SSL error
                if "EOF occurred in violation of protocol" in error_msg or "ssl" in error_msg.lower():
                    print(f"SSL connection error detected. Retrying in 5 seconds... (attempt {retry_count}/{max_retries})")
                    await asyncio.sleep(5)
                    continue
                elif retry_count < max_retries:
                    print(f"Non-SSL error. Retrying in 3 seconds... (attempt {retry_count}/{max_retries})")
                    await asyncio.sleep(3)
                    continue
                else:
                    # Max retries reached, re-raise the error
                    raise agent_error
        
        # After the agent completes, capture PDF directly from the browser
        print(f"Browser automation completed. Capturing PDF directly...")
        uploaded_files = []
        
        try:
            # Capture PDF directly from the browser session with retry
            captured_pdf = None
            pdf_retry_count = 0
            max_pdf_retries = 2
            
            while pdf_retry_count < max_pdf_retries and captured_pdf is None:
                try:
                    captured_pdf = capture_and_upload_pdf(browser_session, user_id, email, TEMP_DIR)
                    if captured_pdf:
                        uploaded_files.append(captured_pdf)
                        print(f"PDF captured and uploaded successfully: {captured_pdf['file_url']}")
                    else:
                        print("No PDF was captured from the browser")
                        break  # No point retrying if no PDF found
                except Exception as capture_error:
                    pdf_retry_count += 1
                    error_msg = str(capture_error)
                    print(f"PDF capture attempt {pdf_retry_count} failed: {error_msg}")
                    
                    if "EOF occurred in violation of protocol" in error_msg or "ssl" in error_msg.lower():
                        print(f"SSL error during PDF capture. Retrying in 3 seconds... (attempt {pdf_retry_count}/{max_pdf_retries})")
                        await asyncio.sleep(3)
                        continue
                    elif pdf_retry_count < max_pdf_retries:
                        print(f"Non-SSL error during PDF capture. Retrying in 2 seconds... (attempt {pdf_retry_count}/{max_pdf_retries})")
                        await asyncio.sleep(2)
                        continue
                    else:
                        # Max retries reached, log the error
                        print(f"PDF capture failed after {max_pdf_retries} attempts: {capture_error}", file=sys.stderr)
                        import traceback
                        traceback.print_exc()
        except Exception as capture_error:
            print(f"Error capturing PDF: {capture_error}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        print(f"=== AUTOMATION AND MONITORING COMPLETE ===")
        # Safely print result to avoid Unicode errors
        try:
            result_str = str(result)
            print(f"Browser automation result: {result_str}")
        except UnicodeEncodeError:
            print(f"Browser automation result: [Result contains Unicode characters]")
        
        print(f"Uploaded files: {uploaded_files}")
        
        # Safely handle result output to avoid Unicode encoding issues
        try:
            result_str = str(result)
            print(f"Success for {email}: {result_str}")
        except UnicodeEncodeError:
            # If Unicode encoding fails, just print a safe message
            print(f"Success for {email}: [Result contains Unicode characters]")
            result_str = "[Result contains Unicode characters]"
        
        # Close the browser session
        try:
            await browser_session.close()
            print("Browser session closed successfully")
        except Exception as e:
            print(f"Error closing browser session: {e}")
        
        # Record results based on uploaded files
        if uploaded_files and len(uploaded_files) > 0:
            # Multiple files might have been uploaded
            for uploaded_file in uploaded_files:
                results.append({
                    'email': email,
                    'status': 'success',
                    'error': None,
                    'result': result_str,
                    'file_url': uploaded_file['file_url'],
                    'filename': uploaded_file['filename']
                })
                print(f"PDF uplozaded to Supabase: {uploaded_file['file_url']}")
        else:
            # Record success without file URL if no PDF was found
            results.append({
                'email': email,
                'status': 'success',
                'error': None,
                'result': result_str
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
    print("=== STARTING BROWSER SCRIPT EXECUTION ===")
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

        # Write completion signal for errors
        completion_file = os.path.join(TEMP_DIR, 'browser_completion.json')
        with open(completion_file, 'w') as f:
            json.dump({
                'status': 'completed_with_error',
                'message': error_msg,
                'timestamp': str(datetime.now())
            }, f)
    else:
        # If TEMP_DIR is not set, we have a very early error
        print("ERROR: TEMP_DIR not set - this is a very early initialization error", file=sys.stderr)
        print("This suggests the script failed during import or very early initialization", file=sys.stderr)

# Write final results summary (always execute)
print(f"Writing final results: {len(results)} results")
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
    
    print(f"Completion file written with status: {completion_status}")

print(f"Processing complete. Processed {len(results)} emails.")
