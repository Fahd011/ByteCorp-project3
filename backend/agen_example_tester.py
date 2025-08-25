import asyncio
import os
from pathlib import Path
from browser_use import Agent, BrowserSession, BrowserProfile
from browser_use.llm import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

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
2. Log in using:
   - Email: {EMAIL}
   - Password: {PASSWORD}
3. Wait for the dashboard to load. Only then proceed to the next step.
4. Then go to this url: https://businessportal2.duke-energy.com/billinghistory
5. On the billing history page:
   - download only download the first bill
6. Wait at least 5 seconds after clicking to ensure the download is triggered.
7. Now, go to the top right corner of the page.
   - Click the user icon (showing {EMAIL}).
   - Select "Sign out" from the dropdown.
8. Confirm that you are signed out:
   - You should be redirected to the **main homepage**.
   - After reaching the homepage and confirming logout, do not click or navigate anywhere.
     The task is finished. Do not revisit any links or pages after logout. Do not open new tabs.
9. If you see a page that says "Something went wrong", stop the task.
Important:
- Do not revisit the billing history page after logout.
- Do not click on "Pay My Bill" or similar options.
- If no elements are interactable, wait 5 seconds — the page might still be loading. Repeat until page has loaded
- Only download 1 pdf. Never more than 1
"""

async def main():
    # Enhanced browser profile with additional stability args for VMs
    browser_profile = BrowserProfile(
        headless=True,
        java_script_enabled=True,  # Ensure JavaScript is enabled
        args=[
            "--no-sandbox", 
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",  # Overcome limited resource problems
            "--disable-gpu",  # Applicable to Windows
            "--disable-web-security",  # Disable web security for better compatibility
            "--disable-features=VizDisplayCompositor",  # Disable compositor
            "--disable-background-timer-throttling",  # Prevent background throttling
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-field-trial-config",
            "--disable-ipc-flooding-protection",
            f"--download-default-directory={BILLS_DIR.absolute()}",  # Use absolute path
            "--window-size=1920,1080",  # Set explicit window size
            "--disable-extensions",  # Disable extensions for stability
            "--no-first-run",  # Skip first run setup
            "--disable-default-apps",  # Disable default apps
        ],
        wait_between_actions=2.0,  # Increase wait time between actions
    )

    # Create browser session
    browser_session = BrowserSession(
        browser_profile=browser_profile,
    )

    # Create agent with the Duke Energy task
    agent = Agent(
        task=TASK_TEMPLATE,
        llm=ChatOpenAI(model="gpt-4o-mini"),
        browser_session=browser_session,
        max_failures=5,  # Allow more failures before giving up
        retry_delay=3,  # Longer retry delay
    )

    # Run the agent
    print(f"Starting Duke Energy billing task...")
    print(f"Downloads will be saved to: {BILLS_DIR.absolute()}")
    
    try:
        result = await agent.run()
        print("Task completed!")
        print(f"Final result: {result.final_result()}")
    except Exception as e:
        print(f"Task failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(main())