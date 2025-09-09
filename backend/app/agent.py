import os
import asyncio
import requests
import httpx
import calendar
import json

from datetime import datetime
from typing import Dict
# Import Azure storage service
from azure_storage_service import azure_storage_service

from browser_use_sdk import AsyncBrowserUse
from config import config
from app.models import BillingResult
from app.db import SessionLocal


# ---------------------------------------------------------------------------
# CONFIGURATION -------------------------------------------------------------
# ---------------------------------------------------------------------------
DOWNLOAD_DIR = os.path.expanduser("~/duke_bills")  # ~/duke_bills on any OS
API_KEY=config.BROWSER_USE_API_KEY

# ---------------------------------------------------------------------------
# AGENT FUNCTION ------------------------------------------------------------
# ---------------------------------------------------------------------------
def run_agent_task(user_cred: Dict[str, str], signin_url: str, billing_history_url: str):
    """
    Runs the Duke Energy agent for a single user's credentials.
    Designed to be called in a separate process (multiprocessing).
    """
    async def _run():
        # Ensure ~/duke_bills exists
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
        client = AsyncBrowserUse(api_key=API_KEY)

        email = user_cred.get("username")
        password = user_cred.get("password")

        # You must pass the credential_id to handle_task_result
        credential_id = user_cred.get("credential_id")  # Make sure this is set in user_cred

        TASK_TEMPLATE = f"""
1. Go to {signin_url}
2. Wait for the page to fully load (this site is slow)
3. Log-in with:
     • email    : {email}
     • password : {password}
4. Wait until dashboard finishes loading
5. Navigate to {billing_history_url}
6. Wait until the text "Billing & Payment Activity" is visible
7. If "Oops, something went wrong." appears, STOP the task
8. Click only the "View Bill" button in the FIRST row
9. Wait until the bill PDF finishes downloading
"""

        # print("[INFO] Starting remote browser task …")
        # result = await client.tasks.run(
        #     task=TASK_TEMPLATE,
        # )

        # # Give Cloud task a moment to finish syncing
        # await asyncio.sleep(10)

        # print(f"[INFO] Task finished:")
        # print(f"  id                = {result.id}")
        # print(f"  status            = {result.status}")
        # print(f"  done_output       = {result.done_output}")
        # print(f"  output_files       = {result.output_files}")
        
        #  # 👇 Call your helper
        # await handle_task_result(result, client, email, DOWNLOAD_DIR, credential_id)
         # 🧪 TESTING: Comment out agent execution for PDF extraction testing
        print("[TEST] Skipping agent execution - using mock result for testing")
        
        # Create a mock result object for testing
        class MockOutputFile:
            def __init__(self, file_id, file_name):
                self.id = file_id
                self.file_name = file_name
                self.fileName = file_name  # Some APIs use fileName instead of file_name
        
        class MockResult:
            def __init__(self):
                self.id = "test-task-id-12345"
                self.status = "finished"
                self.done_output = None
                self.output_files = [MockOutputFile("test-file-id-67890", "Billing.pdf")]
        
        result = MockResult()
        
        print(f"[TEST] Mock task result created:")
        print(f"  id                = {result.id}")
        print(f"  status            = {result.status}")
        print(f"  done_output       = {result.done_output}")
        print(f"  output_files       = {result.output_files}")
        
        # 👇 Call your helper with mock result
        await handle_task_result(result, client, email, DOWNLOAD_DIR, credential_id)
    # Run the async function in a new event loop (needed for multiprocessing)
    asyncio.run(_run())



import calendar

import os
import requests
import calendar
from datetime import datetime

# Assuming you have a service like this injected/available
# from services.azure_storage import azure_storage_service


async def handle_task_result(result, client, email, DOWNLOAD_DIR, credential_id):
    print("handle_task_result called")
    if hasattr(result, 'output_files') and result.output_files:
        print(f"  output_files      = {len(result.output_files)} files found")
        
        for output_file in result.output_files:
            file_name = getattr(output_file, 'file_name', 'unknown')
            print(f"file_id: {output_file.id}")
            print(f"file_name: {file_name}")
            if file_name.lower().endswith('.pdf'):
                try:
                    # 🧪 TESTING: Use existing PDF from bills directory instead of downloading
                    print(f"[TEST] Using existing PDF for testing extraction functionality")
                    
                    # Use the first available PDF from bills/2025/August
                    test_pdf_path = "bills/2025/August/billing_rtx_sagiliti_com_2025-08-23_09-46-07_AM.pdf"
                    
                    if not os.path.exists(test_pdf_path):
                        print(f"[ERROR] Test PDF not found at {test_pdf_path}")
                        continue
                    
                    # Read the existing PDF file
                    with open(test_pdf_path, "rb") as f:
                        pdf_content = f.read()
                    
                    print(f"[OK] Using test PDF: {test_pdf_path}")
                    print(f"[INFO] PDF size: {len(pdf_content)} bytes")

                    # Get current date info
                    now = datetime.now()
                    year = now.strftime("%Y")
                    month_name = calendar.month_name[now.month]  # e.g. January, February

                    # Create a test filename
                    clean_email = email.replace('@', '_').replace('+', '_').replace('.', '_')
                    safe_time = now.strftime("%d-%m-%y_%I-%M%p")
                    test_filename = f"{clean_email}_{safe_time}_test.pdf"
                    blob_name = f"{year}/{month_name}/{test_filename}"

                    # Upload to Azure
                    try:
                        success, blob_url, uploaded_blob_name = azure_storage_service.upload_pdf_to_azure(
                            pdf_content=pdf_content,
                            email=email,
                            original_filename=blob_name
                        )

                        if success:
                            print(f"[OK] Uploaded test PDF to Azure Blob Name: {uploaded_blob_name}")
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
                                
                                # 🤖 AUTOMATIC PDF EXTRACTION
                                print(f"[INFO] Triggering automatic PDF extraction for billing result {billing_result.id}")
                                await trigger_automatic_extraction(billing_result, email)

                                db.close()

                            except Exception as db_e:
                                print(f"[ERROR] Failed to insert BillingResult: {db_e}")
                                if 'db' in locals():
                                    db.close()
                        else:
                            print(f"[ERROR] Upload to Azure failed for {blob_name}")
                    except Exception as e:
                        print(f"[ERROR] Azure upload failed: {e}")
                        
                except Exception as e:
                    print(f"[ERROR] Error processing test PDF: {e}")
            else:
                print(f"[INFO] Skipping non-PDF file: {file_name}")
    else:
        print("[INFO] No output files found in task result")

async def trigger_automatic_extraction(billing_result, email):
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
                        excel_blob_name = f"{billing_result.year}/{billing_result.month}/{clean_email}_{safe_time}_extracted_data.xlsx"
                        
                        try:
                            success, excel_blob_url, uploaded_excel_name = azure_storage_service.upload_pdf_to_azure(
                                pdf_content=excel_content,
                                email=email,
                                original_filename=excel_blob_name
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

                                json_blob_name = f"{billing_result.year}/{billing_result.month}/{clean_email}_{safe_time}_extracted_data.json"
                                
                                json_success, json_blob_url, uploaded_json_name = azure_storage_service.upload_pdf_to_azure(
                                    pdf_content=json_content,
                                    email=email,
                                    original_filename=json_blob_name
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
























# # ----------------------------------------------
# import asyncio
# import os
# import calendar


# from pathlib import Path
# from datetime import datetime
# from browser_use import Agent, BrowserSession, BrowserProfile
# from browser_use.llm import ChatOpenAI
# from dotenv import load_dotenv
# from typing import Dict


# load_dotenv()

# from azure_storage_service import azure_storage_service

# # ---------------------------------------------------------------------------
# # CONFIGURATION -------------------------------------------------------------
# # ---------------------------------------------------------------------------
# # DOWNLOAD_DIR = os.path.expanduser("~/duke_bills")
# DOWNLOAD_DIR = BILLS_DIR = Path("bills")# ~/duke_bills on any OS

# # ---------------------------------------------------------------------------
# # AGENT FUNCTION ------------------------------------------------------------
# # ---------------------------------------------------------------------------
# def run_agent_task(user_cred: Dict[str, str], signin_url: str, billing_history_url: str):
#     """
#     Runs the Duke Energy agent for a single user's credentials.
#     Designed to be called in a separate process (multiprocessing).
#     """
    
#     async def _run():
#         # ---------------------------------------------------------------------------
#         # MAIN TASK -----------------------------------------------------------------
#         # ---------------------------------------------------------------------------
#         TASK_TEMPLATE = f"""
#         1. Go to {signin_url}.
#         2. Wait for the login page to fully load.
#         3. Log in with:
#             • email    : {user_cred.get("username")}
#             • password : {user_cred.get("password")}
#         4. After clicking sign in, wait until the dashboard has fully loaded.
#         5. Navigate to {billing_history_url}.
#         6. Wait until the billing history page fully loads and billing rows are visible.
#         7. If "Oops, something went wrong." appears, STOP the task immediately.
#         8. Find the "View Bill" button in the FIRST billing row.
#         9. Click the "View Bill" button in the FIRST row EXACTLY ONE TIME.
#         10. After clicking once, wait 3 seconds for the download to complete.
#         11. TASK IS NOW COMPLETE. Do not click any more buttons or take any more actions.
#         12. Use the 'done' action to mark the task as finished with message "Successfully downloaded one bill".
#         """
#         # Use downloads_path instead of Chrome args
#         browser_profile = BrowserProfile(
#             headless=True,
#             java_script_enabled=True,
#             downloads_path=DOWNLOAD_DIR,  # Use the proper downloads_path parameter
#             args=[
#                 "--no-sandbox", 
#                 "--disable-setuid-sandbox",
#                 "--disable-dev-shm-usage",
#                 "--disable-gpu",
#                 "--disable-web-security",
#                 "--disable-features=VizDisplayCompositor",
#                 "--disable-background-timer-throttling",
#                 "--disable-backgrounding-occluded-windows",
#                 "--disable-renderer-backgrounding",
#                 "--disable-field-trial-config",
#                 "--disable-ipc-flooding-protection",
#                 "--window-size=1920,1080",
#                 "--disable-extensions",
#                 "--no-first-run",
#                 "--disable-default-apps",
#             ],
#             wait_between_actions=2.0,
#         )

#         browser_session = BrowserSession(
#             browser_profile=browser_profile,
#         )

#         agent = Agent(
#             task=TASK_TEMPLATE,
#             llm=ChatOpenAI(model="gpt-4o-mini"),
#             browser_session=browser_session,
#             max_failures=5,
#             retry_delay=3,
#         )

#         print(f"Starting Duke Energy billing task...")
#         print(f"Downloads will be saved to: {DOWNLOAD_DIR}")
        
#         # Track initial files in the bills directory before agent runs
#         download_path = DOWNLOAD_DIR
#         initial_files = set(os.listdir(download_path))

#         try:
#             result = await agent.run()
#             print("Task completed!")
#             print(f"Final result: {result.final_result()}")

#             # Give the remote browser a moment to finish synchronising the file
#             await asyncio.sleep(5)

#             bill_files = list(download_path.glob("*.pdf")) + list(download_path.glob("*.PDF"))

#             # Bills were downloaded successfully!
#             print(f"✅ Bills found: {len(bill_files)} files downloaded for user: {user_cred.get('username')}")
#             # Detect new files
#             new_files = set(os.listdir(download_path)) - initial_files
            
#             clean_email = user_cred.get('username').replace('@', '_').replace('+', '_').replace('.', '_')

#             # Get current date info
#             now = datetime.now()
#             year = now.strftime("%Y")
#             month_name = calendar.month_name[now.month]  # e.g. January, February

#             if new_files:
#                 for file in new_files:
#                     # -----------------------------------
#                     # Upload same file to Azure
#                     # -----------------------------------
                    
#                     safe_time = now.strftime("%d-%m-%y_%I-%M%p")
                    
#                     # Local filename and path
#                     local_filename = f"{clean_email}_{safe_time}.pdf"
#                     pdf_content = file  # raw bytes
#                     blob_name = f"{year}/{month_name}/{local_filename}"
#                     credential_id = user_cred.get('credential_id')  # Make sure this is set in user_cred

#                     try:
#                         uploaded_blob_name = azure_storage_service.upload_pdf_to_azure(
#                             pdf_content=pdf_content,
#                             email=user_cred.get('username'),
#                             original_filename=blob_name
#                         )

#                         if uploaded_blob_name:
#                             print(f"[OK] Uploaded to Azure Blob Name: {uploaded_blob_name}")
#                             # Insert BillingResult entry in DB
#                             try:
#                                 from app.models import BillingResult
#                                 from app.db import SessionLocal
#                                 db = SessionLocal()
#                                 # You need to pass the correct credential id here
#                                 # If you have it available, use it. Otherwise, you may need to pass it to this function.
#                                 billing_result = BillingResult(
#                                     user_billing_credential_id=credential_id,
#                                     azure_blob_url=uploaded_blob_name,
#                                     run_time=datetime.utcnow(),
#                                     status="success",
#                                     year=year,
#                                     month=month_name
#                                 )
#                                 db.add(billing_result)
#                                 db.commit()
#                                 db.close()
#                             except Exception as db_e:
#                                 print(f"[ERROR] Failed to insert BillingResult: {db_e}")
#                         else:
#                             print(f"[ERROR] Upload to Azure failed for {blob_name}")
#                     except Exception as e:
#                         print(f"[ERROR] Azure upload failed: {e}")


#             print(f"[INFO] Task finished:")
#         except Exception as e:
#             print(f"Task failed with error: {e}")

#     # Run the async function in a new event loop (needed for multiprocessing)
#     asyncio.run(_run())