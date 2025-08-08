import io
import csv
import subprocess
import os
import signal
import psutil
import threading
import time
import json
from backend.supabase_client import download_file_from_supabase, upload_file_to_supabase
from backend.models.models import ImportSession, ImportResult
from backend.db import db
from datetime import datetime
from flask import current_app
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test environment variables
print(f"=== AGENT_RUNNER ENVIRONMENT TEST ===")
print(f"OPENAI_API_KEY available: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
print(f"OPENAI_API_KEY length: {len(os.getenv('OPENAI_API_KEY', ''))}")
print(f"SUPABASE_URL available: {'Yes' if os.getenv('SUPABASE_URL') else 'No'}")
print(f"SUPABASE_KEY available: {'Yes' if os.getenv('SUPABASE_KEY') else 'No'}")
print(f"=== END ENVIRONMENT TEST ===")

# Dictionary to store running processes and their metadata
running_processes = {}

def stop_agent_job(session_id):
    """Stop a running agent job"""
    if session_id in running_processes:
        process_info = running_processes[session_id]
        main_process = process_info.get('process')
        browser_processes = process_info.get('browser_processes', [])
        
        try:
            # Terminate the main Python process
            if main_process:
                try:
                    main_process.terminate()
                    main_process.wait(timeout=5)
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    if main_process.is_running():
                        main_process.kill()
                except Exception as e:
                    print(f"Error terminating main process: {e}")
            
            # Terminate all browser processes
            for browser_pid in browser_processes:
                try:
                    browser_proc = psutil.Process(browser_pid)
                    # Get all child processes
                    children = browser_proc.children(recursive=True)
                    
                    # Terminate children first
                    for child in children:
                        try:
                            child.terminate()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    # Terminate parent browser process
                    try:
                        browser_proc.terminate()
                        browser_proc.wait(timeout=3)
                    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                        if browser_proc.is_running():
                            browser_proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass  # Process already terminated
                except Exception as e:
                    print(f"Error terminating browser process {browser_pid}: {e}")
            
            # Force kill any remaining browser processes by name
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] in ['chrome', 'chromium', 'firefox', 'geckodriver', 'chromedriver']:
                        # Check if this is our browser process by looking at command line
                        cmdline = proc.info.get('cmdline', [])
                        if any('browser_use' in arg or 'browser.py' in arg for arg in cmdline):
                            proc.terminate()
                            proc.wait(timeout=2)
                            if proc.is_running():
                                proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                except Exception as e:
                    print(f"Error killing browser process: {e}")
                    
        except Exception as e:
            print(f"Error in stop_agent_job: {e}")
        finally:
            # Clean up the process reference
            del running_processes[session_id]
        
        return True
    return False

def find_browser_processes():
    """Find browser processes related to our automation"""
    browser_pids = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            # Look for browser processes that are part of our automation
            if any('browser_use' in arg or 'browser.py' in arg for arg in cmdline):
                browser_pids.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return browser_pids

def run_agent_worker(session_id, app):
    """Worker function that runs the agent in a separate thread"""
    # Create application context for this thread
    with app.app_context():
        session = ImportSession.query.get(session_id)
        if not session:
            return
        
        temp_dir = None
        main_process = None
        
        try:
            # Download CSV from Supabase
            print(f"=== DOWNLOADING CSV FROM SUPABASE ===")
            print(f"CSV URL: {session.csv_url}")
            csv_bytes = download_file_from_supabase(session.csv_url)
            print(f"✓ Downloaded {len(csv_bytes)} bytes from Supabase")
            
            # Verify CSV content
            try:
                csv_content = csv_bytes.decode('utf-8')
                lines = csv_content.split('\n')
                print(f"✓ CSV has {len(lines)} lines")
                print(f"✓ First line (headers): {lines[0] if lines else 'Empty'}")
                print(f"✓ Second line (sample data): {lines[1] if len(lines) > 1 else 'No data'}")
            except Exception as e:
                print(f"❌ Error reading CSV content: {e}")
            
            # Alternative: Pass CSV content directly as environment variable (for small files)
            # This avoids local file creation but has size limitations
            csv_content_base64 = None
            temp_csv_path = None
            
            if len(csv_bytes) < 10000:  # Only for files under 10KB
                import base64
                csv_content_base64 = base64.b64encode(csv_bytes).decode('utf-8')
                print(f"✓ CSV content encoded as base64 ({len(csv_content_base64)} chars)")
                print(f"✓ No temp folder needed - using environment variable")
            else:
                print(f"⚠ CSV too large for environment variable ({len(csv_bytes)} bytes), using local file")
                # Create a unique temporary directory for this job only if needed
                temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp', f'job_{session_id}')
                os.makedirs(temp_dir, exist_ok=True)
                temp_csv_path = os.path.join(temp_dir, f'credentials_{session_id}.csv')
                with open(temp_csv_path, 'wb') as f:
                    f.write(csv_bytes)
                print(f"✓ Saved CSV to: {temp_csv_path}")
                
                # Verify the file exists and is readable
                if os.path.exists(temp_csv_path):
                    print(f"✓ CSV file exists and is readable")
                    file_size = os.path.getsize(temp_csv_path)
                    print(f"✓ CSV file size: {file_size} bytes")
                else:
                    print(f"❌ CSV file does not exist: {temp_csv_path}")
                    return

            # Run browser.py in a subprocess with the necessary parameters
            browser_script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'browser.py')
            env = os.environ.copy()
            env.update({
                'LOGIN_URL': session.login_url,
                'BILLING_URL': session.billing_url,
                'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', '')  # Add OpenAI API key
            })
            
            # Debug: Show environment variables being passed
            print(f"=== ENVIRONMENT VARIABLES ===")
            print(f"OPENAI_API_KEY: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not set'}")
            print(f"OPENAI_API_KEY length: {len(os.getenv('OPENAI_API_KEY', ''))}")
            print(f"LOGIN_URL: {session.login_url}")
            print(f"BILLING_URL: {session.billing_url}")
            print(f"Working directory: {os.getcwd()}")
            print(f"Browser script path: {browser_script_path}")
            print(f"Browser script exists: {os.path.exists(browser_script_path)}")
            
            # If CSV is small enough, pass content directly as environment variable
            if csv_content_base64:
                env['CSV_CONTENT_BASE64'] = csv_content_base64
                print(f"✓ Passing CSV content as environment variable")
            else:
                env['CSV_FILE'] = temp_csv_path
                print(f"✓ Using local CSV file: {temp_csv_path}")
                print(f"CSV file exists: {os.path.exists(temp_csv_path)}")
            
            # Start process
            print(f"=== STARTING BROWSER.PY AGENT ===")
            print(f"Session ID: {session_id}")
            print(f"Browser script path: {browser_script_path}")
            print(f"CSV file: {temp_csv_path}")
            print(f"Login URL: {session.login_url}")
            print(f"Billing URL: {session.billing_url}")
            print(f"Environment variables: {env}")
            
            print(f"About to start subprocess...")
            try:
                main_process = subprocess.Popen(['python', browser_script_path],
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE,
                                              env=env,
                                              text=True,
                                              bufsize=1,
                                              universal_newlines=True)
                print(f"✓ Subprocess created successfully")
            except Exception as e:
                print(f"❌ Failed to create subprocess: {e}")
                return
            
            print(f"Started browser process for session {session_id}")
            print(f"Process ID: {main_process.pid}")
            print(f"Browser script path: {browser_script_path}")
            print(f"Environment variables: {env}")
            print(f"=== BROWSER.PY AGENT STARTED SUCCESSFULLY ===")
            
            # Immediately check if process is running
            print(f"Checking if process is running immediately...")
            if main_process.poll() is None:
                print(f"✓ Process is running immediately (PID: {main_process.pid})")
            else:
                print(f"❌ Process failed immediately (return code: {main_process.poll()})")
                try:
                    stderr_output = main_process.stderr.read()
                    if stderr_output:
                        print(f"❌ Immediate process error: {stderr_output}")
                except:
                    pass
                return
            
            # Check if process is actually running
            if main_process.poll() is None:
                print(f"✓ Process is running (PID: {main_process.pid})")
            else:
                print(f"❌ Process failed to start (return code: {main_process.poll()})")
                # Get any error output from the failed process
                try:
                    stderr_output = main_process.stderr.read()
                    if stderr_output:
                        print(f"❌ Process error output: {stderr_output}")
                except:
                    pass
                return
            
            # Update the process info with the main process
            if session_id in running_processes:
                running_processes[session_id]['process'] = main_process
            
            # Wait a moment for browser processes to start
            time.sleep(2)
            
            # Check if process is still running after 2 seconds
            if main_process.poll() is not None:
                print(f"❌ Process died after 2 seconds (return code: {main_process.poll()})")
                try:
                    stderr_output = main_process.stderr.read()
                    if stderr_output:
                        print(f"❌ Process error output: {stderr_output}")
                except:
                    pass
                return
            
            print(f"✓ Process still running after 2 seconds (PID: {main_process.pid})")
            
            # Find and track browser processes
            browser_pids = find_browser_processes()
            print(f"Found browser processes: {browser_pids}")
            if session_id in running_processes:
                running_processes[session_id]['browser_processes'] = browser_pids
            
            # Wait for process to complete with real-time output
            print(f"Waiting for process to complete...")
            try:
                # Read output in real-time using a simpler approach
                start_time = time.time()  # Initialize start_time
                
                while True:
                    # Check if process is still running
                    if main_process.poll() is not None:
                        break
                    
                    # Read from stdout (blocking read with timeout)
                    try:
                        stdout_line = main_process.stdout.readline()
                        if stdout_line:
                            print(f"[BROWSER.PY STDOUT] {stdout_line.strip()}")
                    except:
                        pass
                    
                    # Read from stderr (blocking read with timeout)
                    try:
                        stderr_line = main_process.stderr.readline()
                        if stderr_line:
                            print(f"[BROWSER.PY STDERR] {stderr_line.strip()}")
                    except:
                        pass
                    
                    # Small delay to avoid busy waiting
                    time.sleep(0.1)
                    
                    # Add timeout check (5 minutes)
                    if time.time() - start_time > 300:
                        print(f"Process timed out after 5 minutes for session {session_id}")
                        main_process.kill()
                        break
                
                # Get the return code
                return_code = main_process.poll()
                print(f"Process completed for session {session_id}")
                print(f"Return code: {return_code}")
                
                # Check if process failed
                if return_code != 0:
                    print(f"Process failed with return code: {return_code}")
                else:
                    print(f"Process completed successfully")
            except subprocess.TimeoutExpired:
                print(f"Process timed out after 60 seconds for session {session_id}")
                main_process.kill()
                print(f"Killed timed out process")
                # Create error result for timeout
                result = ImportResult(
                    session_id=session_id,
                    email=None,
                    status='error',
                    error='Process timed out after 60 seconds',
                    file_url=None
                )
                db.session.add(result)

            # Process results
            if main_process.returncode == 0:
                # For each downloaded PDF in the Downloads directory, upload to Supabase
                downloads_path = os.path.expanduser('~/Downloads')
                for filename in os.listdir(downloads_path):
                    if filename.endswith('.pdf'):
                        with open(os.path.join(downloads_path, filename), 'rb') as f:
                            pdf_bytes = f.read()
                        file_url = upload_file_to_supabase(pdf_bytes, filename)
                        
                        # Create success result
                        result = ImportResult(
                            session_id=session_id,
                            email=filename.split('-')[0].replace('_at_', '@'),  # Extract email from filename
                            status='success',
                            error=None,
                            file_url=file_url
                        )
                        db.session.add(result)
                        
                        # Clean up downloaded PDF
                        os.remove(os.path.join(downloads_path, filename))
            else:
                # Create error result
                result = ImportResult(
                    session_id=session_id,
                    email=None,
                    status='error',
                    error=f'Browser automation failed: {stderr.decode()}',
                    file_url=None
                )
                db.session.add(result)

        except Exception as e:
            # Handle any exceptions
            session = ImportSession.query.get(session_id)
            if session:
                session.status = 'error'
                result = ImportResult(
                    session_id=session_id,
                    email=None,
                    status='error',
                    error=str(e),
                    file_url=None
                )
                db.session.add(result)
                db.session.commit()
        finally:
            # Clean up temporary directory and its contents
            if temp_dir and os.path.exists(temp_dir):
                try:
                    for file in os.listdir(temp_dir):
                        os.remove(os.path.join(temp_dir, file))
                    os.rmdir(temp_dir)
                except:
                    pass
            
            # Mark job as completed and clean up process reference
            session = ImportSession.query.get(session_id)
            if session:
                session.status = 'completed'
                db.session.commit()
            
            # Remove from running processes
            if session_id in running_processes:
                del running_processes[session_id]

def cleanup_temp_folders():
    """Manually clean up all temp folders"""
    temp_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp')
    if os.path.exists(temp_root):
        print("Cleaning up all temp directories...")
        try:
            for item in os.listdir(temp_root):
                item_path = os.path.join(temp_root, item)
                if os.path.isdir(item_path):
                    # Remove all files in the directory
                    for file in os.listdir(item_path):
                        os.remove(os.path.join(item_path, file))
                    # Remove the directory
                    os.rmdir(item_path)
                    print(f"✓ Cleaned up temp directory: {item}")
            # Remove the temp root directory if it's empty
            if not os.listdir(temp_root):
                os.rmdir(temp_root)
                print("✓ Removed empty temp root directory")
        except Exception as e:
            print(f"Warning: Could not clean up temp directories: {e}")
    else:
        print("No temp directory found to clean up")

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
                    print(f"✓ Cleaned up temp directory: {item}")
            # Remove the temp root directory if it's empty
            if not os.listdir(temp_root):
                os.rmdir(temp_root)
                print("✓ Removed empty temp root directory")
        except Exception as e:
            print(f"Warning: Could not clean up temp directories: {e}")

def run_agent_for_job(session_id, app=None):
    """Start the agent job in a separate thread"""
    session = ImportSession.query.get(session_id)
    if not session:
        return None
    
    # Check if already running
    if session_id in running_processes:
        return None
    
    # Mark as running
    session.status = 'running'
    db.session.commit()

    # Initialize process tracking
    running_processes[session_id] = {
        'process': None,
        'browser_processes': [],
        'start_time': time.time()
    }

    # Start the agent in a separate thread
    thread = threading.Thread(target=run_agent_worker, args=(session_id, app))
    thread.daemon = True  # Thread will be terminated when main process exits
    thread.start()
    
    return None
