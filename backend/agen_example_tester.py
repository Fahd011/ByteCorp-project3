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
    # Enhanced browser profile with additional stability args for VMs
    browser_profile = BrowserProfile(
        headless=True,
        java_script_enabled=True,
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
            f"--download-default-directory={BILLS_DIR.absolute()}",
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
    
    try:
        result = await agent.run()
        print("Task completed!")
        print(f"Final result: {result.final_result()}")
    except Exception as e:
        print(f"Task failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(main())