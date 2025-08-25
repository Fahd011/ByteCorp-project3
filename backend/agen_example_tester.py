import asyncio
import os
import calendar


from pathlib import Path
from datetime import datetime
from browser_use import Agent, BrowserSession, BrowserProfile
from browser_use.llm import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

from azure_storage_service import azure_storage_service

# ---------------------------------------------------------------------------
# CONFIGURATION -------------------------------------------------------------
# ---------------------------------------------------------------------------
EMAIL = "billing+rtx@sagiliti.com"
PASSWORD = "Collins123!!"
BILLS_DIR = Path("bills")
BILLS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# MAIN TASK -----------------------------------------------------------------
# ---------------------------------------------------------------------------
TASK_TEMPLATE = f"""
1. Go to https://duke-energy.com/my-account/sign-in.
2. Wait for the login page to fully load.
3. Log in with:
    • email    : {EMAIL}
    • password : {PASSWORD}
4. After clicking sign in, wait until the dashboard has fully loaded.
5. Navigate to https://businessportal2.duke-energy.com/billinghistory.
6. Wait until the billing history page fully loads and billing rows are visible.
7. If "Oops, something went wrong." appears, STOP the task immediately.
8. Find the "View Bill" button in the FIRST billing row.
9. Click the "View Bill" button in the FIRST row EXACTLY ONE TIME.
10. After clicking once, wait 3 seconds for the download to complete.
11. TASK IS NOW COMPLETE. Do not click any more buttons or take any more actions.
12. Use the 'done' action to mark the task as finished with message "Successfully downloaded one bill".
"""

async def main():
    # Use downloads_path instead of Chrome args
    browser_profile = BrowserProfile(
        headless=True,
        java_script_enabled=True,
        downloads_path=BILLS_DIR.absolute(),  # Use the proper downloads_path parameter
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
    print(f"Downloads will be saved to: {BILLS_DIR.absolute()}")
    
    # Track initial files in the bills directory before agent runs
    download_path = BILLS_DIR
    initial_files = set(os.listdir(download_path))

    try:
        result = await agent.run()
        print("Task completed!")
        print(f"Final result: {result.final_result()}")

        # Give the remote browser a moment to finish synchronising the file
        await asyncio.sleep(5)

        bill_files = list(download_path.glob("*.pdf")) + list(download_path.glob("*.PDF"))

        # Bills were downloaded successfully!
        print(f"✅ Bills found: {len(bill_files)} files downloaded for user: {EMAIL}")
        # Detect new files
        new_files = set(os.listdir(download_path)) - initial_files
        
        clean_email = EMAIL.replace('@', '_').replace('+', '_').replace('.', '_')

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
                credential_id ="d4d5dcbc-d66e-498f-b3d5-82d5e4bb1b9d"

                try:
                    uploaded_blob_name = azure_storage_service.upload_pdf_to_azure(
                        pdf_content=pdf_content,
                        email=EMAIL,
                        original_filename=blob_name
                    )

                    if uploaded_blob_name:
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

if __name__ == "__main__":
    asyncio.run(main())