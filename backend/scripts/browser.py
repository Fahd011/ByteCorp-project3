from browser_use.llm import ChatOpenAI
from browser_use import Agent
from dotenv import load_dotenv
from browser_use.browser import BrowserSession, BrowserProfile
import pandas as pd
import asyncio
import os
import uuid
from datetime import datetime
from supabase import create_client, Client
import sys
import json

load_dotenv()

print("=== BROWSER SCRIPT INITIALIZATION STARTED ===")

bill_count = 0

# Supabase setup
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Initialize LLM
llm = ChatOpenAI(model="gpt-4.1-mini")

# Get configuration from environment variables
csv_path = os.getenv('CSV_PATH') 
login_url = os.getenv('LOGIN_URL')
billing_url = os.getenv('BILLING_URL')
user_id = os.getenv('USER_ID')
session_id = os.getenv('SESSION_ID')

# Validate required environment variables
if not all([csv_path, login_url, billing_url]):
    error_msg = "Error: Missing required environment variables. Need CSV_PATH, LOGIN_URL, and BILLING_URL"
    print(error_msg, file=sys.stderr)
    sys.exit(1)

# Initialize temp directory for results
temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp', f'job_{session_id or "unknown"}')
os.makedirs(temp_dir, exist_ok=True)
print(f"Using temp directory: {temp_dir}")

print(f"Configuration loaded:")
print(f"  CSV_PATH: {csv_path}")
print(f"  LOGIN_URL: {login_url}")
print(f"  BILLING_URL: {billing_url}")
print(f"  USER_ID: {user_id}")
print(f"  SESSION_ID: {session_id}")
print(f"  TEMP_DIR: {temp_dir}")

def write_real_time_result(result_data):
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
        print(f"Real-time result written: {result_data}")
    except Exception as e:
        print(f"Error writing real-time results: {e}", file=sys.stderr)

def write_completion_signal(status, message, total_processed=0, successful=0, failed=0):
    """Write completion signal for agent runner"""
    completion_file = os.path.join(temp_dir, 'browser_completion.json')
    try:
        with open(completion_file, 'w') as f:
            json.dump({
                'status': status,
                'message': message,
                'total_processed': total_processed,
                'successful': successful,
                'failed': failed,
                'timestamp': str(datetime.now())
            }, f)
        print(f"Completion signal written: {status}")
    except Exception as e:
        print(f"Error writing completion signal: {e}", file=sys.stderr)

def write_error_signal(error_msg, error_type, email=None):
    """Write error signal for agent runner"""
    error_file = os.path.join(temp_dir, 'browser_error.json')
    try:
        with open(error_file, 'w') as f:
            json.dump({
                'error': error_msg,
                'type': error_type,
                'email': email,
                'timestamp': str(datetime.now())
            }, f)
        print(f"Error signal written: {error_type}")
    except Exception as e:
        print(f"Error writing error signal: {e}", file=sys.stderr)

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
    write_error_signal(error_msg, 'csv_error')
    write_completion_signal('completed_with_error', error_msg)
    sys.exit(1)

# Create downloads folder in current repository
downloads_folder = os.path.join(os.getcwd(), 'downloads')
os.makedirs(downloads_folder, exist_ok=True)
print(f"Downloads folder: {downloads_folder}")

async def process_email(email, password, bill_count):
    """Process a single email/password combination"""
    try:
        print(f"Processing email: {email}")
        
        # Unique user data dir to isolate sessions
        unique_profile_path = f'/tmp/browser_profiles/{uuid.uuid4()}'
        os.makedirs(unique_profile_path, exist_ok=True)
        
        browser_session = BrowserSession(
            browser_profile=BrowserProfile(
                downloads_path=downloads_folder,
                user_data_dir=unique_profile_path,
            )
        )

        agent = Agent(
            task = f"""
1. Go to {login_url}.
2. Log in using:
   - Email: {email}
   - Password: {password}
3. After successful login, go to "Billing and Payment Activity".
   - If unsure, navigate directly to {billing_url}.
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

        # Run the agent
        print(f"Starting browser automation for {email}...")
        result = await agent.run()
        
        # Wait for any downloads to complete, then rename the file
        print(f"Waiting for download to complete...")
        await asyncio.sleep(3)  # Wait for download to finish
        
        # Find the most recent PDF file and rename it
        pdf_files = [f for f in os.listdir(downloads_folder) if f.endswith('.pdf')]
        if pdf_files:
            # Get the most recently modified PDF file
            latest_pdf = max(pdf_files, key=lambda f: os.path.getmtime(os.path.join(downloads_folder, f)))
            old_path = os.path.join(downloads_folder, latest_pdf)
            
            # Create new filename with user_id and session_id for tracking
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            safe_email = email.replace('@', '_at_').replace('.', '_')
            new_filename = f"{safe_email}-{timestamp}.pdf"
            new_path = os.path.join(downloads_folder, new_filename)
            
            try:
                os.rename(old_path, new_path)
                print(f"SUCCESS: Renamed file to {new_filename}")
                
                # Upload to Supabase
                try:
                    print(f"Attempting to upload {new_filename} to Supabase...")
                    print(f"File path: {new_path}")
                    print(f"File exists: {os.path.exists(new_path)}")
                    print(f"File size: {os.path.getsize(new_path)} bytes")
                    
                    with open(new_path, "rb") as f:
                        file_content = f.read()
                        print(f"File content read successfully, size: {len(file_content)} bytes")
                        
                        # Upload to Supabase
                        upload_result = supabase.storage.from_("bills").upload(new_filename, file_content)
                        print(f"SUCCESS: Uploaded {new_filename} to Supabase bucket 'bills'")
                        print(f"Upload result: {upload_result}")
                        
                        # Clean up local file after successful upload
                        
                except Exception as e:
                    print(f"ERROR: Failed to upload to Supabase: {e}")
                    print(f"Error type: {type(e)}")
                    import traceback
                    traceback.print_exc()

            except Exception as e:
                print(f"ERROR: Failed to rename file: {e}")
            
            # Always try to delete the file after processing
            try:
                if os.path.exists(new_path):
                    os.remove(new_path)
                    print(f"Local file {new_filename} removed after processing")
            except Exception as delete_error:
                print(f"WARNING: Could not delete local file {new_filename}: {delete_error}")
                
            # Write real-time result for successful processing
            result_data = {
                'email': email,
                'status': 'success',
                'filename': new_filename,
                'uploaded_to_supabase': True,
                'timestamp': str(datetime.now())
            }
            write_real_time_result(result_data)
            
        else:
            print(f"WARNING: No PDF files found in downloads folder for {email}")
            # Write real-time result for no PDF found
            result_data = {
                'email': email,
                'status': 'no_pdf_found',
                'filename': None,
                'uploaded_to_supabase': False,
                'timestamp': str(datetime.now())
            }
            write_real_time_result(result_data)
        
        # Close browser session
        try:
            await browser_session.close()
            print(f"Browser session closed for {email}")
        except Exception as e:
            print(f"Error closing browser session: {e}")
        
        bill_count += 1
        return True
        
    except Exception as e:
        error_msg = f"Error processing {email}: {str(e)}"
        print(error_msg, file=sys.stderr)
        
        # Write real-time result for error
        result_data = {
            'email': email,
            'status': 'error',
            'error': str(e),
            'filename': None,
            'uploaded_to_supabase': False,
            'timestamp': str(datetime.now())
        }
        write_real_time_result(result_data)
        
        return False

async def main():
    """Main function to process all emails"""
    global bill_count
    
    print("=== BROWSER SCRIPT STARTED ===")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Total credentials to process: {len(usernames)}")
    
    results = []
    
    for email, password in zip(usernames, passwords):
        try:
            success = await process_email(email, password, bill_count)
            results.append({
                'email': email,
                'status': 'success' if success else 'error',
                'timestamp': str(datetime.now())
            })
        except Exception as e:
            print(f"Critical error processing {email}: {e}", file=sys.stderr)
            results.append({
                'email': email,
                'status': 'error',
                'error': str(e),
                'timestamp': str(datetime.now())
            })
    
    # Print summary
    successful = len([r for r in results if r['status'] == 'success'])
    failed = len([r for r in results if r['status'] == 'error'])
    
    print(f"\n=== PROCESSING COMPLETE ===")
    print(f"Total processed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    # Write final results file
    results_file = os.path.join(temp_dir, 'browser_results.json')
    try:
        with open(results_file, 'w') as f:
            json.dump({
                'results': results,
                'total_processed': len(results),
                'successful': successful,
                'failed': failed,
                'timestamp': str(datetime.now())
            }, f)
        print(f"Final results written to: {results_file}")
    except Exception as e:
        print(f"Error writing final results: {e}", file=sys.stderr)
    
    # Write completion signal
    completion_status = 'completed_with_error' if failed > 0 else 'completed'
    completion_message = f'Processing complete. Processed {len(results)} emails.'
    write_completion_signal(completion_status, completion_message, len(results), successful, failed)
    
    return results

# Run the main async function
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        error_msg = f"Critical error in main execution: {str(e)}"
        print(error_msg, file=sys.stderr)
        write_error_signal(error_msg, 'critical_error')
        write_completion_signal('completed_with_error', error_msg)
        sys.exit(1)
