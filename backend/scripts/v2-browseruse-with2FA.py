import requests
import json
import time
import re
import os
from dotenv import load_dotenv
import getpass

load_dotenv()
# --- Configuration ---
YOUR_API_KEY = os.getenv("BROWSER_USE_API_KEY")
YOUR_SIGNIN_URL = "https://myaccount.denverwater.org/"
YOUR_EMAIL = os.getenv("USER_EMAIL")
if not YOUR_EMAIL:
    YOUR_EMAIL = input("Enter your email/username: ").strip()

YOUR_PASSWORD = os.getenv("USER_PASSWORD")
if not YOUR_PASSWORD:
    YOUR_PASSWORD = getpass.getpass("Enter your password: ")

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = "+16122875488"
TWILIO_TARGET_MESSAGE_SID = os.getenv("TWILIO_TARGET_MESSAGE_SID")

# 3. TASK 1: This prompt logs in and stops at the 2FA page
TASK_1_PROMPT = """
1. Wait for the login page to fully load.
2. Find and fill the username/email field with the secret 'my_email'.
3. Find and fill the password field with the secret 'my_pass'.
4. Click the sign-in/login button.
5. Wait for the 2FA verification page to appear (look for a verification code input field).
6. Once you see the 2FA input field, use the 'done' action with output: "Ready for 2FA code."
"""

# 4. TASK 2: This prompt submits the 2FA code
TASK_2_PROMPT = """
The browser is now on the 2FA page.
1. Find the 2FA code input field.
2. Fill it with the secret 'my_otp'.
3. Find and click the 'Submit' or 'Verify' button.
4. Wait for the page to load and confirm login.
5. Use the 'done' action with output: "Login successful!"
"""
# ---------------------

def get_message_by_sid(message_sid):
    """Fetch a single SMS message from Twilio by SID."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print("[ERROR] Twilio credentials not set.")
        return None

    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages/{message_sid}.json"
        response = requests.get(url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Failed to fetch message by SID: {e}")
        return None

def extract_code_from_message_body(message_body):
    """Extract a verification code from a Twilio message body."""
    if not message_body:
        return None

    code_patterns = [
        r'\b(\d{6})\b',  # 6-digit code
        r'\b(\d{5})\b',  # 5-digit code
        r'\b(\d{4})\b',  # 4-digit code
        r'\b(\d{8})\b',  # 8-digit code
    ]

    for pattern in code_patterns:
        match = re.search(pattern, message_body)
        if match:
            return match.group(1)
    return None

def get_latest_sms_code(max_wait_seconds=60, check_interval=3):
    """Fetch the latest SMS verification code from Twilio."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print("[ERROR] Twilio credentials not set.")
        return None

    # Fast path: explicit message SID provided
    if TWILIO_TARGET_MESSAGE_SID:
        direct_message = get_message_by_sid(TWILIO_TARGET_MESSAGE_SID)
        if direct_message:
            body = direct_message.get('body', '')
            code = extract_code_from_message_body(body)
            if code:
                print(f"[SUCCESS] Found verification code: {code}")
                return code
            else:
                print(f"[WARNING] No code in message SID {TWILIO_TARGET_MESSAGE_SID}")

    print(f"[INFO] Waiting for 2FA code on {TWILIO_PHONE_NUMBER}...")
    start_time = time.time()
    last_message_sid = None

    while time.time() - start_time < max_wait_seconds:
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
            params = {'To': TWILIO_PHONE_NUMBER, 'PageSize': 5}

            response = requests.get(url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), params=params)
            response.raise_for_status()

            messages = response.json().get('messages', [])

            if messages:
                latest_message = messages[0]
                message_sid = latest_message.get('sid')
                message_body = latest_message.get('body', '')

                if message_sid != last_message_sid:
                    print(f"[INFO] New message received: {message_body[:50]}...")
                    code = extract_code_from_message_body(message_body)
                    if code:
                        print(f"[SUCCESS] Found verification code: {code}")
                        return code
                    last_message_sid = message_sid

            elapsed = int(time.time() - start_time)
            print(f"[INFO] Waiting for 2FA code... ({elapsed}/{max_wait_seconds}s)")
            time.sleep(check_interval)

        except Exception as e:
            print(f"[ERROR] Error fetching SMS: {e}")
            time.sleep(check_interval)

    print("[WARNING] Timeout waiting for 2FA code")
    return None

def create_persistent_session(api_key, start_url):
    """
    Creates a new PERSISTENT session that stays open between tasks.
    This is the key fix.
    """
    session_url = "https://api.browser-use.com/api/v2/sessions"
    headers = {
        "X-Browser-Use-API-Key": api_key,
        "Content-Type": "application/json"
    }
    payload = {"startUrl": start_url}
    
    try:
        response = requests.post(session_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        session_data = response.json()
        session_id = session_data.get("id")
        live_url = session_data.get("liveUrl")
        
        if session_id:
            print(f"Persistent session created (ID: {session_id})")
            if live_url:
                print(f"\n--- You can watch the agent live at: {live_url} ---\n")
            return session_id, live_url
        else:
            print("Failed to create persistent session, 'id' not in response.")
            return None, None
            
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while creating session: {http_err}")
        print(f"Response content: {http_err.response.text}")
        return None, None
    except Exception as err:
        print(f"An error occurred while creating session: {err}")
        return None, None

def create_task(api_key, task_prompt, session_id, secrets=None):
    """
    Creates a new task INSIDE an existing session.
    """
    create_task_url = "https://api.browser-use.com/api/v2/tasks"
    headers = {
        "X-Browser-Use-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "task": task_prompt,
        "sessionId": session_id, # This is mandatory
        "secrets": secrets or {}
    }
    
    try:
        response = requests.post(create_task_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while creating task: {http_err}")
        print(f"Response content: {http_err.response.text}")
        return None
    except Exception as err:
        print(f"An error occurred while creating task: {err}")
        return None

def wait_for_task_to_finish(api_key, task_id, poll_interval=3):
    """Polls the task status until it's 'finished' or 'stopped'."""
    get_task_url = f"https://api.browser-use.com/api/v2/tasks/{task_id}"
    headers = {"X-Browser-Use-API-Key": api_key}
    
    print(f"Waiting for Task (ID: {task_id}) to finish...")
    
    while True:
        try:
            response = requests.get(get_task_url, headers=headers)
            response.raise_for_status()
            
            task_data = response.json()
            status = task_data.get("status")
            
            if status == "finished":
                print(f"Task finished.")
                print(f"Task output: {task_data.get('output')}\n")
                return True
            elif status == "stopped":
                print(f"Task stopped.\n")
                return False
            elif status == "created" or status == "started" or status == "paused":
                print(f"Task status is '{status}'. Waiting...")
                time.sleep(poll_interval)
            else:
                print(f"Unknown task status: {status}")
                return False
                
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred while polling task: {http_err}")
            print(f"Response content: {http_err.response.text}")
            return False
        except Exception as err:
            print(f"An error occurred while polling task: {err}")
            return False

# --- Main Script ---
if __name__ == "__main__":
    if YOUR_API_KEY == "<apiKey>" or YOUR_SIGNIN_URL == "{signin_url}":
        print("Error: Please fill in your API key, sign-in URL, email, and password at the top of the script.")
    else:
        
        # === STEP 1: Create a Persistent Session ===
        print("Creating persistent session...")
        session_id, live_url = create_persistent_session(YOUR_API_KEY, YOUR_SIGNIN_URL)
        
        if session_id:
            # === STEP 2: Run the First Task (Login) ===
            print("Starting Task 1: Logging in...")
            login_secrets = {
                "my_email": YOUR_EMAIL,
                "my_pass": YOUR_PASSWORD
            }
            
            task1_data = create_task(
                YOUR_API_KEY, 
                TASK_1_PROMPT, 
                session_id=session_id, 
                secrets=login_secrets
            )
            
            if task1_data and "id" in task1_data:
                task1_id = task1_data["id"]
                print(f"Task 1 created (ID: {task1_id})")
                
                # === STEP 3: Wait for Task 1 to Finish ===
                task1_succeeded = wait_for_task_to_finish(YOUR_API_KEY, task1_id)
                
                if task1_succeeded:
                    # === STEP 4: Fetch 2FA code from Twilio ===
                    print("\nFetching 2FA code from Twilio...")
                    otp_code = get_latest_sms_code(max_wait_seconds=90)
                    
                    if not otp_code:
                        print("Failed to retrieve 2FA code. Aborting.")
                        exit(1)
                    
                    print(f"Retrieved 2FA code: {otp_code}")
                    
                    # === STEP 5: Run the Second Task (Submit 2FA) ===
                    print("\nSending Task 2: Submitting 2FA code...")
                    otp_secrets = {"my_otp": otp_code}
                    
                    task2_data = create_task(
                        YOUR_API_KEY,
                        TASK_2_PROMPT,
                        session_id=session_id,  # <-- Re-using the same session
                        secrets=otp_secrets
                    )
                    
                    if task2_data:
                        task2_id = task2_data["id"]
                        print(f"Task 2 created (ID: {task2_id}). Agent is completing login.")
                        if live_url:
                             print(f"You can keep watching at the same live URL.")
                        
                        # (Optional) Wait for Task 2 to finish
                        # print("\nWaiting for Task 2 to complete...")
                        # wait_for_task_to_finish(YOUR_API_KEY, task2_id)
                        
                        print("\nAll tasks submitted.")
                else:
                    print("Task 1 (Login) did not finish successfully. Aborting.")
            else:
                print("Failed to create Task 1.")
        else:
            print("Failed to create persistent session. Aborting.")