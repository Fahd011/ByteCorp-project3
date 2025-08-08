#!/usr/bin/env python3

import os
import sys
import asyncio
import pandas as pd
from browser_use import Agent
from browser_use.llm import ChatOpenAI
from browser_use.browser import BrowserSession, BrowserProfile
from dotenv import load_dotenv

# Fix encoding issues on Windows
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONLEGACYWINDOWSSTDIO'] = 'utf-8'
    import io
    sys.stderr = io.StringIO()

print("=== BROWSER.PY SCRIPT STARTING ===")
print(f"Current working directory: {os.getcwd()}")
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")

# Load environment variables
load_dotenv()

# Get environment variables
CSV_FILE = os.getenv('CSV_FILE', 'creds2.csv')
CSV_CONTENT_BASE64 = os.getenv('CSV_CONTENT_BASE64', None)  # Alternative: CSV content as base64
LOGIN_URL = os.getenv('LOGIN_URL', 'https://www.google.com')
BILLING_URL = os.getenv('BILLING_URL', 'https://www.google.com')
DOWNLOADS_FOLDER = os.getenv('DOWNLOADS_FOLDER', './downloads')

print(f"CSV_FILE: {CSV_FILE}")
print(f"CSV_CONTENT_BASE64: {'Present' if CSV_CONTENT_BASE64 else 'Not present'}")
print(f"LOGIN_URL: {LOGIN_URL}")
print(f"BILLING_URL: {BILLING_URL}")
print(f"DOWNLOADS_FOLDER: {DOWNLOADS_FOLDER}")

# Read credentials
try:
    print("Reading CSV file...")
    if CSV_CONTENT_BASE64:
        # Read from base64 content
        import base64
        csv_bytes = base64.b64decode(CSV_CONTENT_BASE64)
        csv_content = csv_bytes.decode('utf-8')
        from io import StringIO
        creds = pd.read_csv(StringIO(csv_content), skipinitialspace=True)
        print(f"✓ Loaded CSV from base64 content")
    else:
        # Read from file
        creds = pd.read_csv(CSV_FILE, skipinitialspace=True)
        print(f"✓ Loaded CSV from file: {CSV_FILE}")
    
    usernames = creds['cred_username']
    passwords = creds['cred_password']
    print(f"Loaded {len(usernames)} credentials")
except Exception as e:
    print(f"Error reading CSV: {e}")
    exit(1)

print("=== BROWSER.PY SCRIPT CONFIGURED SUCCESSFULLY ===")

# Test browser_use imports
print("=== TESTING BROWSER_USE IMPORTS ===")
try:
    print("Testing browser_use import...")
    from browser_use import Agent
    print("✓ Agent imported successfully")
    
    print("Testing ChatOpenAI import...")
    from browser_use.llm import ChatOpenAI
    print("✓ ChatOpenAI imported successfully")
    
    print("Testing BrowserSession import...")
    from browser_use.browser import BrowserSession, BrowserProfile
    print("✓ BrowserSession imported successfully")
    
    print("=== ALL BROWSER_USE IMPORTS SUCCESSFUL ===")
except Exception as import_error:
    print(f"❌ BROWSER_USE IMPORT FAILED: {import_error}")
    print("This is likely why the browser window doesn't appear!")
    exit(1)


def get_latest_pdf(before_files):
    """Get the newly downloaded PDF file"""
    after_files = set(os.listdir(DOWNLOADS_FOLDER))
    new_files = after_files - before_files
    pdf_files = [f for f in new_files if f.lower().endswith('.pdf')]
    if not pdf_files:
        return None
    latest_pdf = max(pdf_files, key=lambda f: os.path.getctime(os.path.join(DOWNLOADS_FOLDER, f)))
    return latest_pdf


llm = ChatOpenAI(model="gpt-4.1-mini")

async def main():
    """Main function to run the browser automation"""
    global bill_count
    
    print("=== ENTERING MAIN FUNCTION ===")
    
    # Create downloads folder if it doesn't exist
    os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
    print(f"Downloads folder: {DOWNLOADS_FOLDER}")
    
    # Process each credential
    for index, (email, password) in enumerate(zip(usernames, passwords)):
        print(f"\n=== PROCESSING CREDENTIAL {index + 1}: {email} ===")
        
        # Create a unique profile path for this session
        unique_profile_path = f"./browser_profiles/profile_{index}_{email.replace('@', '_').replace('.', '_')}"
        os.makedirs(unique_profile_path, exist_ok=True)
        print(f"Profile path: {unique_profile_path}")
        
        # Create browser session
        print("Creating browser session...")
        try:
            from browser_use.browser import BrowserProfile, BrowserSession
            
            browser_profile = BrowserProfile(
                downloads_path=DOWNLOADS_FOLDER,
                user_data_dir=unique_profile_path,
            )
            print("✓ BrowserProfile created successfully")
            
            browser_session = BrowserSession(
                browser_profile=browser_profile,
            )
            print("✓ BrowserSession created successfully")
        except Exception as session_error:
            print(f"❌ BROWSER SESSION CREATION FAILED: {session_error}")
            print("This is why the browser window doesn't appear!")
            continue
        
        # Create LLM
        print("Creating LLM...")
        try:
            from browser_use.llm import ChatOpenAI
            llm = ChatOpenAI(model="gpt-4o-mini")
            print("✓ LLM created successfully")
        except Exception as llm_error:
            print(f"❌ LLM CREATION FAILED: {llm_error}")
            print("This is why the browser window doesn't appear!")
            continue
        
        # Create agent
        print("Creating agent...")
        try:
            from browser_use import Agent
            agent = Agent(
                task=f"Navigate to {LOGIN_URL}, login with {email} and {password}, then go to {BILLING_URL} and download the latest bill.",
                llm=llm,
                browser_session=browser_session,
                headless=False,
            )
            print("✓ Agent created successfully")
        except Exception as agent_error:
            print(f"❌ AGENT CREATION FAILED: {agent_error}")
            print("This is why the browser window doesn't appear!")
            continue
        
        print(f"Starting browser automation for {email} - Browser window should be visible!")
        print(f"Look for a Chrome window that should appear on your screen!")
        print(f"Browser window should be maximized and visible.")
        print("=" * 50)
        print("🎯 BROWSER WINDOW SHOULD APPEAR NOW!")
        print("Check your screen for a Chrome window!")
        print("If you don't see it, check:")
        print("1. Behind other windows")
        print("2. On other monitors")
        print("3. In the taskbar")
        print("=" * 50)
        
        # IMMEDIATELY open a browser window to ensure it appears
        try:
            print("Opening browser window immediately...")
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--window-position=0,0")
            
            immediate_driver = webdriver.Chrome(options=chrome_options)
            immediate_driver.get(LOGIN_URL)
            print(f"🎯 BROWSER WINDOW OPENED IMMEDIATELY FOR {email}")
            print("Browser window should be visible now!")
            
            # Keep it open for a moment
            await asyncio.sleep(3)
            immediate_driver.quit()
            print("Immediate browser window closed")
            
        except Exception as immediate_error:
            print(f"Immediate browser window failed: {immediate_error}")
        
        # Give the browser a moment to start
        await asyncio.sleep(5)  # Increased from 2 to 5 seconds
        
        print("=== ABOUT TO RUN BROWSER_USE AGENT ===")
        try:
            result = await agent.run()
            print(f"Browser automation completed for {email}")
            print(result)
        except Exception as e:
            print(f"Browser automation failed for {email}: {e}")
            print("This is likely due to OpenAI API quota limits")
            print("The browser window should still be visible")
            
            # Force open the browser_use agent window even if API fails
            try:
                print("Forcing browser_use agent window to open...")
                from browser_use import Agent
                from browser_use.llm import ChatOpenAI
                from browser_use.browser import BrowserSession, BrowserProfile
                
                # Create a simple agent that just opens the window
                simple_browser_session = BrowserSession(
                    browser_profile=BrowserProfile(
                        downloads_path=DOWNLOADS_FOLDER,
                        user_data_dir=unique_profile_path,
                    )
                )
                
                simple_llm = ChatOpenAI(model="gpt-3.5-turbo")  # Use cheaper model
                
                simple_agent = Agent(
                    task="Just open a browser window and navigate to the login page. That's all.",
                    llm=simple_llm,
                    browser_session=simple_browser_session,
                    headless=False,
                )
                
                print("Starting simple browser_use agent...")
                simple_result = await simple_agent.run()
                print("Simple browser_use agent completed")
                
            except Exception as force_error:
                print(f"Force browser_use also failed: {force_error}")
                
                # Final fallback: Open a simple browser window
                try:
                    print("Opening final fallback browser window...")
                    from selenium import webdriver
                    from selenium.webdriver.chrome.options import Options
                    
                    chrome_options = Options()
                    chrome_options.add_argument("--start-maximized")
                    chrome_options.add_argument("--no-sandbox")
                    chrome_options.add_argument("--disable-dev-shm-usage")
                    chrome_options.add_argument("--disable-gpu")
                    chrome_options.add_argument("--window-size=1920,1080")
                    chrome_options.add_argument("--window-position=0,0")
                    
                    driver = webdriver.Chrome(options=chrome_options)
                    driver.get(LOGIN_URL)
                    
                    print(f"Fallback browser window opened for {email}")
                    print("Browser window should be visible now!")
                    
                    # Keep the window open for a longer time
                    await asyncio.sleep(10)  # Increased from 5 to 10 seconds
                    driver.quit()
                    print("Fallback browser window closed")
                    
                except Exception as fallback_error:
                    print(f"Fallback browser also failed: {fallback_error}")
        
        bill_count += 1
        print(f"=== COMPLETED PROCESSING FOR {email} ===")
    
    print("=== ALL CREDENTIALS PROCESSED ===")
    print(f"Total bills processed: {bill_count}")

if __name__ == "__main__":
    print("=== BROWSER.PY MAIN BLOCK STARTING ===")
    bill_count = 0
    asyncio.run(main())
    print("=== BROWSER.PY SCRIPT COMPLETED ===")
