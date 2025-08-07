from browser_use.llm import ChatOpenAI
from browser_use import Agent
from dotenv import load_dotenv
from browser_use.browser import BrowserSession, BrowserProfile
import pandas as pd
import asyncio
import os
import uuid

load_dotenv()
bill_count = 0

llm = ChatOpenAI(model="gpt-4.1-mini")

creds = pd.read_csv('creds2.csv', skipinitialspace=True)
usernames = creds['cred_username']
passwords = creds['cred_password']
loginURL = 'https://duke-energy.com/my-account/sign-in'
billingURL = 'https://businessportal2.duke-energy.com/billinghistory'

for email, password in zip(usernames, passwords):
    
    async def main(email, password, bill_count):
        # Unique user data dir to isolate sessions
        unique_profile_path = f'/tmp/browser_profiles/{uuid.uuid4()}'
        os.makedirs(unique_profile_path, exist_ok=True)

        browser_session = BrowserSession(
            browser_profile=BrowserProfile(
                downloads_path=os.path.expanduser('~/Downloads'),
                user_data_dir=unique_profile_path,
            )
        )

        agent = Agent(
            task = f"""
1. Go to {loginURL}.
2. Log in using:
   - Email: {email}
   - Password: {password}
3. After successful login, go to "Billing and Payment Activity".
   - If unsure, navigate directly to {billingURL}.
4. On the billing history page:
   - Find the first "View Bill" button.
   - Click it to download the bill (the download may happen silently).
5. Wait at least 5 seconds after clicking to ensure the download is triggered.
6. Now, go to the top right corner of the page.
   - Click the user icon (showing {email}).
   - Select "Sign out" from the dropdown.
7. Confirm that you are signed out:
   - You should be redirected to the **main homepage**.
   - After reaching the homepage and confirming logout, do not click or navigate anywhere. 
     The task is finished. Do not revisit any links or pages after logout. Do not open new tabs..
8. If you see a page that says “Something went wrong”, stop the task.

Important:
- Do not revisit the billing history page after logout.
- Do not click on “Pay My Bill” or similar options.
- If no elements are interactable, wait 5 seconds — the page might still be loading. Repeat until page has loaded
- Only download 1 pdf. Never more than 1
""",
            llm=llm,
            browser_session=browser_session,
            headless=True,
        )

        result = await agent.run()
        print(result)
        bill_count += 1

    asyncio.run(main(email, password, bill_count))
