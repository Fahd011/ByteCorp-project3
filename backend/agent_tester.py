import os
import asyncio
from browser_use_sdk import AsyncBrowserUse

from datetime import datetime


async def main():
    email = "billing+rtx@sagiliti.com"
    password = "Collins123!!"

    # ✅ Use home directory instead of root for downloads
    download_dir = os.path.expanduser("~/duke_bills")
    os.makedirs(download_dir, exist_ok=True)

    initial_files = set(os.listdir(download_dir))

    client = AsyncBrowserUse(
        api_key=os.environ.get("BROWSER_USE_API_KEY","bu_7xpa6a_pYy1Xz1mspGw0azXf_9EOZk_IVHwZh-5UVKM"),  # This is the default and can be omitted
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    task = f"""
    1. Go to https://duke-energy.com/my-account/sign-in
    2. Wait for the page to fully load (be patient, this website is slow)
    3. Sign in using email: {email} and password: {password}
    4. Wait for login to complete and dashboard to load completely
    5. Navigate to https://businessportal2.duke-energy.com/billinghistory
    6. IMPORTANT: Wait patiently for the billing history page to load completely
    7. Check the page content:
       - If you see "Oops, something went wrong." message, IMMEDIATELY stop the task
       - If you see other error messages, refresh the page and wait again
       - Keep waiting until you see "Billing & Payment Activity" text on the page
    8. Once the billing history table is visible, find the first row in the billing table
    9. Click ONLY on the "View Bill" button in the FIRST row of the table
    10. Wait for the bill to download
    11. The bill should be saved automatically
    """

    result = await client.tasks.run(task=task)

    print(f"Task completed with status: {result.status}")
    print(f"Task output: {result.done_output}")

    await asyncio.sleep(3)

    current_files = set(os.listdir(download_dir))
    new_files = current_files - initial_files

    if new_files:
        for filename in new_files:
            if filename.lower().endswith('.pdf'):
                old_path = os.path.join(download_dir, filename)
                clean_email = email.replace('@', '_').replace('+', '_').replace('.', '_')
                new_filename = f"{clean_email}_{timestamp}.pdf"
                new_path = os.path.join(download_dir, new_filename)

                try:
                    os.rename(old_path, new_path)
                    print(f"File renamed from '{filename}' to '{new_filename}'")
                except Exception as e:
                    print(f"Error renaming file: {e}")
            else:
                print(f"Downloaded file '{filename}' is not a PDF")
    else:
        print("No new files detected in download directory")

asyncio.run(main())