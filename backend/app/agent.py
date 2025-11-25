import os
import asyncio
import requests
import calendar
import json
import time
import tempfile
from pathlib import Path
import pandas as pd

from datetime import datetime
from typing import Dict
# Import Azure storage service
from azure_storage_service import azure_storage_service

from config import config
from app.models import BillingResult, UserBillingCredential
from app.db import get_db_context
from app.prompts.agent_prompts import get_provider_prompt
from app.extraction.extractor_router import extract_bill_by_provider
from app.audit_logger import AuditLogger
from scripts.graphapi import GraphAPIEmailClient


# ---------------------------------------------------------------------------
# CONFIGURATION -------------------------------------------------------------
# ---------------------------------------------------------------------------
DOWNLOAD_DIR = os.path.expanduser("~/duke_bills")  # ~/duke_bills on any OS
API_KEY = config.BROWSER_USE_API_KEY
BASE_URL = 'https://api.browser-use.com/api/v2'

# ---------------------------------------------------------------------------
# BROWSER USE CLOUD API V2 FUNCTIONS ----------------------------------------
# ---------------------------------------------------------------------------
def create_persistent_session(start_url: str, proxy_country_code: str = None, max_retries: int = 3):
    """Create a new persistent browser session (v2 API) with retry logic"""
    session_url = f"{BASE_URL}/sessions"
    headers = {
        "X-Browser-Use-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {"startUrl": start_url}
    if proxy_country_code:
        payload["proxyCountryCode"] = proxy_country_code
        print(f"[INFO] Creating session with {proxy_country_code} proxy")
    
    # Retry logic with exponential backoff
    for attempt in range(max_retries):
        try:
            print(f"[INFO] Attempting to create session (attempt {attempt + 1}/{max_retries})...")
            # Add timeout: 60 seconds for connection, 120 seconds for read
            response = requests.post(
                session_url, 
                headers=headers, 
                json=payload,
                timeout=(60, 120)  # (connect timeout, read timeout)
            )
            response.raise_for_status()
            session_data = response.json()
            session_id = session_data.get("id")
            live_url = session_data.get("liveUrl")
            
            if session_id:
                print(f"[INFO] Session created (ID: {session_id})")
                if live_url:
                    print(f"[INFO] Live view: {live_url}")
                return session_id, live_url
            else:
                print("[ERROR] Failed to create session - no session ID in response")
                return None, None
                
        except requests.exceptions.Timeout:
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            if attempt < max_retries - 1:
                print(f"[WARNING] Request timed out. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print("[ERROR] Request timed out after all retries")
                return None, None
        except requests.exceptions.HTTPError as http_err:
            # Don't retry on 4xx errors (client errors)
            if http_err.response.status_code < 500:
                print(f"[ERROR] HTTP error creating session: {http_err}")
                print(f"Response: {http_err.response.text}")
                return None, None
            # Retry on 5xx errors (server errors)
            wait_time = 2 ** attempt
            if attempt < max_retries - 1:
                print(f"[WARNING] Server error ({http_err.response.status_code}). Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"[ERROR] HTTP error creating session after retries: {http_err}")
                print(f"Response: {http_err.response.text}")
                return None, None
        except Exception as err:
            wait_time = 2 ** attempt
            if attempt < max_retries - 1:
                print(f"[WARNING] Error creating session: {err}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"[ERROR] Error creating session after retries: {err}")
                return None, None
    
    return None, None

def create_task_in_session(task_prompt: str, session_id: str, secrets: dict = None):
    """Create a new task inside an existing session (v2 API)"""
    task_url = f"{BASE_URL}/tasks"
    headers = {
        "X-Browser-Use-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "task": task_prompt,
        "sessionId": session_id,
        "secrets": secrets or {}
    }
    
    try:
        response = requests.post(task_url, headers=headers, json=payload)
        response.raise_for_status()
        task_data = response.json()
        task_id = task_data.get("id")
        
        if task_id:
            print(f"[INFO] Task created (ID: {task_id})")
            return task_id
        else:
            print("[ERROR] Failed to create task")
            return None
            
    except requests.exceptions.HTTPError as http_err:
        print(f"[ERROR] HTTP error creating task: {http_err}")
        print(f"Response: {http_err.response.text}")
        return None
    except Exception as err:
        print(f"[ERROR] Error creating task: {err}")
        return None

def get_task_details(task_id: str):
    """Get full task details including output (v2 API)"""
    task_url = f"{BASE_URL}/tasks/{task_id}"
    headers = {"X-Browser-Use-API-Key": API_KEY}
    
    try:
        response = requests.get(task_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Error getting task details: {e}")
        return None

def wait_for_task_completion(task_id: str, poll_interval: int = 3):
    """Poll task status until completion with real-time step monitoring (v2 API)"""
    print(f"[INFO] Monitoring task {task_id}...")
    
    unique_steps = []
    
    while True:
        try:
            details = get_task_details(task_id)
            if not details:
                print("[ERROR] Failed to get task details")
                return None
            
            # Monitor and print new steps
            new_steps = details.get('steps', [])
            if new_steps != unique_steps:
                for step in new_steps:
                    if step not in unique_steps:
                        print(f"[STEP] {json.dumps(step, indent=2)}")
                unique_steps = new_steps
            
            status = details.get('status', 'unknown')
            
            if status == 'finished':
                print(f"[INFO] Task finished successfully")
                return details
            elif status in ['failed', 'stopped']:
                print(f"[ERROR] Task {status}")
                return details
            # elif status in ['created', 'started', 'paused']:
            #     # Only print status if no new steps (to avoid spam)
            #     if new_steps == unique_steps:
            #         print(f"[INFO] Task status: {status}...")
            #     time.sleep(poll_interval)
            # else:
            #     print(f"[WARNING] Unknown task status: {status}")
            #     time.sleep(poll_interval)
                
        except Exception as e:
            print(f"[ERROR] Error monitoring task: {e}")
            time.sleep(poll_interval)
def get_email_otp_for_duke(user_email: str, max_wait_seconds: int = 90, check_interval: int = 5):
    """
    Fetch OTP code from email for Duke Energy 2FA.
    Polls email inbox until OTP is found or timeout.
    
    Args:
        user_email: User's email address (used for logging only)
        max_wait_seconds: Maximum time to wait for OTP email
        check_interval: How often to check for new emails (seconds)
        
    Returns:
        OTP code as string if found, None otherwise
    """
    print(f"[INFO] Waiting for Duke Energy OTP email...")
    print(f"[INFO] Filtering by sender: no-reply@verify.dukeenergy.com")
    
    start_time = time.time()
    email_client = GraphAPIEmailClient()
    
    while time.time() - start_time < max_wait_seconds:
        try:
            # Get OTP from latest emails
            otp, subject, sender = email_client.get_latest_otp_from_inbox(
                sender_filter="no-reply@verify.dukeenergy.com",
                recipient_email=user_email,
                max_emails=5
            )
            
            if otp:
                print(f"[SUCCESS] Found OTP code: {otp}")
                print(f"[INFO] From: {sender}")
                print(f"[INFO] Subject: {subject}")
                return otp
            
            # No OTP found yet, wait and retry
            elapsed = int(time.time() - start_time)
            print(f"[INFO] Waiting for OTP email... ({elapsed}/{max_wait_seconds}s)")
            time.sleep(check_interval)
            
        except Exception as e:
            print(f"[ERROR] Error fetching email OTP: {e}")
            time.sleep(check_interval)
    
    print("[WARNING] Timeout waiting for OTP email")
    return None

# ---------------------------------------------------------------------------
# MOCK RESULT OBJECT CLASS --------------------------------------------------
# ---------------------------------------------------------------------------
class MockResult:
    """Mock result object to maintain compatibility with handle_task_result"""
    def __init__(self, task_id, status, output_files=None, done_output=None):
        self.id = task_id
        self.status = status
        self.output_files = output_files or []
        self.done_output = done_output

class MockOutputFile:
    """Mock output file object to maintain compatibility with handle_task_result"""
    def __init__(self, file_id, file_name):
        self.id = file_id
        self.file_name = file_name
        self.fileName = file_name  # Some APIs use fileName instead of file_name

class MockClient:
    """Mock client object to maintain compatibility with handle_task_result"""
    def __init__(self, task_id):
        self.task_id = task_id
    
    class tasks:
        @staticmethod
        async def get_output_file(file_id, task_id):
            """Get download URL for output file (v2 API)"""
            headers = {"X-Browser-Use-API-Key": API_KEY}
            
            # Use correct v2 endpoint: /files/tasks/{task_id}/output-files/{file_id}
            response = requests.get(
                f"{BASE_URL}/files/tasks/{task_id}/output-files/{file_id}",
                headers=headers
            )
            response.raise_for_status()
            file_data = response.json()
            
            class MockFileResponse:
                def __init__(self, download_url):
                    self.download_url = download_url
            
            # v2 API might return 'url' or 'downloadUrl' or 'download_url'
            download_url = file_data.get('url') or file_data.get('downloadUrl') or file_data.get('download_url')
            return MockFileResponse(download_url)

# ---------------------------------------------------------------------------
# AGENT FUNCTION ------------------------------------------------------------
# ---------------------------------------------------------------------------
def run_agent_task(user_cred: Dict[str, str], signin_url: str, billing_history_url: str, provider_name: str):
    """
    Runs the agent for a single user's credentials.
    For Duke Energy: 3-task flow with 2FA (login -> OTP -> download)
    For other providers: Single-task flow (no 2FA)
    Designed to be called in a separate process (multiprocessing).
    """
    async def _run():
        # Ensure ~/duke_bills exists
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
        email = user_cred.get("username")
        password = user_cred.get("password")
        credential_id = user_cred.get("credential_id")
        
        # Normalize provider name to check if Duke Energy
        is_duke = "duke" in provider_name.lower()

        print(f"[INFO] Starting remote browser task for {provider_name}...")
        
        try:
            # Create persistent session with proxy for Duke Energy
            proxy_code = "us" if is_duke else None
            session_id, live_url = create_persistent_session(signin_url, proxy_code)
            
            if not session_id:
                raise Exception("Failed to create browser session")
            
            if is_duke:
                # Duke Energy: 3-task flow with 2FA
                print("[INFO] Duke Energy detected - using 3-task flow with 2FA")
                
                # Task 1: Login and wait for 2FA page
                print("\n=== TASK 1: Login ===")
                task1_prompt = get_provider_prompt(provider_name, "task1_login")
                task1_prompt = task1_prompt.format(
                    signin_url=signin_url,
                    email=email,
                    password=password
                )
                
                task1_id = create_task_in_session(task1_prompt, session_id, {})
                if not task1_id:
                    raise Exception("Failed to create Task 1 (login)")
                
                task1_result = wait_for_task_completion(task1_id)
                if not task1_result or task1_result.get('status') != 'finished':
                    raise Exception(f"Task 1 failed: {task1_result.get('output', 'Unknown error')}")
                
                # Check if login completed without 2FA (went directly to dashboard)
                task1_output = (task1_result.get('output') or '').lower()
                skip_2fa = "successfully logged in" in task1_output
                
                if skip_2fa:
                    print("[INFO] Login completed without 2FA prompt - skipping OTP retrieval and Task 2")
                else:
                    # Fetch OTP from email
                    print("\n=== Fetching OTP from email ===")
                    otp_code = get_email_otp_for_duke(email, max_wait_seconds=90)
                    if not otp_code:
                        raise Exception("Failed to retrieve OTP code from email")
                    
                    # Task 2: Submit OTP
                    print("\n=== TASK 2: Submit 2FA ===")
                    task2_prompt = get_provider_prompt(provider_name, "task2_2fa")
                    task2_prompt = task2_prompt.format(otp_code=otp_code)
                    
                    task2_id = create_task_in_session(task2_prompt, session_id, {})
                    if not task2_id:
                        raise Exception("Failed to create Task 2 (2FA)")
                    
                    task2_result = wait_for_task_completion(task2_id)
                    if not task2_result or task2_result.get('status') != 'finished':
                        raise Exception(f"Task 2 failed: {task2_result.get('output', 'Unknown error')}")
                
                # Task 3: Navigate and download bill
                print("\n=== TASK 3: Download Bill ===")
                task3_prompt = get_provider_prompt(provider_name, "task3_download")
                task3_prompt = task3_prompt.format(billing_history_url=billing_history_url)
                
                task3_id = create_task_in_session(task3_prompt, session_id, {})
                if not task3_id:
                    raise Exception("Failed to create Task 3 (download)")
                
                task3_result = wait_for_task_completion(task3_id)
                final_task_id = task3_id
                task_details = task3_result
                
            else:
                # Non-Duke providers: Single task flow (no 2FA)
                print(f"[INFO] {provider_name} - using single-task flow (no 2FA)")
                
                task_prompt = get_provider_prompt(provider_name)
                task_prompt = task_prompt.format(
                    signin_url=signin_url,
                    email=email,
                    password=password,
                    billing_history_url=billing_history_url
                )
                
                task_id = create_task_in_session(task_prompt, session_id, {})
                if not task_id:
                    raise Exception("Failed to create task")
                
                task_details = wait_for_task_completion(task_id)
                final_task_id = task_id
            
            # Process final task result
            if not task_details:
                raise Exception("Failed to get task details")
            
            final_status = task_details.get('status')
            print(f"[INFO] Final task status: {final_status}")
            
            # Process final task result
            if not task_details:
                raise Exception("Failed to get task details")

            final_status = task_details.get('status')
            print(f"[INFO] Final task status: {final_status}")

            # DEBUG: Print all keys in task_details to see what's available
            print(f"[DEBUG] All task_details keys: {task_details.keys()}")
            print(f"[DEBUG] Full task_details: {json.dumps(task_details, indent=2)}")
            # Create mock result object for compatibility
            output_files = []
            if task_details.get('outputFiles'):  # v2 API uses camelCase
                print(f"[DEBUG] Raw outputFiles: {task_details.get('outputFiles')}")
                for file_info in task_details['outputFiles']:
                    if isinstance(file_info, dict):
                        file_id = file_info.get('id', 'unknown')
                        file_name = file_info.get('fileName', 'unknown')  # v2 API uses camelCase
                    else:
                        file_id = str(file_info)
                        file_name = str(file_info)
                    
                    if file_name.lower().endswith('.pdf'):
                        output_files.append(MockOutputFile(file_id, file_name))
            
            result = MockResult(
                task_id=final_task_id,
                status=final_status,
                output_files=output_files,
                done_output=task_details.get('output', '')
            )
            
            print(f"[INFO] Task finished:")
            print(f"  id                = {result.id}")
            print(f"  status            = {result.status}")
            print(f"  done_output       = {result.done_output}")
            print(f"  output_files      = {len(result.output_files)} files found")
            
            # Create mock client for compatibility
            client = MockClient(final_task_id)

            # Check if task failed based on done_output content and update credential error
            if result.done_output and any(keyword in result.done_output for keyword in ["Failed to log in", "Failed", "failed"]):
                try:
                    with get_db_context() as db:
                        credential = db.query(UserBillingCredential).filter(UserBillingCredential.id == credential_id).first()
                        if credential:
                            credential.last_error = result.done_output
                            credential.last_state = "error"
                            db.commit()
                            print(f"[INFO] Updated credential {credential_id} with error: {result.done_output}")
                        else:
                            print(f"[WARNING] Credential {credential_id} not found")
                except Exception as e:
                    print(f"[ERROR] Failed to update credential error: {e}")
            else:
                # Call handle_task_result with the same arguments as before
                await handle_task_result(result, client, email, DOWNLOAD_DIR, credential_id, provider_name)
            
        except Exception as e:
            print(f"[ERROR] Task execution failed: {e}")
            # Create a failed result for error handling
            result = MockResult(
                task_id="unknown",
                status="failed",
                output_files=[],
                done_output=f"Task failed: {str(e)}"
            )
            client = MockClient("unknown")
            await handle_task_result(result, client, email, DOWNLOAD_DIR, credential_id, provider_name)

    # Run the async function in a new event loop (needed for multiprocessing)
    asyncio.run(_run())


async def handle_task_result(result, client, email, DOWNLOAD_DIR, credential_id, provider_name):
    print("handle_task_result called")
    if hasattr(result, 'output_files') and result.output_files:
        print(f"  output_files      = {len(result.output_files)} files found")
        
        for output_file in result.output_files:
            file_name = getattr(output_file, 'file_name', 'unknown')
            print(f"file_id: {output_file.id}")
            print(f"file_name: {file_name}")
            if file_name.lower().endswith('.pdf'):
                try:
                    # Get download URL from remote browser agent
                    file_response = await client.tasks.get_output_file(
                        file_id=output_file.id, 
                        task_id=result.id
                    )
                    file_url = file_response.download_url
                    response = requests.get(file_url)

                    if response.status_code == 200:
                        pdf_content = response.content
                        print(f"[OK] Downloaded PDF: {file_name}")
                        print(f"[INFO] PDF size: {len(pdf_content)} bytes")

                        # Get current date info
                        now = datetime.now()
                        year = now.strftime("%Y")
                        month_name = calendar.month_name[now.month]  # e.g. January, February

                        # Create filename
                        clean_email = email.replace('@', '_').replace('+', '_').replace('.', '_')
                        safe_time = now.strftime("%d-%m-%y_%I-%M%p")
                        local_filename = f"{clean_email}_{safe_time}.pdf"
                        blob_name = local_filename

                        # Upload to Azure
                        try:
                            success, blob_url, uploaded_blob_name = azure_storage_service.upload_pdf_to_azure(
                                pdf_content=pdf_content,
                                email=email,
                                original_filename=blob_name,
                                provider=provider_name
                            )

                            if success:
                                print(f"[OK] Uploaded PDF to Azure Blob Name: {uploaded_blob_name}")
                                # Insert BillingResult entry in DB
                                try:
                                    with get_db_context() as db:
                                        billing_result = BillingResult(
                                            user_billing_credential_id=credential_id,
                                            azure_blob_url=uploaded_blob_name,
                                            run_time=datetime.utcnow(),
                                            status="success",
                                            year=year,
                                            month=month_name,
                                            provider_name=provider_name
                                        )
                                        db.add(billing_result)
                                        db.commit()
                                        
                                        # Reset is_eligible_for_retry to false on successful retry
                                        credential = db.query(UserBillingCredential).filter(UserBillingCredential.id == credential_id).first()
                                        if credential:
                                            credential.is_eligible_for_retry = False
                                            credential.last_state = "completed"
                                            credential.last_error = None  # Clear any previous error
                                            db.commit()
                                            print(f"[INFO] Reset is_eligible_for_retry to false for credential {credential_id} after successful retry")
                                        
                                        # AUTOMATIC PDF EXTRACTION
                                        print(f"[INFO] Triggering automatic PDF extraction for billing result {billing_result.id}")
                                        await trigger_automatic_extraction(billing_result, email, provider_name)

                                except Exception as db_e:
                                    print(f"[ERROR] Failed to insert BillingResult: {db_e}")
                            else:
                                print(f"[ERROR] Upload to Azure failed for {blob_name}")
                        except Exception as e:
                            print(f"[ERROR] Azure upload failed: {e}")

                    else:
                        print(f"[ERROR] Failed to download {file_name}: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"[ERROR] Error downloading {file_name}: {e}")
            else:
                print(f"[INFO] Skipping non-PDF file: {file_name}")
    else:
        print("[INFO] No output files found in task result")
        
        # Update is_eligible_for_retry to true when no output files found
        try:
            with get_db_context() as db:
                credential = db.query(UserBillingCredential).filter(UserBillingCredential.id == credential_id).first()
                if credential and credential.is_eligible_for_retry == False:
                    credential.is_eligible_for_retry = True
                    credential.last_state = "retrying"
                    db.commit()
                    print(f"[INFO] Updated is_eligible_for_retry to true for credential {credential_id} and will be retried")
                elif credential and credential.is_eligible_for_retry == True:
                    print(f"[RETRY FAILED] Credential 1{credential.is_eligible_for_retry} retried and failed again")
                    print(f"[RETRY FAILED] Credential 2{credential.last_state} retried and failed again")
                    print(f"[RETRY FAILED] Credential 3{credential.last_error} retried and failed again")
                    credential.is_eligible_for_retry = False
                    credential.last_state = "Failed"
                    credential.last_error = "Unable to download the bill"
                    db.commit()
                    print(f"[INFO] Credential {credential_id} retried and failed again")
                else:
                    print(f"[WARNING] Credential {credential_id} not found")
        except Exception as e:
            print(f"[ERROR] Failed to update is_eligible_for_retry: {e}")


async def trigger_automatic_extraction(billing_result, email, provider_name):
    """Automatically extract data from the newly created billing result"""
    try:
        print(f"[INFO] Starting automatic PDF extraction for {billing_result.id}")
        
        # Download PDF from Azure
        print(f"🔍 Downloading PDF from Azure blob: {billing_result.azure_blob_url}")
        success, pdf_content = azure_storage_service.download_pdf_from_azure(billing_result.azure_blob_url)
        
        if not success:
            raise Exception(f"Failed to download PDF from Azure blob: {billing_result.azure_blob_url}")
        
        print(f"✅ PDF downloaded successfully from Azure")
        
        # Log extraction start
        AuditLogger.log_extraction_start(
            billing_result_id=billing_result.id,
            provider_name=provider_name,
            email=email
        )
        
        # Extract bill data using RAG
        extracted_data = await extract_bill_by_provider(provider_name, pdf_content)
        
        if extracted_data:
            print(f"[✅] Extraction completed successfully")
            
            # Create Excel file from extracted data
            now = datetime.now()
            clean_email = email.replace('@', '_').replace('+', '_').replace('.', '_')
            safe_time = now.strftime("%d-%m-%y_%I-%M%p")
            
            # Flatten the nested data structure for Excel
            def flatten_dict(d, parent_key='', sep='_'):
                items = []
                for k, v in d.items():
                    new_key = f"{parent_key}{sep}{k}" if parent_key else k
                    if isinstance(v, dict):
                        items.extend(flatten_dict(v, new_key, sep=sep).items())
                    elif isinstance(v, list):
                        for i, item in enumerate(v):
                            if isinstance(item, dict):
                                items.extend(flatten_dict(item, f"{new_key}_{i}", sep=sep).items())
                            else:
                                items.append((f"{new_key}_{i}", item))
                    else:
                        items.append((new_key, v))
                return dict(items)
            
            # Create DataFrame
            flattened_data = flatten_dict(extracted_data)
            df = pd.DataFrame([flattened_data])
            
            # Create Excel file in memory
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_excel:
                excel_path = tmp_excel.name
            
            try:
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Extracted Data', index=False)
                
                # Read Excel content
                with open(excel_path, 'rb') as f:
                    excel_content = f.read()
                
                # Upload Excel to Azure
                excel_blob_name = f"{clean_email}_{safe_time}_extracted_data.xlsx"
                success, excel_blob_url, uploaded_excel_name = azure_storage_service.upload_pdf_to_azure(
                    pdf_content=excel_content,
                    email=email,
                    original_filename=excel_blob_name,
                    provider=provider_name
                )
                
                if success:
                    print(f"[✅] Excel file uploaded to Azure: {uploaded_excel_name}")
                    
                    # Upload JSON to Azure
                    json_content = json.dumps(extracted_data, indent=2).encode('utf-8')
                    json_blob_name = f"{clean_email}_{safe_time}_extracted_data.json"
                    
                    json_success, json_blob_url, uploaded_json_name = azure_storage_service.upload_pdf_to_azure(
                        pdf_content=json_content,
                        email=email,
                        original_filename=json_blob_name,
                        provider=provider_name
                    )
                    
                    if json_success:
                        print(f"[✅] JSON data uploaded to Azure: {uploaded_json_name}")
                        
                        # Update the BillingResult with the new blob URLs
                        try:
                            with get_db_context() as db:
                                billing_record = db.query(BillingResult).filter(BillingResult.id == billing_result.id).first()
                                if billing_record:
                                    billing_record.excel_blob_url = uploaded_excel_name
                                    billing_record.json_blob_url = uploaded_json_name
                                    db.commit()
                                    print(f"[✅] Updated BillingResult with Excel and JSON blob URLs")
                                    
                                    # Log extraction success
                                    AuditLogger.log_extraction_complete(
                                        billing_result_id=billing_result.id,
                                        provider_name=provider_name,
                                        email=email,
                                        success=True,
                                        excel_url=uploaded_excel_name,
                                        json_url=uploaded_json_name
                                    )
                                else:
                                    print(f"[❌] BillingResult not found for ID: {billing_result.id}")
                        except Exception as db_error:
                            print(f"[❌] Failed to update BillingResult: {db_error}")
                    else:
                        print(f"[❌] Failed to upload JSON data to Azure")
                else:
                    print(f"[❌] Failed to upload Excel file to Azure")
            finally:
                # Cleanup temp Excel file
                Path(excel_path).unlink()
        else:
            print(f"[❌] No data extracted from PDF")
                
    except Exception as e:
        print(f"[❌] Error in automatic PDF extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Log extraction failure
        AuditLogger.log_extraction_complete(
            billing_result_id=billing_result.id,
            provider_name=provider_name,
            email=email,
            success=False,
            error=str(e)
        )