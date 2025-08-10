import io
import csv
import subprocess
import os
import signal
import psutil
import json
from supabase_client import download_file_from_supabase, upload_file_to_supabase, upload_pdf_to_bills_bucket
from models.models import ImportSession, ImportResult
from db import db
from datetime import datetime

# Dictionary to store running processes
running_processes = {}

def stop_agent_job(session_id):
    """Stop a running agent job"""
    if session_id in running_processes:
        process = running_processes[session_id]
        try:
            # Get the process group
            parent = psutil.Process(process.pid)
            children = parent.children(recursive=True)
            
            # Terminate children first
            for child in children:
                child.terminate()
            
            # Terminate parent
            parent.terminate()
            
            # Wait for processes to terminate
            gone, alive = psutil.wait_procs(children + [parent], timeout=3)
            
            # Force kill if still alive
            for p in alive:
                p.kill()
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass  # Process already terminated
        
        del running_processes[session_id]
        return True
    return False

def read_real_time_results(temp_dir):
    """Read real-time results file if it exists"""
    real_time_file = os.path.join(temp_dir, 'real_time_results.json')
    print(f"[DEBUG] Looking for real-time results at: {real_time_file}")
    if os.path.exists(real_time_file):
        try:
            with open(real_time_file, 'r') as f:
                real_time_data = json.load(f)
            print(f"[DEBUG] Found real-time results: {real_time_data}")
            return real_time_data
        except Exception as e:
            print(f"[DEBUG] Error reading real-time results: {e}")
            return None
    else:
        print(f"[DEBUG] Real-time results file not found")
    return None

def read_error_file(temp_dir):
    """Read error file if it exists"""
    error_file = os.path.join(temp_dir, 'browser_error.json')
    if os.path.exists(error_file):
        try:
            with open(error_file, 'r') as f:
                error_data = json.load(f)
            return error_data
        except Exception as e:
            return {
                'error': f'Failed to read error file: {str(e)}',
                'type': 'file_read_error'
            }
    return None

def read_results_file(temp_dir):
    """Read results file if it exists"""
    results_file = os.path.join(temp_dir, 'browser_results.json')
    print(f"[DEBUG] Looking for results file at: {results_file}")
    if os.path.exists(results_file):
        try:
            with open(results_file, 'r') as f:
                results_data = json.load(f)
            print(f"[DEBUG] Found results data: {results_data}")
            return results_data
        except Exception as e:
            print(f"[DEBUG] Error reading results file: {e}")
            return None
    else:
        print(f"[DEBUG] Results file not found")
    return None

def read_completion_file(temp_dir):
    """Read completion file if it exists"""
    completion_file = os.path.join(temp_dir, 'browser_completion.json')
    print(f"[DEBUG] Looking for completion file at: {completion_file}")
    if os.path.exists(completion_file):
        try:
            with open(completion_file, 'r') as f:
                completion_data = json.load(f)
            print(f"[DEBUG] Found completion data: {completion_data}")
            return completion_data
        except Exception as e:
            print(f"[DEBUG] Error reading completion file: {e}")
            return None
    else:
        print(f"[DEBUG] Completion file not found")
    return None

def run_agent_for_job(session_id):
    print(f"=== STARTING JOB {session_id} ===")
    session = ImportSession.query.get(session_id)
    if not session:
        print(f"ERROR: Session {session_id} not found")
        return None
    
    # Check if already running
    if session_id in running_processes:
        print(f"ERROR: Job {session_id} is already running")
        return None
    
    print(f"Job details:")
    print(f"  User ID: {session.user_id}")
    print(f"  Login URL: {session.login_url}")
    print(f"  Billing URL: {session.billing_url}")
    print(f"  CSV URL: {session.csv_url}")
    
    # Mark as running
    session.status = 'running'
    db.session.commit()
    print(f"Job status set to 'running'")

    try:
        # Create a unique temporary directory for this job
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp', f'job_{session_id}')
        os.makedirs(temp_dir, exist_ok=True)
        print(f"Created temp directory: {temp_dir}")
        
        # Download CSV from Supabase and save temporarily with a unique name
        print(f"Downloading CSV from Supabase: {session.csv_url}")
        csv_bytes = download_file_from_supabase(session.csv_url)
        temp_csv_path = os.path.join(temp_dir, f'credentials_{session_id}.csv')
        with open(temp_csv_path, 'wb') as f:
            f.write(csv_bytes)
        print(f"CSV downloaded and saved to: {temp_csv_path}")
        print(f"CSV size: {len(csv_bytes)} bytes")

        # Run browser.py in a subprocess with the necessary parameters
        browser_script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'browser.py')
        print(f"Browser script path: {browser_script_path}")
        
        env = os.environ.copy()
        env.update({
            'CSV_PATH': temp_csv_path,
            'LOGIN_URL': session.login_url,
            'BILLING_URL': session.billing_url,
            'USER_ID': str(session.user_id),
            'SESSION_ID': session_id
        })
        print(f"Environment variables set:")
        print(f"  CSV_PATH: {temp_csv_path}")
        print(f"  LOGIN_URL: {session.login_url}")
        print(f"  BILLING_URL: {session.billing_url}")
        print(f"  USER_ID: {session.user_id}")
        print(f"  SESSION_ID: {session_id}")
        
        # Start process with real-time output
        process = subprocess.Popen(['python', browser_script_path],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,  # Redirect stderr to stdout
                                 env=env,
                                 start_new_session=True,
                                 universal_newlines=True,  # Text mode
                                 encoding='utf-8',  # Explicit UTF-8 encoding
                                 errors='replace',  # Replace invalid characters
                                 bufsize=1)  # Line buffered
        
        # Store the process
        running_processes[session_id] = process
        
        print(f"Browser process started with PID: {process.pid}")
        print("=== BROWSER SCRIPT OUTPUT ===")
        
        # Set a timeout for the process (30 minutes)
        try:
            # Read output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(f"[BROWSER] {output.strip()}")
            
            # Get any remaining output
            stdout, stderr = process.communicate()
            if stdout:
                print(f"[BROWSER] {stdout.strip()}")
            if stderr:
                print(f"[BROWSER ERROR] {stderr.strip()}")
                
        except subprocess.TimeoutExpired:
            # Process timed out, kill it
            print("Browser process timed out after 30 minutes")
            process.kill()
            stdout, stderr = process.communicate()
            if stdout:
                print(f"[BROWSER TIMEOUT] {stdout.strip()}")
            if stderr:
                print(f"[BROWSER TIMEOUT ERROR] {stderr.strip()}")
            
            # Create timeout error result
            result = ImportResult(
                session_id=session_id,
                email=None,
                status='error',
                error='Browser automation timed out after 30 minutes',
                file_url=None
            )
            db.session.add(result)
            session.status = 'completed'
            db.session.commit()
            return None

        print("=== PROCESSING RESULTS ===")
        
        # Debug: List all files in temp directory
        print(f"[DEBUG] Files in temp directory {temp_dir}:")
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"[DEBUG]  {file} ({file_size} bytes)")
        else:
            print(f"[DEBUG] Temp directory does not exist: {temp_dir}")
        
        # Check for completion and error files
        completion_data = read_completion_file(temp_dir)
        error_data = read_error_file(temp_dir)
        results_data = read_results_file(temp_dir)
        real_time_results = read_real_time_results(temp_dir)

        print(f"Completion data: {completion_data}")
        print(f"Error data: {error_data}")
        print(f"Results data: {results_data}")
        print(f"Real-time results: {real_time_results}")

        # Process real-time results first (these are already uploaded to Supabase)
        if real_time_results:
            print(f"Processing {len(real_time_results)} real-time results")
            for result_item in real_time_results:
                print(f"Processing result item: {result_item}")
                if result_item.get('file_url'):
                    # Create success result with PDF
                    result = ImportResult(
                        session_id=session_id,
                        email=result_item.get('email'),
                        status='success',
                        error=None,
                        file_url=result_item['file_url']
                    )
                    db.session.add(result)
                    print(f"[OK] Added real-time result with PDF: {result_item['file_url']}")
                else:
                    # Create success result without PDF
                    result = ImportResult(
                        session_id=session_id,
                        email=result_item.get('email'),
                        status='success',
                        error=None,
                        file_url=None
                    )
                    db.session.add(result)
                    print(f"[WARN] Added real-time result without PDF for email: {result_item.get('email')}")
            
            # Commit real-time results immediately
            db.session.commit()
        else:
            print("No real-time results found - checking if any results were already saved to database")
            
            # Check if any results already exist in database for this session
            existing_results = ImportResult.query.filter_by(session_id=session_id).all()
            if existing_results:
                print(f"Found {len(existing_results)} existing results in database")
                for result in existing_results:
                    print(f"  - Email: {result.email}, Status: {result.status}, File: {result.file_url}")
            else:
                print("No existing results found in database either")
        
        # Always process completion data if available
        if completion_data:
            print(f"Browser process completed with status: {completion_data.get('status')}")
            
            if completion_data.get('status') == 'interrupted':
                # Process was interrupted
                result = ImportResult(
                    session_id=session_id,
                    email=None,
                    status='error',
                    error=f"Process interrupted: {completion_data.get('message', 'Unknown interruption')}",
                    file_url=None
                )
                db.session.add(result)
                session.status = 'completed'
                db.session.commit()
                return None
            elif completion_data.get('status') == 'completed_with_error':
                # Process completed with error
                error_msg = completion_data.get('message', 'Unknown error occurred')
                result = ImportResult(
                    session_id=session_id,
                    email=None,
                    status='error',
                    error=error_msg,
                    file_url=None
                )
                db.session.add(result)
                session.status = 'error'
                db.session.commit()
                return None

        if error_data:
            print(f"[ERROR] Processing error data: {error_data}")
            # Handle specific error types
            if error_data.get('type') == 'openai_error':
                # Create error result for OpenAI token issues
                result = ImportResult(
                    session_id=session_id,
                    email=None,
                    status='error',
                    error=error_data['error'],
                    file_url=None
                )
                db.session.add(result)
                session.status = 'completed'
                print(f"[ERROR] OpenAI error processed: {error_data['error']}")
                db.session.commit()
                return None
            
            elif error_data.get('type') in ['env_error', 'csv_error']:
                # Create error result for configuration issues
                result = ImportResult(
                    session_id=session_id,
                    email=None,
                    status='error',
                    error=error_data['error'],
                    file_url=None
                )
                db.session.add(result)
                session.status = 'completed'
                db.session.commit()
                return None
            
            elif error_data.get('type') in ['processing_error', 'critical_error']:
                # Create error result for specific email
                email = error_data.get('email', 'Unknown')
                result = ImportResult(
                    session_id=session_id,
                    email=email,
                    status='error',
                    error=error_data['error'],
                    file_url=None
                )
                db.session.add(result)
                
                # If we have results data, process successful ones
                if results_data and 'results' in results_data:
                    for result_item in results_data['results']:
                        if result_item['status'] == 'success':
                            # Check if the result already has a file_url from browser script
                            file_url = result_item.get('file_url')
                            
                            if file_url:
                                # PDF was already uploaded by browser script during automation
                                success_result = ImportResult(
                                    session_id=session_id,
                                    email=result_item['email'],
                                    status='success',
                                    error=None,
                                    file_url=file_url
                                )
                                db.session.add(success_result)
                                print(f"Added success result with PDF: {file_url}")
                            else:
                                # No PDF found, create success result without file
                                success_result = ImportResult(
                                    session_id=session_id,
                                    email=result_item['email'],
                                    status='success',
                                    error=None,
                                    file_url=None
                                )
                                db.session.add(success_result)
                                print(f"Added success result without PDF for email: {result_item['email']}")
                
                session.status = 'completed'
                db.session.commit()
                return None

        # Process results if no error files found
        if process.returncode == 0:
            # Check if we have results data
            if results_data and 'results' in results_data:
                for result_item in results_data['results']:
                    if result_item['status'] == 'success':
                        # Check if the result already has a file_url from browser script
                        file_url = result_item.get('file_url')
                        
                        if file_url:
                            # PDF was already uploaded by browser script during automation
                            result = ImportResult(
                                session_id=session_id,
                                email=result_item['email'],
                                status='success',
                                error=None,
                                file_url=file_url
                            )
                            db.session.add(result)
                            print(f"Added result with PDF: {file_url}")
                        else:
                            # No PDF found, create success result without file
                            result = ImportResult(
                                session_id=session_id,
                                email=result_item['email'],
                                status='success',
                                error=None,
                                file_url=None
                            )
                            db.session.add(result)
                            print(f"Added result without PDF for email: {result_item['email']}")
                    elif result_item['status'] == 'error':
                        # Create error result
                        result = ImportResult(
                            session_id=session_id,
                            email=result_item['email'],
                            status='error',
                            error=result_item['error'],
                            file_url=None
                        )
                        db.session.add(result)
                        print(f"Added error result for email: {result_item['email']}")
            else:
                # No results found - this means no PDFs were captured from the browser
                print("No PDF results found in browser output - no bills were captured")
                # Don't create any results since no bills were found
        else:
            # Create error result for subprocess failure
            try:
                if stderr:
                    stderr_content = stderr.decode('utf-8', errors='replace')
                else:
                    stderr_content = "No error output available"
            except Exception as decode_error:
                stderr_content = f"Error decoding stderr: {decode_error}"
            error_msg = f'Browser automation failed: {stderr_content}'
            result = ImportResult(
                session_id=session_id,
                email=None,
                status='error',
                error=error_msg,
                file_url=None
            )
            db.session.add(result)
        
        # Commit all results to database
        db.session.commit()
        print(f"[COMMIT] Committed all results to database")

    except Exception as e:
        # Handle any exceptions
        session.status = 'error'
        result = ImportResult(
            session_id=session_id,
            email=None,
            status='error',
            error=str(e),
            file_url=None
        )
        db.session.add(result)
    finally:
        # Clean up temporary directory and its contents
        if os.path.exists(temp_dir):
            try:
                for file in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, file))
                os.rmdir(temp_dir)
                print(f"[CLEANUP] Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                print(f"[WARN] Warning: Could not clean up temp directory {temp_dir}: {e}")
        
        # Only mark as completed if not already marked as error
        if session.status != 'error':
            session.status = 'completed'
            print(f"[OK] Job {session_id} completed successfully")
        else:
            print(f"[ERROR] Job {session_id} completed with errors")
        db.session.commit()

        print(f"=== JOB {session_id} FINISHED ===")
    return None

def cleanup_orphaned_processes():
    """Clean up any orphaned browser processes on server startup"""
    print("Cleaning up orphaned browser processes...")
    
    # Kill any browser processes that might be leftover
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            # Look for browser processes that are part of our automation
            if cmdline and any('browser_use' in arg or 'browser.py' in arg for arg in cmdline):
                print(f"Killing orphaned browser process: {proc.info['pid']}")
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    # Clean up any existing temp directories
    temp_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')
    if os.path.exists(temp_root):
        print("Cleaning up existing temp directories...")
        try:
            for item in os.listdir(temp_root):
                item_path = os.path.join(temp_root, item)
                if os.path.isdir(item_path):
                    # Remove all files in the directory
                    for file in os.listdir(item_path):
                        os.remove(os.path.join(item_path, file))
                    # Remove the directory
                    os.rmdir(item_path)
                    print(f"[OK] Cleaned up temp directory: {item}")
            # Remove the temp root directory if it's empty
            if not os.listdir(temp_root):
                os.rmdir(temp_root)
                print("[OK] Removed empty temp root directory")
        except Exception as e:
            print(f"Warning: Could not clean up temp directories: {e}")