import os
import asyncio
import requests
from datetime import datetime

from browser_use_sdk import AsyncBrowserUse

# ---------------------------------------------------------------------------
# CONFIGURATION -------------------------------------------------------------
# ---------------------------------------------------------------------------
EMAIL    = "billing+rtx@sagiliti.com"
PASSWORD = "Collins123!!"
DOWNLOAD_DIR = os.path.expanduser("~/duke_bills")  # ~/duke_bills on any OS
API_KEY  = os.environ.get(
    "BROWSER_USE_API_KEY",
    "bu_7xpa6a_pYy1Xz1mspGw0azXf_9EOZk_IVHwZh-5UVKM",
)

# ---------------------------------------------------------------------------
# MAIN TASK -----------------------------------------------------------------
# ---------------------------------------------------------------------------
TASK_TEMPLATE = f"""
1. Go to https://duke-energy.com/my-account/sign-in
2. Wait for the page to fully load (this site is slow)
3. Log-in with:
     • email    : {EMAIL}
     • password : {PASSWORD}
4. Wait until dashboard finishes loading
5. Navigate to https://businessportal2.duke-energy.com/billinghistory
6. Wait until the text \"Billing & Payment Activity\" is visible
7. If \"Oops, something went wrong.\" appears, STOP the task
8. Click only the \"View Bill\" button in the FIRST row
9. Wait until the bill PDF finishes downloading
"""


async def run_duke_download():
    # Ensure ~/duke_bills exists
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    client = AsyncBrowserUse(api_key=API_KEY)

    print("[INFO] Starting remote browser task …")
    result = await client.tasks.run(
        task=TASK_TEMPLATE,
    )

   

    # Give the remote browser a moment to finish synchronising the file
    await asyncio.sleep(5)
    
    
    print(f"[INFO] Task finished:")
    print(f"  id                = {result.id}")
    print(f"  status            = {result.status}")
    print(f"  done_output       = {result.done_output}")
    print(f"  output_files       = {result.output_files}")
    
    # Check if there are any output files
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
                        # Create filename with timestamp
                        clean_email = EMAIL.replace('@', '_').replace('+', '_').replace('.', '_')
                        local_filename = f"{clean_email}_{timestamp}.pdf"
                        local_path = os.path.join(DOWNLOAD_DIR, local_filename)
                        
                        # Save the file
                        with open(local_path, "wb") as f:
                            f.write(response.content)
                        
                        print(f"[OK] Downloaded and saved: {local_path}")
                    else:
                        print(f"[ERROR] Failed to download {file_name}: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"[ERROR] Error downloading {file_name}: {e}")
            else:
                print(f"[INFO] Skipping non-PDF file: {file_name}")
    else:
        print("[INFO] No output files found in task result")


if __name__ == "__main__":
    asyncio.run(run_duke_download())
