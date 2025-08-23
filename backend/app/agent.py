import os
import asyncio
import requests

from datetime import datetime
from typing import Dict

from browser_use_sdk import AsyncBrowserUse

# ---------------------------------------------------------------------------
# CONFIGURATION -------------------------------------------------------------
# ---------------------------------------------------------------------------
DOWNLOAD_DIR = os.path.expanduser("~/duke_bills")  # ~/duke_bills on any OS
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
        # Ensure ~/duke_bills exists
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
        client = AsyncBrowserUse(api_key=API_KEY)

        email = user_cred.get("username")
        password = user_cred.get("password")

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

        print("[INFO] Starting remote browser task …")
        result = await client.tasks.run(
            task=TASK_TEMPLATE,
        )

        # Give Cloud task a moment to finish syncing
        await asyncio.sleep(5)

        print(f"[INFO] Task finished:")
        print(f"  id                = {result.id}")
        print(f"  status            = {result.status}")
        print(f"  done_output       = {result.done_output}")
        print(f"  output_files       = {result.output_files}")
        
         # 👇 Call your helper
        await handle_task_result(result, client, email, DOWNLOAD_DIR)

    # Run the async function in a new event loop (needed for multiprocessing)
    asyncio.run(_run())



async def handle_task_result(result, client, email, DOWNLOAD_DIR):
    if hasattr(result, 'output_files') and result.output_files:
        print(f"  output_files      = {len(result.output_files)} files found")
        
        # Look for PDF files in output_files
        for output_file in result.output_files:
            file_name = getattr(output_file, 'file_name', 'unknown')
            if file_name.lower().endswith('.pdf'):
                try:
                    # Get download URL for the file
                    file_response = await client.tasks.get_output_file(
                        file_id=output_file.id, 
                        task_id=result.id
                    )
                    file_url = file_response.download_url
                    
                    # Download the file
                    response = requests.get(file_url)
                    if response.status_code == 200:
                        # Clean email for filename
                        clean_email = email.replace('@', '_').replace('+', '_').replace('.', '_')
                        
                        # Human-readable datetime for logs
                        human_time = datetime.now().strftime("%d/%m/%y %I:%M%p")
                        
                        # Safe datetime for filename
                        safe_time = datetime.now().strftime("%d-%m-%y_%I-%M%p")
                        
                        # Local filename
                        local_filename = f"{clean_email}_{safe_time}.pdf"
                        local_path = os.path.join(DOWNLOAD_DIR, local_filename)
                        
                        # Save the file
                        with open(local_path, "wb") as f:
                            f.write(response.content)
                        
                        print(f"[OK] Downloaded and saved: {local_path}")
                        print(f"[INFO] Download time: {human_time}")
                    else:
                        print(f"[ERROR] Failed to download {file_name}: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"[ERROR] Error downloading {file_name}: {e}")
            else:
                print(f"[INFO] Skipping non-PDF file: {file_name}")
    else:
        print("[INFO] No output files found in task result")
