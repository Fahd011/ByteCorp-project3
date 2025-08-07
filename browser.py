from browser_use.llm import ChatOpenAI
from browser_use import Agent
from dotenv import load_dotenv
from browser_use.browser import BrowserSession, BrowserProfile
import pandas as pd
import asyncio
import os
import uuid
import time
from datetime import datetime

load_dotenv()
bill_count = 0

llm = ChatOpenAI(model="gpt-4.1-mini")

# === CHANGE THESE PER WEBSITE ===
CSV_FILE = 'creds2.csv'
LOGIN_URL = 'https://duke-energy.com/my-account/sign-in'
BILLING_URL = 'https://businessportal2.duke-energy.com/billinghistory'
DOWNLOADS_FOLDER = os.path.expanduser('~/Downloads')

creds = pd.read_csv(CSV_FILE, skipinitialspace=True)
usernames = creds['cred_username']
passwords = creds['cred_password']


def get_latest_pdf(before_files):
    """Get the newly downloaded PDF file"""
    after_files = set(os.listdir(DOWNLOADS_FOLDER))
    new_files = after_files - before_files
    pdf_files = [f for f in new_files if f.lower().endswith('.pdf')]
    if not pdf_files:
        return None
    latest_pdf = max(pdf_files, key=lambda f: os.path.getctime(os.path.join(DOWNLOADS_FOLDER, f)))
    return latest_pdf


for email, password in zip(usernames, passwords):

    async def main(email, password, login_url, billing_url, bill_count):
        unique_profile_path = f'/tmp/browser_profiles/{uuid.uuid4()}'
        os.makedirs(unique_profile_path, exist_ok=True)

        browser_session = BrowserSession(
            browser_profile=BrowserProfile(
                downloads_path=DOWNLOADS_FOLDER,
                user_data_dir=unique_profile_path,
            )
        )

        # Record files in Downloads before download
        before_files = set(os.listdir(DOWNLOADS_FOLDER))

        agent = Agent(
            task = f"""
You are automating the process of downloading a billing document from a user's account on a website.

Steps:
1. Open the login page: {login_url}
2. Sign in using:
   - Username/Email: {email}
   - Password: {password}
3. After successful login, navigate to the billing section of the site:
   - Open this page: {billing_url}
4. On the billing page:
   - Locate the most recent or topmost bill available.
   - Click the associated download/view button (PDF download expected).
   - The download may occur silently.
   - Wait at least 5 seconds after clicking to allow the download to complete.
5. After downloading:
   - Locate the user menu (typically a profile icon or username).
   - Click it and select the option to log out or sign out.
6. Confirm that the logout was successful:
   - You should be redirected to the homepage or login screen.
7. Stop the task if any error page appears (like “Something went wrong”).

Rules:
- Do NOT download more than one bill per user.
- Do NOT navigate to payment or other pages.
- Do NOT interact with any element after logout.
- If an element is unclickable or loading, wait a few seconds before retrying.
- If logout fails or cannot be confirmed, stop the task.

Behave like a careful, responsible human user. Avoid clicking suspicious or irrelevant elements. Do not open new tabs.
""",
            llm=llm,
            browser_session=browser_session,
            headless=True,
        )

        result = await agent.run()
        print(result)
        bill_count += 1

        # === Rename the downloaded file
        time.sleep(5)  # Buffer to ensure the download finishes
        downloaded_file = get_latest_pdf(before_files)

        if downloaded_file:
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            safe_email = email.replace('@', '_at_')  # to avoid illegal characters in filename
            new_name = f"{safe_email}-{password}-{timestamp}.pdf"
            old_path = os.path.join(DOWNLOADS_FOLDER, downloaded_file)
            new_path = os.path.join(DOWNLOADS_FOLDER, new_name)
            os.rename(old_path, new_path)
            print(f"Renamed downloaded bill to: {new_name}")
        else:
            print("⚠️ No new PDF file was found after agent run.")

    asyncio.run(main(email, password, LOGIN_URL, BILLING_URL, bill_count))
