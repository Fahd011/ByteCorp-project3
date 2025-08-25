# import os
# import asyncio
# import requests

# from datetime import datetime
# from typing import Dict
# # Import Azure storage service
# from azure_storage_service import azure_storage_service

# from browser_use_sdk import AsyncBrowserUse

# # ---------------------------------------------------------------------------
# # CONFIGURATION -------------------------------------------------------------
# # ---------------------------------------------------------------------------
# DOWNLOAD_DIR = os.path.expanduser("~/duke_bills")  # ~/duke_bills on any OS
# API_KEY  = os.environ.get(
#     "BROWSER_USE_API_KEY",
#     "bu_7xpa6a_pYy1Xz1mspGw0azXf_9EOZk_IVHwZh-5UVKM",
# )

# # ---------------------------------------------------------------------------
# # AGENT FUNCTION ------------------------------------------------------------
# # ---------------------------------------------------------------------------
# def run_agent_task(user_cred: Dict[str, str], signin_url: str, billing_history_url: str):
#     """
#     Runs the Duke Energy agent for a single user's credentials.
#     Designed to be called in a separate process (multiprocessing).
#     """
#     async def _run():
#         # Ensure ~/duke_bills exists
#         os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
#         client = AsyncBrowserUse(api_key=API_KEY)

#         email = user_cred.get("username")
#         password = user_cred.get("password")

#         # You must pass the credential_id to handle_task_result
#         credential_id = user_cred.get("credential_id")  # Make sure this is set in user_cred

#         TASK_TEMPLATE = f"""
# 1. Go to {signin_url}
# 2. Wait for the page to fully load (this site is slow)
# 3. Log-in with:
#      • email    : {email}
#      • password : {password}
# 4. Wait until dashboard finishes loading
# 5. Navigate to {billing_history_url}
# 6. Wait until the text "Billing & Payment Activity" is visible
# 7. If "Oops, something went wrong." appears, STOP the task
# 8. Click only the "View Bill" button in the FIRST row
# 9. Wait until the bill PDF finishes downloading
# """

#         print("[INFO] Starting remote browser task …")
#         result = await client.tasks.run(
#             task=TASK_TEMPLATE,
#         )

#         # Give Cloud task a moment to finish syncing
#         await asyncio.sleep(10)

#         print(f"[INFO] Task finished:")
#         print(f"  id                = {result.id}")
#         print(f"  status            = {result.status}")
#         print(f"  done_output       = {result.done_output}")
#         print(f"  output_files       = {result.output_files}")
        
#          # 👇 Call your helper
#         await handle_task_result(result, client, email, DOWNLOAD_DIR, credential_id)

#     # Run the async function in a new event loop (needed for multiprocessing)
#     asyncio.run(_run())



# import calendar

# import os
# import requests
# import calendar
# from datetime import datetime

# # Assuming you have a service like this injected/available
# # from services.azure_storage import azure_storage_service


# async def handle_task_result(result, client, email, DOWNLOAD_DIR, credential_id):
#     print("handle_task_result called")
#     if hasattr(result, 'output_files') and result.output_files:
#         print(f"  output_files      = {len(result.output_files)} files found")
        
#         for output_file in result.output_files:
#             file_name = getattr(output_file, 'file_name', 'unknown')
#             if file_name.lower().endswith('.pdf'):
#                 try:
#                     # Get download URL from remote browser agent
#                     file_response = await client.tasks.get_output_file(
#                         file_id=output_file.id, 
#                         task_id=result.id
#                     )
#                     file_url = file_response.download_url
#                     response = requests.get(file_url)

#                     if response.status_code == 200:
#                         clean_email = email.replace('@', '_').replace('+', '_').replace('.', '_')

#                         # Get current date info
#                         now = datetime.now()
#                         year = now.strftime("%Y")
#                         month_name = calendar.month_name[now.month]  # e.g. January, February

#                         # Local folder structure (~/duke_bills/2025/January/)
#                         year_folder = os.path.join(DOWNLOAD_DIR, year)
#                         month_folder = os.path.join(year_folder, month_name)
#                         os.makedirs(month_folder, exist_ok=True)

#                         # Human-readable + safe datetime for filename
#                         human_time = now.strftime("%d/%m/%y %I:%M%p")
#                         safe_time = now.strftime("%d-%m-%y_%I-%M%p")

#                         # Local filename and path
#                         local_filename = f"{clean_email}_{safe_time}.pdf"
#                         local_path = os.path.join(month_folder, local_filename)

#                         # Save file locally
#                         with open(local_path, "wb") as f:
#                             f.write(response.content)

#                         print(f"[OK] Downloaded and saved locally: {local_path}")
#                         print(f"[INFO] Download time: {human_time}")

#                         # -----------------------------------
#                         # Upload same file to Azure
#                         # -----------------------------------
#                         pdf_content = response.content  # raw bytes
#                         blob_name = f"{year}/{month_name}/{local_filename}"

#                         try:
#                             success, blob_url, uploaded_blob_name = azure_storage_service.upload_pdf_to_azure(
#                                 pdf_content=pdf_content,
#                                 email=email,
#                                 original_filename=blob_name
#                             )

#                             if success:
#                                 print(f"[OK] Uploaded to Azure Blob Name: {uploaded_blob_name}")
#                                 # Insert BillingResult entry in DB
#                                 try:
#                                     from app.models import BillingResult
#                                     from app.db import SessionLocal
#                                     db = SessionLocal()
#                                     # You need to pass the correct credential id here
#                                     # If you have it available, use it. Otherwise, you may need to pass it to this function.
#                                     billing_result = BillingResult(
#                                         user_billing_credential_id=credential_id,
#                                         azure_blob_url=uploaded_blob_name,
#                                         run_time=datetime.utcnow(),
#                                         status="success",
#                                         year=year,
#                                         month=month_name
#                                     )
#                                     db.add(billing_result)
#                                     db.commit()
#                                     db.close()
#                                 except Exception as db_e:
#                                     print(f"[ERROR] Failed to insert BillingResult: {db_e}")
#                             else:
#                                 print(f"[ERROR] Upload to Azure failed for {blob_name}")
#                         except Exception as e:
#                             print(f"[ERROR] Azure upload failed: {e}")

#                     else:
#                         print(f"[ERROR] Failed to download {file_name}: HTTP {response.status_code}")
                        
#                 except Exception as e:
#                     print(f"[ERROR] Error downloading {file_name}: {e}")
#             else:
#                 print(f"[INFO] Skipping non-PDF file: {file_name}")
#     else:
#         print("[INFO] No output files found in task result")


























# ----------------------------------------------
import asyncio
import os
import calendar


from pathlib import Path
from datetime import datetime
from browser_use import Agent, BrowserSession, BrowserProfile
from browser_use.llm import ChatOpenAI
from dotenv import load_dotenv
from typing import Dict


load_dotenv()

from azure_storage_service import azure_storage_service

# ---------------------------------------------------------------------------
# CONFIGURATION -------------------------------------------------------------
# ---------------------------------------------------------------------------
# DOWNLOAD_DIR = os.path.expanduser("~/duke_bills")
DOWNLOAD_DIR = BILLS_DIR = Path("bills")# ~/duke_bills on any OS
API_KEY  = os.environ.get(
    "BROWSER_USE_API_KEY",
    "bu_7xpa6a_pYy1Xz1mspGw0azXf_9EOZk_IVHwZh-5UVKM",
)

# ---------------------------------------------------------------------------
# AGENT FUNCTION ------------------------------------------------------------
# ---------------------------------------------------------------------------
def run_agent_task(user_cred: Dict[str, str], signin_url: str, billing_history_url: str):
    """
    Runs the Duke Energy agent for a single user's credentials.
    Designed to be called in a separate process (multiprocessing).
    """
    
    async def _run():
        # ---------------------------------------------------------------------------
        # MAIN TASK -----------------------------------------------------------------
        # ---------------------------------------------------------------------------
        TASK_TEMPLATE = f"""
        1. Go to {signin_url}.
        2. Wait for the login page to fully load.
        3. Log in with:
            • email    : {user_cred.get("username")}
            • password : {user_cred.get("password")}
        4. After clicking sign in, wait until the dashboard has fully loaded.
        5. Navigate to {billing_history_url}.
        6. Wait until the billing history page fully loads and billing rows are visible.
        7. If "Oops, something went wrong." appears, STOP the task immediately.
        8. Find the "View Bill" button in the FIRST billing row.
        9. Click the "View Bill" button in the FIRST row EXACTLY ONE TIME.
        10. After clicking once, wait 3 seconds for the download to complete.
        11. TASK IS NOW COMPLETE. Do not click any more buttons or take any more actions.
        12. Use the 'done' action to mark the task as finished with message "Successfully downloaded one bill".
        """
        # Use downloads_path instead of Chrome args
        browser_profile = BrowserProfile(
            headless=True,
            java_script_enabled=True,
            downloads_path=DOWNLOAD_DIR,  # Use the proper downloads_path parameter
            args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-field-trial-config",
                "--disable-ipc-flooding-protection",
                "--window-size=1920,1080",
                "--disable-extensions",
                "--no-first-run",
                "--disable-default-apps",
            ],
            wait_between_actions=2.0,
        )

        browser_session = BrowserSession(
            browser_profile=browser_profile,
        )

        agent = Agent(
            task=TASK_TEMPLATE,
            llm=ChatOpenAI(model="gpt-4o-mini"),
            browser_session=browser_session,
            max_failures=5,
            retry_delay=3,
        )

        print(f"Starting Duke Energy billing task...")
        print(f"Downloads will be saved to: {DOWNLOAD_DIR}")
        
        # Track initial files in the bills directory before agent runs
        download_path = DOWNLOAD_DIR
        initial_files = set(os.listdir(download_path))

        try:
            result = await agent.run()
            print("Task completed!")
            print(f"Final result: {result.final_result()}")

            # Give the remote browser a moment to finish synchronising the file
            await asyncio.sleep(5)

            bill_files = list(download_path.glob("*.pdf")) + list(download_path.glob("*.PDF"))

            # Bills were downloaded successfully!
            print(f"✅ Bills found: {len(bill_files)} files downloaded for user: {user_cred.get('username')}")
            # Detect new files
            new_files = set(os.listdir(download_path)) - initial_files
            
            clean_email = user_cred.get('username').replace('@', '_').replace('+', '_').replace('.', '_')

            # Get current date info
            now = datetime.now()
            year = now.strftime("%Y")
            month_name = calendar.month_name[now.month]  # e.g. January, February

            if new_files:
                for file in new_files:
                    # -----------------------------------
                    # Upload same file to Azure
                    # -----------------------------------
                    
                    safe_time = now.strftime("%d-%m-%y_%I-%M%p")
                    
                    # Local filename and path
                    local_filename = f"{clean_email}_{safe_time}.pdf"
                    pdf_content = file  # raw bytes
                    blob_name = f"{year}/{month_name}/{local_filename}"
                    credential_id ="54c0d7fa-c282-438a-99ae-3a435774aa85"

                    try:
                        success, uploaded_blob_name = azure_storage_service.upload_pdf_to_azure(
                            pdf_content=pdf_content,
                            email=user_cred.get('username'),
                            original_filename=blob_name
                        )

                        if success:
                            print(f"[OK] Uploaded to Azure Blob Name: {uploaded_blob_name}")
                            # Insert BillingResult entry in DB
                            try:
                                from app.models import BillingResult
                                from app.db import SessionLocal
                                db = SessionLocal()
                                # You need to pass the correct credential id here
                                # If you have it available, use it. Otherwise, you may need to pass it to this function.
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
                                db.close()
                            except Exception as db_e:
                                print(f"[ERROR] Failed to insert BillingResult: {db_e}")
                        else:
                            print(f"[ERROR] Upload to Azure failed for {blob_name}")
                    except Exception as e:
                        print(f"[ERROR] Azure upload failed: {e}")


            print(f"[INFO] Task finished:")
        except Exception as e:
            print(f"Task failed with error: {e}")

    # Run the async function in a new event loop (needed for multiprocessing)
    asyncio.run(_run())
