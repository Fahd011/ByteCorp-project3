import io
import csv
import subprocess
import os
import signal
import psutil
import json
from backend.supabase_client import download_file_from_supabase, upload_file_to_supabase
from backend.models.models import ImportSession, ImportResult
from backend.db import db
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
    if os.path.exists(results_file):
        try:
            with open(results_file, 'r') as f:
                results_data = json.load(f)
            return results_data
        except Exception as e:
            return None
    return None

def read_completion_file(temp_dir):
    """Read completion file if it exists"""
    completion_file = os.path.join(temp_dir, 'browser_completion.json')
    if os.path.exists(completion_file):
        try:
            with open(completion_file, 'r') as f:
                completion_data = json.load(f)
            return completion_data
        except Exception as e:
            return None
    return None

def run_agent_for_job(session_id):
    session = ImportSession.query.get(session_id)
    if not session:
        return None
    
    # Check if already running
    if session_id in running_processes:
        return None
    
    # Mark as running
    session.status = 'running'
    db.session.commit()

    try:
        # Create a unique temporary directory for this job
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp', f'job_{session_id}')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download CSV from Supabase and save temporarily with a unique name
        csv_bytes = download_file_from_supabase(session.csv_url)
        temp_csv_path = os.path.join(temp_dir, f'credentials_{session_id}.csv')
        with open(temp_csv_path, 'wb') as f:
            f.write(csv_bytes)

        # Run browser.py in a subprocess with the necessary parameters
        browser_script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'browser.py')
        env = os.environ.copy()
        env.update({
            'CSV_PATH': temp_csv_path,
            'LOGIN_URL': session.login_url,
            'BILLING_URL': session.billing_url
        })
        
        # Start process in its own process group
        process = subprocess.Popen(['python', browser_script_path],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 env=env,
                                 start_new_session=True)
        
        # Store the process
        running_processes[session_id] = process
        
        # Set a timeout for the process (30 minutes)
        try:
            stdout, stderr = process.communicate(timeout=1800)  # 30 minutes timeout
        except subprocess.TimeoutExpired:
            # Process timed out, kill it
            process.kill()
            stdout, stderr = process.communicate()
            
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

        # Check for completion and error files
        completion_data = read_completion_file(temp_dir)
        error_data = read_error_file(temp_dir)
        results_data = read_results_file(temp_dir)

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
                session.status = 'completed'
                db.session.commit()
                return None

        if error_data:
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
                            # For successful results, check for downloaded PDFs
                            downloads_path = os.path.expanduser('~/Downloads')
                            for filename in os.listdir(downloads_path):
                                if filename.endswith('.pdf'):
                                    with open(os.path.join(downloads_path, filename), 'rb') as f:
                                        pdf_bytes = f.read()
                                    file_url = upload_file_to_supabase(pdf_bytes, filename)
                                    
                                    # Create success result
                                    success_result = ImportResult(
                                        session_id=session_id,
                                        email=result_item['email'],
                                        status='success',
                                        error=None,
                                        file_url=file_url
                                    )
                                    db.session.add(success_result)
                                    
                                    # Clean up downloaded PDF
                                    os.remove(os.path.join(downloads_path, filename))
                
                session.status = 'completed'
                db.session.commit()
                return None

        # Process results if no error files found
        if process.returncode == 0:
            # Check if we have results data
            if results_data and 'results' in results_data:
                for result_item in results_data['results']:
                    if result_item['status'] == 'success':
                        # For successful results, check for downloaded PDFs
                        downloads_path = os.path.expanduser('~/Downloads')
                        for filename in os.listdir(downloads_path):
                            if filename.endswith('.pdf'):
                                with open(os.path.join(downloads_path, filename), 'rb') as f:
                                    pdf_bytes = f.read()
                                file_url = upload_file_to_supabase(pdf_bytes, filename)
                                
                                # Create success result
                                result = ImportResult(
                                    session_id=session_id,
                                    email=result_item['email'],
                                    status='success',
                                    error=None,
                                    file_url=file_url
                                )
                                db.session.add(result)
                                
                                # Clean up downloaded PDF
                                os.remove(os.path.join(downloads_path, filename))
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
            else:
                # Fallback to original logic for downloaded PDFs
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
            # Create error result for subprocess failure
            error_msg = f'Browser automation failed: {stderr.decode()}'
            result = ImportResult(
                session_id=session_id,
                email=None,
                status='error',
                error=error_msg,
                file_url=None
            )
            db.session.add(result)

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
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))
            os.rmdir(temp_dir)
        
        # Mark job as completed
        session.status = 'completed'
        db.session.commit()

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
                    print(f"✓ Cleaned up temp directory: {item}")
            # Remove the temp root directory if it's empty
            if not os.listdir(temp_root):
                os.rmdir(temp_root)
                print("✓ Removed empty temp root directory")
        except Exception as e:
            print(f"Warning: Could not clean up temp directories: {e}")