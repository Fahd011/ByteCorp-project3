import os
import asyncio
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

    # Remember which files we already have
    before_files = set(os.listdir(DOWNLOAD_DIR))

    client = AsyncBrowserUse(api_key=API_KEY)

    print("[INFO] Starting remote browser task …")
    result = await client.tasks.run(task=TASK_TEMPLATE)
    print(f"[INFO] Task finished, status = {result.status}\n         output = {result.done_output}")

    # Give the remote browser a moment to finish synchronising the file
    await asyncio.sleep(5)

    # Identify newly downloaded files
    after_files = set(os.listdir(DOWNLOAD_DIR))
    new_files   = after_files - before_files

    if not new_files:
        print("[WARN] No new files detected in", DOWNLOAD_DIR)
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_email = EMAIL.replace("@", "_").replace("+", "_").replace(".", "_")

    for f in new_files:
        if f.lower().endswith(".pdf"):
            old_path = os.path.join(DOWNLOAD_DIR, f)
            new_name = f"{clean_email}_{timestamp}.pdf"
            new_path = os.path.join(DOWNLOAD_DIR, new_name)
            try:
                os.rename(old_path, new_path)
                print(f"[OK] Renamed '{f}'  →  '{new_name}'")
            except OSError as e:
                print(f"[ERROR] Could not rename '{f}': {e}")
        else:
            print(f"[SKIP] '{f}' is not a PDF – leaving unchanged")


if __name__ == "__main__":
    asyncio.run(run_duke_download())
