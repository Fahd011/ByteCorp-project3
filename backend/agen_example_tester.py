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
4. After clicking sign in, DO NOT navigate further until the dashboard has fully loaded and interactive elements are visible.
5. Once the dashboard is clearly loaded, navigate to https://businessportal2.duke-energy.com/billinghistory.
6. Wait until the billing history page fully loads and billing rows are visible.
7. If "Oops, something went wrong." appears, STOP the task immediately.
8. Find the "View Bill" button in the FIRST billing row only.
9. Click the "View Bill" button in the FIRST row EXACTLY ONE TIME.
10. After clicking the View Bill button ONE TIME, wait 3 seconds for the download to start.
11. Once you have clicked the View Bill button once, the task is COMPLETE. Do not click any more buttons.
12. IMPORTANT: After one successful click on View Bill, immediately mark the task as done and stop all actions.
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