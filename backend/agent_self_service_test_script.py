import os
from pathlib import Path
import asyncio
import uuid
from datetime import datetime

from browser_use.browser import BrowserSession, BrowserProfile
from browser_use.llm import ChatOpenAI
from browser_use import Agent

# ---------------------------------------------------------------------------
# CONFIGURATION -------------------------------------------------------------
# ---------------------------------------------------------------------------
EMAIL    = "billing+rtx@sagiliti.com"
PASSWORD = "Collins123!!"
DOWNLOAD_DIR = Path(os.path.expanduser("~/duke_bills"))  # ~/duke_bills as Path object

# ---------------------------------------------------------------------------
# MAIN TASK -----------------------------------------------------------------
# ---------------------------------------------------------------------------
TASK_TEMPLATE = f"""
1. Go to https://duke-energy.com/my-account/sign-in.
2. Wait for the login page to fully load.
3. Log in with:
    • email    : {EMAIL}
    • password : {PASSWORD}
4. After clicking sign in, DO NOT navigate further until the dashboard has fully loaded and interactive elements are visible.
5. Once the dashboard is clearly loaded, navigate to https://businessportal2.duke-energy.com/billinghistory.
6. Wait until the billing history page fully loads and billing rows are visible.
7. If "Oops, something went wrong." appears, STOP the task
8. Find the "View Bill" button in the FIRST billing row.
9. Click the "View Bill" button in the FIRST row EXACTLY ONE TIME.
10. After clicking once and seeing a download notification, the task is COMPLETE. STOP immediately.
11. SUCCESS = One click on first row View Bill button + one PDF downloaded. DO NOT CLICK AGAIN.
"""


# Initialize LLM
llm = ChatOpenAI(model="gpt-4.1-mini")


async def run_duke_download():
    # Ensure ~/duke_bills exists
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create unique profile path for this session
    unique_profile_path = f'/tmp/browser_profiles/{uuid.uuid4()}'
    os.makedirs(unique_profile_path, exist_ok=True)
    
    download_path = DOWNLOAD_DIR / str(datetime.now().year) / datetime.now().strftime("%B")
    download_path.mkdir(parents=True, exist_ok=True)
    initial_files = set(os.listdir(download_path))

      # Create browser session with bills folder as downloads path
    browser_session = BrowserSession(
        browser_profile=BrowserProfile(
            downloads_path=str(download_path),  # Downloads go directly to bills folder
            user_data_dir=unique_profile_path,
            headless=True,  # Show browser window
            viewport={"width": 1920, "height": 1080},  # Full screen size
            window_size={"width": 1920, "height": 1080},  # Browser window size
            wait_for_network_idle_page_load_time=5.0,  # Increased wait time for slow pages
            wait_between_actions=2.0,  # Wait 2 seconds between actions
        )
    )
    
                    # Create the agent with the actual task
    agent = Agent(
        task=TASK_TEMPLATE,
        llm=llm,
        browser_session=browser_session,
        max_steps=15,  # Limit total steps to prevent excessive actions
        args=["--start-maximized"],
    )
    
    # Run the async agent in the current event loop
    result = await agent.run()


    # Give the remote browser a moment to finish synchronising the file
    await asyncio.sleep(5)
    
    bill_files = list(download_path.glob("*.pdf")) + list(download_path.glob("*.PDF"))
    
    # Bills were downloaded successfully!
    print(f"✅ Bills found: {len(bill_files)} files downloaded for user: {EMAIL}")
    # Detect new files
    new_files = set(os.listdir(download_path)) - initial_files
    
    if new_files:
        for file in new_files:
            print(f"  - New file: {file}")
    
    print(f"[INFO] Task finished:")


if __name__ == "__main__":
    asyncio.run(run_duke_download())
