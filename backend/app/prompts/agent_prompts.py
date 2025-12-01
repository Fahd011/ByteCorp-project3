"""
Provider-specific prompts for browser automation tasks
"""

PROVIDER_PROMPTS = {
    "duke_energy": {
        "task1_login": """
            1. Go to {signin_url}
            2. Wait for the page to fully load (this site is slow)
            3. If you don't see the login page, click the sign in button on the top right of the page
            4. Log-in with email: {email} and password: {password}
            5. Click the "Verify you are human" checkbox and wait until it is checked and says success
            6. Click the sign-in/login button
            7. Wait for the 2FA verification page to appear (look for a verification code input field)
            8 If you are redirected to the home page, go to https://businessportal2.duke-energy.com/BusinessDashboard and stop the task with status "Successfully logged in"
            9. If you are on the disambiguation page, STOP the task with status "Successfully logged in"
            10. If you see the dashboard or the home page, STOP the task with status "Successfully logged in"
            11. Once you see the 2FA code input field, use the 'done' action with output: "Ready for 2FA code"
            """,
        "task2_2fa": """
            The browser is now on the 2FA page. If you see the dashboard or the home page, STOP the task with status "2FA completed" otherwise continue with the following steps:
            1. Find the 2FA/verification code input field
            2. Fill it with the code: {otp_code}
            3. Click the Submit or Verify button
            4. Wait for the dashboard to load and is visible
            5. Use the 'done' action with output: "2FA completed"
            """,
        "task3_download": """
            1. If you are on the disambiguation page, select Business 
            2. Wait until the dashboard is loaded and visible, DO NOT MOVE TO STEP 3 UNTIL YOU SEE THE DASHBOARD. Wait for 10 seconds and check again if necessary.
            3. Click on "Billing" and Select "Billing & Payment Activity"
            4. Wait until the text "Billing & Payment Activity" is visible
            5. If "Oops, something went wrong." appears, STOP the task with status "Failed"
            6. Click only the "View Bill" button in the FIRST row
            7. Wait until the bill PDF finishes downloading
            8. Use the 'done' action with output: "Successfully downloaded one bill"
            """
    },
    "centerpoint_energy": {
        "task1_login": """
            1. Go to {signin_url}
            2. Wait for the page to fully load (this site is slow)
            4. Log-in with email: {email} and password: {password}
            5. Select email and get click continue 
            6. If you see the dashboard or the home page, STOP the task with status "Successfully logged in"
            7. If you see the 2FA code input field, use the 'done' action with output: "Ready for 2FA code"
            """,
        "task2_2fa": """
            The browser is now on the 2FA page. If you see the dashboard or the home page, STOP the task with status "2FA completed" otherwise continue with the following steps:
            1. Find the 2FA/verification code input field
            2. Fill it with the code: {otp_code}
            3. Click the Submit or Verify button
            4. Wait for the dashboard to load and is visible
            5. Use the 'done' action with output: "2FA completed"
            """,
        "task3_download": """
            1. expand the first account accordion
            2. Click on view bill
            3. A new window will pop up showing the bill in a pdf viewer
            4. Click the download button 
            7. Wait until the bill PDF finishes downloading
            8. Use the 'done' action with output: "Successfully downloaded one bill"
            """,
    },
    "xcel_energy": """
        1. Go to {signin_url}
        2. Wait for the page to fully load (this site is slow)
        3. Log-in with:
        • email : {email}
        • password : {password}
        4. If unable to login, STOP the task with status "Failed"
        5. Wait until the Billing Accounts text is visible. If not, wait 5 seconds and check again.
        6. Navigate to {billing_history_url}
        7. Wait until the text "Billing History" is visible and navigate to the statements tab
        8. If "Oops, something went wrong." appears, STOP the task with status "Failed"
        9. Click only the download button in the FIRST row
        10. Wait until the bill PDF finishes downloading
        11. Use the 'done' action to mark the task as finished with message "Successfully downloaded one bill"
        """,
    "green_mountain_energy": """
        1. Go to {signin_url}
        2. Wait for the page to fully load (this site is slow)
        3. Log-in with:
        • email : {email}
        • password : {password}
        4. If unable to login, STOP the task with status "Failed"
        5. Click first account number
        6. Click on the invoice number to download the pdf
        7. Wait until the bill PDF finishes downloading
        8. Use the 'done' action with output: "Successfully downloaded one bill"
        """,
}

def get_provider_prompt(provider_name: str, task_step: str = None) -> str:
    """
    Get the appropriate prompt for a provider based on the provider name.
    For Duke Energy and CenterPoint Energy, task_step can be: 'task1_login', 'task2_2fa', 'task3_download'
    For other providers, task_step is ignored and single prompt is returned.
    
    Args:
        provider_name: Name of the provider
        task_step: Which task step for Duke Energy (task1_login, task2_2fa, task3_download)
        
    Returns Duke Energy prompt as default if provider not found.
    """
    # Normalize provider name to match our keys
    provider_key = provider_name.lower().replace(" ", "_").replace("-", "_")
    
    # Handle common variations
    if "duke" in provider_key:
        provider_key = "duke_energy"
    elif "xcel" in provider_key:
        provider_key = "xcel_energy"
    elif "centerpoint" in provider_key:
        provider_key = "centerpoint_energy"
    elif "green_mountain" in provider_key:
        provider_key = "green_mountain_energy"
    
    prompt_data = PROVIDER_PROMPTS.get(provider_key, PROVIDER_PROMPTS["duke_energy"])
    
    # If Duke Energy and task_step specified, return specific task
    if provider_key in ["duke_energy", "centerpoint_energy"] and task_step and isinstance(prompt_data, dict):
        return prompt_data.get(task_step, prompt_data.get("task1_login"))
    
    # For providers with dict structure but no task_step, return task1 for backward compatibility
    if isinstance(prompt_data, dict):
        return prompt_data.get("task1_login")
    
    return prompt_data