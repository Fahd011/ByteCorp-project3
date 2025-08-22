from browser_use import Agent, BrowserSession, BrowserProfile
from browser_use.llm import ChatOpenAI
import asyncio
import os
from datetime import datetime

# Credentials list
CREDENTIALS = [
    {"email": "billing+rtx@sagiliti.com", "password": "Collins123!!"},
    {"email": "billing+tmo_1529@sagiliti.com", "password": "Arbors1529!"},
    # Add as many as needed...
]

DOWNLOAD_DIR = r"C:\Users\malik\Downloads\DukeEnergyBills"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def run_agent_for_credential(email, password):
    # Snapshot of existing files
    initial_files = set(os.listdir(DOWNLOAD_DIR))

    # Create browser profile for this session
    browser_profile = BrowserProfile(
        headless=False,
        viewport={"width": 1920, "height": 1080},
        window_size={"width": 1920, "height": 1080},
        wait_for_network_idle_page_load_time=5.0,
        wait_between_actions=2.0,
        downloads_path=DOWNLOAD_DIR,
    )

    browser_session = BrowserSession(browser_profile=browser_profile)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    task = f"""
    1. Go to https://duke-energy.com/my-account/sign-in
    2. Sign in using email: {email} and password: {password}
    3. Wait for login to complete and dashboard to load
    4. Navigate to https://businessportal2.duke-energy.com/billinghistory
    5. Wait for "Billing & Payment Activity" to appear
    6. Click ONLY the "View Bill" button in the first row
    7. Wait for the PDF to download into {DOWNLOAD_DIR}
    8. Close the browser session
    """

    agent = Agent(
        task=task,
        llm=ChatOpenAI(model="gpt-4o"),
        browser_session=browser_session,
        max_actions_per_step=10,
    )

    await agent.run(max_steps=50)
    await asyncio.sleep(3)  # Give time for downloads

    # # Detect new files
    # new_files = set(os.listdir(DOWNLOAD_DIR)) - initial_files
    # for filename in new_files:
    #     if filename.lower().endswith(".pdf"):
    #         old_path = os.path.join(DOWNLOAD_DIR, filename)
    #         clean_email = email.replace('@', '_').replace('+', '_').replace('.', '_')
    #         new_filename = f"{clean_email}_{timestamp}.pdf"
    #         new_path = os.path.join(DOWNLOAD_DIR, new_filename)
    #         try:
    #             os.rename(old_path, new_path)
    #             print(f"[{email}] File renamed to: {new_filename}")
    #         except Exception as e:
    #             print(f"[{email}] Error renaming file: {e}")
    #     else:
    #         print(f"[{email}] Downloaded non-PDF: {filename}")


async def main():
    for cred in CREDENTIALS:
        await run_agent_for_credential(cred["email"], cred["password"])


if __name__ == "__main__":
    asyncio.run(main())
