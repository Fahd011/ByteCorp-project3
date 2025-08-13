#!/usr/bin/env python3
"""
Simplified Browser Script for Duke Energy Bill Download
Downloads only the latest bill and uploads to Supabase
"""

# Import required modules first
import sys
import os
import locale

# Fix Unicode encoding issues on Windows
if sys.platform == "win32":
    # Set environment variables for UTF-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONLEGACYWINDOWSSTDIO'] = 'utf-8'
    
    # Set console code page to UTF-8
    try:
        import subprocess
        subprocess.run(['chcp', '65001'], shell=True, capture_output=True)
    except:
        pass
    
    # Configure locale for UTF-8
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except:
            pass  # Use default if UTF-8 locale not available
    
    # Fix browser-use library logging issues
    import logging
    import codecs
    
    # Configure logging to handle Unicode properly
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Override the default logging handler to handle Unicode
    class UnicodeStreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                msg = self.format(record)
                stream = self.stream
                # Encode as UTF-8 and decode as UTF-8 to handle Unicode properly
                stream.buffer.write(msg.encode('utf-8'))
                stream.buffer.flush()
            except Exception:
                self.handleError(record)
    
    # Replace the default handler
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.addHandler(UnicodeStreamHandler(sys.stdout))
    
    # Monkey patch browser-use logging to handle Unicode
    def safe_log_emit(self, record):
        try:
            msg = self.format(record)
            # Remove or replace problematic Unicode characters
            msg = msg.encode('ascii', 'replace').decode('ascii')
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            pass  # Silently ignore Unicode errors
    
    # Apply the patch to StreamHandler
    logging.StreamHandler.emit = safe_log_emit

from browser_use.llm import ChatOpenAI
from browser_use import Agent
from dotenv import load_dotenv
from browser_use.browser import BrowserSession, BrowserProfile
import pandas as pd
import asyncio
import json
import uuid
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from supabase_client import upload_pdf_to_bills_bucket

load_dotenv()

# Global variables
TEMP_DIR = None
results = []

def upload_pdf_to_supabase(pdf_bytes, filename, user_id):
    """Upload PDF to Supabase with verification"""
    try:
        print(f"[UPLOAD] Uploading {filename} to Supabase...")
        file_url = upload_pdf_to_bills_bucket(pdf_bytes, filename, user_id)
        print(f"[UPLOAD] Success! File URL: {file_url}")
        return file_url
    except Exception as e:
        print(f"[UPLOAD] Error: {e}")
        raise

def create_safe_filename(email):
    """Create a safe filename from email"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # Remove quotes, spaces, and other invalid characters
    clean_email = email.strip().replace('"', '').replace("'", '').replace(' ', '')
    safe_email = clean_email.replace('@', '_at_').replace('.', '_').replace('+', '_')
    # Ensure filename is safe for storage
    safe_filename = f"bill_{safe_email}_{timestamp}.pdf"
    # Additional safety check - remove any remaining problematic characters
    safe_filename = ''.join(c for c in safe_filename if c.isalnum() or c in '._-')
    return safe_filename

def get_latest_pdf(downloads_folder, before_files):
    """Get the newly downloaded PDF file"""
    after_files = set(os.listdir(downloads_folder))
    new_files = after_files - before_files
    pdf_files = [f for f in new_files if f.lower().endswith('.pdf')]
    if not pdf_files:
        return None
    latest_pdf = max(pdf_files, key=lambda f: os.path.getctime(os.path.join(downloads_folder, f)))
    return latest_pdf

async def process_single_email(email, password, user_id, login_url, billing_url, downloads_folder):
    """Process a single email - download one bill only"""
    
    browser_session = None
    try:
        print(f"\n{'='*60}")
        print(f"[EMAIL] Processing: {email}")
        print(f"{'='*60}")
        
        # Create browser session
        unique_profile_path = f'/tmp/browser_profiles/{uuid.uuid4()}'
        os.makedirs(unique_profile_path, exist_ok=True)
        
        print(f"[BROWSER] Creating browser session with profile: {unique_profile_path}")
        browser_session = BrowserSession(
            browser_profile=BrowserProfile(
                downloads_path=downloads_folder,
                user_data_dir=unique_profile_path,
            )
        )
        print(f"[BROWSER] Browser session created successfully")
        
        print(f"[BROWSER] Browser session created for {email}")
        
        # Record files in Downloads before download
        before_files = set(os.listdir(downloads_folder))
        
        # Create agent for bill download
        agent = Agent(
            task=f"""
1. Go to {login_url}.
2. Log in using:
   - Email: {email}
   - Password: {password}
3. Then go to this url: {billing_url}
4. On the billing history page:
   - download only download the first bill
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
            llm=ChatOpenAI(model="gpt-4o-mini"),
            browser_session=browser_session,
            headless=True,
        )
        
        print(f"[AGENT] Running agent for {email}...")
        try:
            result = await asyncio.wait_for(agent.run(), timeout=300)  # 5 minute timeout
            print(f"[AGENT] Agent completed for {email}")
            print(f"[AGENT] Agent result: {result}")
        except asyncio.TimeoutError:
            print(f"[TIMEOUT] Agent timed out after 5 minutes for {email}")
            result = "Agent timed out - task took too long"
        except Exception as agent_error:
            print(f"[AGENT_ERROR] Agent failed with error: {agent_error}")
            result = f"Agent error: {str(agent_error)}"
        
        # Check if agent reported login failure
        if result and isinstance(result, str):
            if "login failed" in result.lower() or "application error" in result.lower():
                print(f"[LOGIN] Agent reported login failure")
                results.append({
                    'email': email,
                    'status': 'error',
                    'error': 'Login failed - application error or invalid credentials',
                    'result': str(result)
                })
                return False
        
        # Check current URL to see if login was successful
        try:
            current_url = browser_session.page.url
            print(f"[URL] Current URL after agent run: {current_url}")
            
            # Check if we're still on login page
            if 'sign-in' in current_url.lower() or 'login' in current_url.lower():
                print(f"[WARN] Still on login page - login may have failed")
            elif 'error' in current_url.lower():
                print(f"[WARN] On error page - something went wrong")
            else:
                print(f"[OK] Not on login page - login appears successful")
        except Exception as e:
            print(f"[ERROR] Could not get current URL: {e}")
        
        # Wait for download to complete
        time.sleep(5)
        
        # Check for downloaded file
        downloaded_file = get_latest_pdf(downloads_folder, before_files)
        print(f"[DOWNLOAD] Looking for downloaded files in: {downloads_folder}")
        print(f"[DOWNLOAD] Files before download: {len(before_files)}")
        print(f"[DOWNLOAD] Files after download: {len(set(os.listdir(downloads_folder)))}")
        print(f"[DOWNLOAD] New files: {set(os.listdir(downloads_folder)) - before_files}")
        
        if downloaded_file:
            print(f"[DOWNLOAD] Found downloaded file: {downloaded_file}")
            
            # Read the PDF file
            pdf_path = os.path.join(downloads_folder, downloaded_file)
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
            
            if not pdf_content or len(pdf_content) == 0:
                print(f"[ERROR] Empty PDF file")
                results.append({
                    'email': email,
                    'status': 'error',
                    'error': 'Empty PDF file downloaded',
                    'result': str(result)
                })
                return False
            
            # Validate PDF
            if not pdf_content.startswith(b'%PDF'):
                print(f"[ERROR] Invalid PDF content")
                results.append({
                    'email': email,
                    'status': 'error',
                    'error': 'Invalid PDF content',
                    'result': str(result)
                })
                return False
            
            print(f"[PDF] PDF downloaded successfully: {len(pdf_content)} bytes")
            
            # Create safe filename and upload to Supabase
            filename = create_safe_filename(email)
            print(f"[FILENAME] Generated safe filename: {filename}")
            print(f"[FILENAME] Original email: '{email}'")
            print(f"[FILENAME] User ID: {user_id}")
            
            try:
                print(f"[UPLOAD] Attempting to upload {len(pdf_content)} bytes to Supabase...")
                file_url = upload_pdf_to_supabase(pdf_content, filename, user_id)
                
                # Write real-time result
                result_data = {
                    'email': email,
                    'status': 'success',
                    'error': None,
                    'file_url': file_url,
                    'filename': filename,
                    'timestamp': str(datetime.now()),
                    'pdf_size': len(pdf_content)
                }
                
                # Write to real-time results file
                if TEMP_DIR:
                    real_time_file = os.path.join(TEMP_DIR, 'real_time_results.json')
                    existing_results = []
                    if os.path.exists(real_time_file):
                        try:
                            with open(real_time_file, 'r') as f:
                                existing_results = json.load(f)
                        except:
                            existing_results = []
                    
                    existing_results.append(result_data)
                    
                    with open(real_time_file, 'w') as f:
                        json.dump(existing_results, f, indent=2)
                    print(f"[REALTIME] Wrote real-time result to: {real_time_file}")
                
                print(f"[SUCCESS] Successfully processed {email}: {file_url}")
                
                # Clean up downloaded file after successful upload
                try:
                    os.remove(pdf_path)
                    print(f"[CLEANUP] Successfully deleted downloaded file: {downloaded_file}")
                except Exception as cleanup_error:
                    print(f"[CLEANUP] Warning: Could not delete downloaded file {downloaded_file}: {cleanup_error}")
                
                results.append({
                    'email': email,
                    'status': 'success',
                    'error': None,
                    'result': str(result),
                    'file_url': file_url,
                    'filename': filename,
                    'pdf_size': len(pdf_content)
                })
                
                return True
                
            except Exception as upload_error:
                print(f"[ERROR] Upload failed: {upload_error}")
                print(f"[ERROR] Upload error type: {type(upload_error)}")
                print(f"[ERROR] Upload error details: {str(upload_error)}")
                results.append({
                    'email': email,
                    'status': 'error',
                    'error': f"Upload failed: {upload_error}",
                    'result': str(result)
                })
                return False
                
        else:
            print(f"[ERROR] No PDF file downloaded for {email}")
            results.append({
                'email': email,
                'status': 'error',
                'error': 'No PDF file downloaded',
                'result': str(result)
            })
            return False
        
    except asyncio.TimeoutError:
            print(f"[ERROR] Timeout for {email}")
            
            # Check if any files were downloaded despite timeout
            downloaded_file = get_latest_pdf(downloads_folder, before_files)
            if downloaded_file:
                print(f"[TIMEOUT] Found downloaded file despite timeout: {downloaded_file}")
                
                # Read the PDF file
                pdf_path = os.path.join(downloads_folder, downloaded_file)
                with open(pdf_path, 'rb') as f:
                    pdf_content = f.read()
                
                if pdf_content and pdf_content.startswith(b'%PDF'):
                    print(f"[TIMEOUT] Valid PDF found, uploading to Supabase")
                    
                    # Create safe filename and upload to Supabase
                    filename = create_safe_filename(email)
                    
                    try:
                        file_url = upload_pdf_to_supabase(pdf_content, filename, user_id)
                        
                        results.append({
                            'email': email,
                            'status': 'success',
                            'error': None,
                            'result': 'Downloaded despite timeout',
                            'file_url': file_url,
                            'filename': filename,
                            'pdf_size': len(pdf_content)
                        })
                        
                        print(f"[TIMEOUT] Successfully uploaded PDF despite timeout: {file_url}")
                        
                        # Clean up downloaded file after successful upload
                        try:
                            os.remove(pdf_path)
                            print(f"[CLEANUP] Successfully deleted downloaded file: {downloaded_file}")
                        except Exception as cleanup_error:
                            print(f"[CLEANUP] Warning: Could not delete downloaded file {downloaded_file}: {cleanup_error}")
                        
                        return True
                        
                    except Exception as upload_error:
                        print(f"[TIMEOUT] Upload failed: {upload_error}")
            
            results.append({
                'email': email,
                'status': 'error',
                'error': 'Timeout - agent took too long',
                'result': None
            })
            return False
    except Exception as e:
        error_msg = f"Error processing {email}: {str(e)}"
        print(f"[ERROR] {error_msg}")
        
        results.append({
            'email': email,
            'status': 'error',
            'error': str(e),
            'result': None
        })
        
        return False
        
    finally:
        # Always clean up browser session
        if browser_session:
            try:
                await browser_session.close()
                print(f"[CLEANUP] Browser session closed for {email}")
            except Exception as e:
                print(f"[CLEANUP] Error closing browser session: {e}")

async def process_single_email_with_retry(email, password, user_id, login_url, billing_url, downloads_folder, max_retries=5):
    """Process a single email with retry mechanism"""
    
    for attempt in range(1, max_retries + 1):
        print(f"\n{'='*60}")
        print(f"[EMAIL] Processing: {email} (Attempt {attempt}/{max_retries})")
        print(f"{'='*60}")
        
        try:
            success = await process_single_email(email, password, user_id, login_url, billing_url, downloads_folder)
            if success:
                print(f"[SUCCESS] Successfully processed {email} on attempt {attempt}")
                # Find the result in the global results list to get the file_url
                for result in results:
                    if result.get('email') == email and result.get('status') == 'success' and result.get('file_url'):
                        # Write success result with retry info and file_url
                        result_data = {
                            'email': email,
                            'status': 'success',
                            'error': None,
                            'file_url': result.get('file_url'),
                            'filename': result.get('filename'),
                            'pdf_size': result.get('pdf_size'),
                            'retry_attempts': attempt,
                            'final_error': None
                        }
                        write_real_time_result(result_data)
                        return True
                
                # Fallback if result not found in global results
                result_data = {
                    'email': email,
                    'status': 'success',
                    'error': None,
                    'retry_attempts': attempt,
                    'final_error': None
                }
                write_real_time_result(result_data)
                return True
            else:
                print(f"[RETRY] Failed to process {email} on attempt {attempt}")
                if attempt < max_retries:
                    print(f"[RETRY] Waiting 10 seconds before retry...")
                    await asyncio.sleep(10)
                else:
                    print(f"[FAILED] All {max_retries} attempts failed for {email}")
                    # Write failure result with retry info
                    result_data = {
                        'email': email,
                        'status': 'error',
                        'error': f'Failed after {max_retries} attempts - check credentials or website availability',
                        'retry_attempts': max_retries,
                        'final_error': f'Failed after {max_retries} attempts - check credentials or website availability'
                    }
                    write_real_time_result(result_data)
                    return False
                    
        except Exception as e:
            print(f"[ERROR] Exception on attempt {attempt} for {email}: {e}")
            if attempt < max_retries:
                print(f"[RETRY] Waiting 10 seconds before retry...")
                await asyncio.sleep(10)
            else:
                print(f"[FAILED] All {max_retries} attempts failed for {email}")
                # Write failure result with retry info
                result_data = {
                    'email': email,
                    'status': 'error',
                    'error': f'Critical error after {max_retries} attempts: {str(e)}',
                    'retry_attempts': max_retries,
                    'final_error': f'Critical error after {max_retries} attempts: {str(e)}'
                }
                write_real_time_result(result_data)
                return False
    
    return False

def write_real_time_result(result_data):
    """Write result to real-time results file"""
    if TEMP_DIR:
        real_time_file = os.path.join(TEMP_DIR, 'real_time_results.json')
        existing_results = []
        if os.path.exists(real_time_file):
            try:
                with open(real_time_file, 'r') as f:
                    existing_results = json.load(f)
            except:
                existing_results = []
        
        # Check if this email already exists in results
        existing_index = None
        for i, result in enumerate(existing_results):
            if result.get('email') == result_data['email']:
                existing_index = i
                break
        
        if existing_index is not None:
            # Update existing result
            existing_results[existing_index] = result_data
        else:
            # Add new result
            existing_results.append(result_data)
        
        with open(real_time_file, 'w') as f:
            json.dump(existing_results, f, indent=2)
        print(f"[REALTIME] Wrote real-time result to: {real_time_file}")

async def main():
    """Main execution function"""
    global TEMP_DIR
    
    print("[MAIN] Starting simplified bill downloader")
    
    # Get environment variables
    csv_path = os.getenv('CSV_PATH')
    login_url = os.getenv('LOGIN_URL')
    billing_url = os.getenv('BILLING_URL')
    user_id = os.getenv('USER_ID')
    session_id = os.getenv('SESSION_ID', 'unknown')
    
    # Create downloads folder in current repository
    downloads_folder = os.path.join(os.getcwd(), 'downloads')
    os.makedirs(downloads_folder, exist_ok=True)
    
    if not all([csv_path, login_url, billing_url, user_id]):
        print("[ERROR] Missing required environment variables")
        sys.exit(1)
    
    print(f"[MAIN] Environment variables:")
    print(f"  CSV_PATH: {csv_path}")
    print(f"  LOGIN_URL: {login_url}")
    print(f"  BILLING_URL: {billing_url}")
    print(f"  USER_ID: {user_id}")
    print(f"  SESSION_ID: {session_id}")
    print(f"  DOWNLOADS_FOLDER: {downloads_folder}")
    
    # Initialize temp directory - use the same path as the backend expects
    # Go up 3 levels: scripts -> backend -> ByteCorp-project3 -> temp
    TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'temp', f'job_{session_id}')
    os.makedirs(TEMP_DIR, exist_ok=True)
    print(f"[MAIN] Using temp directory: {TEMP_DIR}")
    
    # Read credentials
    try:
        print(f"[MAIN] Reading credentials from: {csv_path}")
        creds = pd.read_csv(csv_path, skipinitialspace=True)
        usernames = creds['cred_username']
        passwords = creds['cred_password']
        print(f"[MAIN] Successfully read {len(usernames)} credentials")
    except Exception as e:
        print(f"[ERROR] Error reading credentials: {e}")
        sys.exit(1)
    
    # Process each email
    for i, (email, password) in enumerate(zip(usernames, passwords), 1):
        # Skip empty or invalid entries
        if pd.isna(email) or pd.isna(password) or str(email).strip() == '' or str(password).strip() == '':
            print(f"\n[SKIP] Skipping invalid entry {i}: email='{email}', password='{password}'")
            continue
            
        print(f"\n[PROGRESS] Processing {i}/{len(usernames)}: {email}")
        
        try:
            success = await process_single_email_with_retry(email, password, user_id, login_url, billing_url, downloads_folder)
            if success:
                print(f"[PROGRESS] Successfully processed {email}")
            else:
                print(f"[PROGRESS] Failed to process {email} after all retries")
                # Note: Failed results are already written to real-time results by the retry function
        except Exception as e:
            print(f"[ERROR] Critical error processing {email}: {e}")
            # Write critical error result
            result_data = {
                'email': email,
                'status': 'error',
                'error': f'Critical error: {str(e)}',
                'retry_attempts': 0,
                'final_error': f'Critical error: {str(e)}'
            }
            write_real_time_result(result_data)
    
    # Write final results
    results_summary = {
        'results': results,
        'total_processed': len(results),
        'successful': len([r for r in results if r['status'] == 'success']),
        'failed': len([r for r in results if r['status'] == 'error']),
        'timestamp': str(datetime.now())
    }
    
    # Write results file
    results_file = os.path.join(TEMP_DIR, 'browser_results.json')
    with open(results_file, 'w') as f:
        json.dump(results_summary, f, indent=2)
    
    # Write completion signal
    completion_file = os.path.join(TEMP_DIR, 'browser_completion.json')
    with open(completion_file, 'w') as f:
        json.dump({
            'status': 'completed',
            'message': f'Processing complete. {results_summary["successful"]} successful, {results_summary["failed"]} failed.',
            **results_summary
        }, f, indent=2)
    
    print(f"\n[COMPLETE] PROCESSING COMPLETE!")
    print(f"[SUCCESS] Successful: {results_summary['successful']}")
    print(f"[ERROR] Failed: {results_summary['failed']}")
    
    # Clean up any remaining files in downloads folder
    try:
        remaining_files = os.listdir(downloads_folder)
        if remaining_files:
            print(f"[CLEANUP] Cleaning up {len(remaining_files)} remaining files in downloads folder...")
            for filename in remaining_files:
                file_path = os.path.join(downloads_folder, filename)
                try:
                    os.remove(file_path)
                    print(f"[CLEANUP] Deleted: {filename}")
                except Exception as e:
                    print(f"[CLEANUP] Warning: Could not delete {filename}: {e}")
            print(f"[CLEANUP] Downloads folder cleanup complete")
        else:
            print(f"[CLEANUP] Downloads folder is already clean")
    except Exception as e:
        print(f"[CLEANUP] Error during downloads folder cleanup: {e}")

# Signal handler for graceful shutdown
def signal_handler(signum, frame):
    print("[STOP] Received stop signal. Cleaning up...")
    if TEMP_DIR:
        completion_file = os.path.join(TEMP_DIR, 'browser_completion.json')
        os.makedirs(os.path.dirname(completion_file), exist_ok=True)
        with open(completion_file, 'w') as f:
            json.dump({
                'status': 'interrupted',
                'message': 'Process interrupted by signal',
                'timestamp': str(datetime.now())
            }, f)
    sys.exit(0)

# Only set up signal handlers if we're in the main thread
try:
    import signal
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    print("[INFO] Signal handlers configured for graceful shutdown")
except (ValueError, OSError) as e:
    print(f"[WARN] Could not set up signal handlers (running in background thread): {e}")
    print("[INFO] Continuing without signal handlers")

# Run the main function
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[CRITICAL] Critical error in main execution: {e}")
        sys.exit(1)