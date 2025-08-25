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
DOWNLOAD_DIR = Path(os.path.expanduser("~/duke_bills"))

# Create download directory if it doesn't exist
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

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
            f"--download-default-directory={DOWNLOAD_DIR}",
            "--window-size=1920,1080",  # Set explicit window size
            "--disable-extensions",  # Disable extensions for stability
            "--no-first-run",  # Skip first run setup
            "--disable-default-apps",  # Disable default apps
        ],
        wait_between_actions=2.0,  # Increase wait time between actions
    )

    # Create browser session with enhanced error handling
    browser_session = BrowserSession(
        browser_profile=browser_profile,
        keep_alive=True,  # Keep browser alive for better stability
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
    print(f"Downloads will be saved to: {DOWNLOAD_DIR}")
    
    try:
        result = await agent.run()
        print("Task completed!")
        print(f"Final result: {result.final_result()}")
    except Exception as e:
        print(f"Task failed with error: {e}")
    finally:
        # Ensure browser session is properly closed
        await browser_session.stop()

if __name__ == "__main__":
    asyncio.run(main())