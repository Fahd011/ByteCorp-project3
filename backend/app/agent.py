import os
import asyncio
import requests
import httpx
import calendar
import json
import time

from datetime import datetime
from typing import Dict
# Import Azure storage service
from azure_storage_service import azure_storage_service

from config import config
from app.models import BillingResult, UserBillingCredential
from app.db import SessionLocal
from app.prompts import get_provider_prompt


# ---------------------------------------------------------------------------
# CONFIGURATION -------------------------------------------------------------
# ---------------------------------------------------------------------------
DOWNLOAD_DIR = os.path.expanduser("~/duke_bills")  # ~/duke_bills on any OS
API_KEY = config.BROWSER_USE_API_KEY
BASE_URL = 'https://api.browser-use.com/api/v1'
HEADERS = {'Authorization': f'Bearer {API_KEY}'}

# ---------------------------------------------------------------------------
# BROWSER USE CLOUD API FUNCTIONS -------------------------------------------
# ---------------------------------------------------------------------------
def create_task(instructions: str):
    """Create a new browser automation task"""
    response = requests.post(f'{BASE_URL}/run-task', headers=HEADERS, json={'task': instructions})
    response.raise_for_status()
    return response.json()['id']

def get_task_status(task_id: str):
    """Get current task status"""
    response = requests.get(f'{BASE_URL}/task/{task_id}/status', headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_task_details(task_id: str):
    """Get full task details including output"""
    response = requests.get(f'{BASE_URL}/task/{task_id}', headers=HEADERS)
    response.raise_for_status()
    return response.json()

def wait_for_completion(task_id: str, poll_interval: int = 2):
    """Poll task status until completion with real-time step monitoring"""
    count = 0
    unique_steps = []
    
    print(f"[INFO] Monitoring task {task_id}...")
    
    while True:
        try:
            details = get_task_details(task_id)
            new_steps = details.get('steps', [])
            
            # Print only new steps that haven't been seen before
            if new_steps != unique_steps:
                for step in new_steps:
                    if step not in unique_steps:
                        print(f"[STEP] {json.dumps(step, indent=2)}")
                unique_steps = new_steps
            
            count += 1
            status = details.get('status', 'unknown')
            
            if status in ['finished', 'failed', 'stopped']:
                print(f"[INFO] Task completed with status: {status}")
                return details
                
            time.sleep(poll_interval)
            
        except Exception as e:
            print(f"[ERROR] Error monitoring task: {e}")
            time.sleep(poll_interval)

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
            """Get download URL for output file"""
            response = requests.get(
                f"{BASE_URL}/task/{task_id}/output-file/{file_id}", 
                headers=HEADERS
            )
            response.raise_for_status()
            file_data = response.json()
            
            class MockFileResponse:
                def __init__(self, download_url):
                    self.download_url = download_url
            
            return MockFileResponse(file_data.get('download_url'))

# ---------------------------------------------------------------------------
# AGENT FUNCTION ------------------------------------------------------------
# ---------------------------------------------------------------------------
def run_agent_task(user_cred: Dict[str, str], signin_url: str, billing_history_url: str, provider_name: str):
    """
    Runs the agent for a single user's credentials.
    Designed to be called in a separate process (multiprocessing).
    """
    async def _run():
        # Ensure ~/duke_bills exists
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
        email = user_cred.get("username")
        password = user_cred.get("password")
        credential_id = user_cred.get("credential_id")

        # Create the task instructions using provider-specific template
        task_instructions = get_provider_prompt(provider_name)
        task_instructions = task_instructions.format(
            signin_url=signin_url,
            email=email,
            password=password,
            billing_history_url=billing_history_url
        )

        print("[INFO] Starting remote browser task …")
        
        try:
            # Create the task
            task_id = create_task(task_instructions)
            print(f"[SUCCESS] Task created with ID: {task_id}")
            
            # Monitor task completion
            task_details = wait_for_completion(task_id)
            
            # Check final status
            final_status = task_details.get('status')
            print(f"[INFO] Final task status: {final_status}")
            
            # Create mock result object for compatibility
            output_files = []
            if task_details.get('output_files'):
                print(f"[DEBUG] Raw output_files: {task_details.get('output_files')}")
                for file_info in task_details['output_files']:
                    if isinstance(file_info, dict):
                        file_id = file_info.get('id', 'unknown')
                        file_name = file_info.get('file_name', 'unknown')
                    else:
                        file_id = str(file_info)
                        file_name = str(file_info)
                    
                    if file_name.lower().endswith('.pdf'):
                        output_files.append(MockOutputFile(file_id, file_name))
            
            result = MockResult(
                task_id=task_id,
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
            client = MockClient(task_id)

            # Check if task failed based on done_output content and update credential error
            if result.done_output and any(keyword in result.done_output for keyword in ["Failed to log in", "Failed", "failed"]): # Removed extra unncessary keywords
                try:
                    db = SessionLocal()
                    credential = db.query(UserBillingCredential).filter(UserBillingCredential.id == credential_id).first()
                    if credential:
                        credential.last_error = result.done_output
                        credential.last_state = "error"
                        db.commit()
                        print(f"[INFO] Updated credential {credential_id} with error: {result.done_output}")
                    else:
                        print(f"[WARNING] Credential {credential_id} not found")
                    db.close()
                except Exception as e:
                    print(f"[ERROR] Failed to update credential error: {e}")
                    if 'db' in locals():
                        db.close()
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
                                    db = SessionLocal()
                                    
                                    billing_result = BillingResult(
                                        user_billing_credential_id=credential_id,
                                        azure_blob_url=uploaded_blob_name,
                                        run_time=datetime.utcnow(),
                                        status="success",
                                        year=year,
                                        month=month_name
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

                                    db.close()

                                except Exception as db_e:
                                    print(f"[ERROR] Failed to insert BillingResult: {db_e}")
                                    if 'db' in locals():
                                        db.close()
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
            db = SessionLocal()
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
            db.close()
        except Exception as e:
            print(f"[ERROR] Failed to update is_eligible_for_retry: {e}")
            if 'db' in locals():
                db.close()


async def trigger_automatic_extraction(billing_result, email, provider_name):
    """Automatically extract data from the newly created billing result"""
    try:
        # Prepare the billing result data for extraction
        billing_data = {
            "id": billing_result.id,
            "azure_blob_url": billing_result.azure_blob_url,
            "username": email,  # Use the actual email from the credential
            "year": billing_result.year,
            "month": billing_result.month,
            "status": billing_result.status
        }
        
        print(f"[INFO] Starting automatic PDF extraction for {billing_result.id}")
        
        # Call the PDF extraction API
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:5000/api/pdf-extraction/upload",
                json={"billing_result": billing_data}
            )
            
            if response.status_code == 200:
                print(f"[✅] Automatic PDF extraction completed successfully for {billing_result.id}")
                extraction_response = response.json()
                print(f"[INFO] Extraction response: {extraction_response}")
                
                # Get the session_id from the response
                session_id = extraction_response.get("session_id")
                if session_id:
                    # Export to Excel and get the file
                    excel_response = await client.get(f"http://localhost:5000/api/pdf-extraction/export/{session_id}")
                    
                    if excel_response.status_code == 200:
                        # Save Excel file to Azure
                        now = datetime.now()
                        clean_email = email.replace('@', '_').replace('+', '_').replace('.', '_')
                        safe_time = now.strftime("%d-%m-%y_%I-%M%p")
                        excel_content = excel_response.content
                        excel_blob_name = f"/{clean_email}_{safe_time}_extracted_data.xlsx"
                        
                        try:
                            success, excel_blob_url, uploaded_excel_name = azure_storage_service.upload_pdf_to_azure(
                                pdf_content=excel_content,
                                email=email,
                                original_filename=excel_blob_name,
                                provider=provider_name
                            )
                            
                            if success:
                                print(f"[✅] Excel file uploaded to Azure: {uploaded_excel_name}")
                                
                                # Save JSON data to Azure
                                # Get the first result's extracted_data
                                results = extraction_response.get("results", [])
                                if results and len(results) > 0:
                                    json_data = results[0].get("extracted_data", {})
                                    json_content = json.dumps(json_data, indent=2).encode('utf-8')
                                else:
                                    print("[❌] No extraction results found")
                                    json_data = {}
                                    json_content = json.dumps(json_data, indent=2).encode('utf-8')

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
                                    from app.db import SessionLocal
                                    db = SessionLocal()
                                    try:
                                        # Get the billing result and update it
                                        billing_record = db.query(BillingResult).filter(BillingResult.id == billing_result.id).first()
                                        if billing_record:
                                            billing_record.excel_blob_url = uploaded_excel_name
                                            billing_record.json_blob_url = uploaded_json_name
                                            db.commit()
                                            print(f"[✅] Updated BillingResult with Excel and JSON blob URLs")
                                        else:
                                            print(f"[❌] BillingResult not found for ID: {billing_result.id}")
                                    except Exception as db_error:
                                        print(f"[❌] Failed to update BillingResult: {db_error}")
                                        db.rollback()
                                    finally:
                                        db.close()
                                else:
                                    print(f"[❌] Failed to upload JSON data to Azure")
                            else:
                                print(f"[❌] Failed to upload Excel file to Azure")
                        except Exception as azure_error:
                            print(f"[❌] Azure upload error: {azure_error}")
                    else:
                        print(f"[❌] Failed to export Excel file: {excel_response.status_code}")
                else:
                    print(f"[❌] No session_id in extraction response")
            else:
                print(f"[❌] Automatic PDF extraction failed for {billing_result.id}")
                print(f"[ERROR] Status: {response.status_code}, Response: {response.text}")
                
    except Exception as e:
        print(f"[❌] Error in automatic PDF extraction: {str(e)}")
        import traceback
        traceback.print_exc()