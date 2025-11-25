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
8. If you see the dashboard or the home page, STOP the task with status "Successfully logged in"
9. Once you see the 2FA code input field, use the 'done' action with output: "Ready for 2FA code"
""",
        "task2_2fa": """
The browser is now on the 2FA page. If you see the dashboard or the home page, STOP the task with status "2FA completed" otherwise continue with the following steps:
1. Find the 2FA/verification code input field
2. Fill it with the code: {otp_code}
3. Click the Submit or Verify button
4. Wait for the dashboard to load
5. Use the 'done' action with output: "2FA completed"
""",
        "task3_download": """
1. Navigate to {billing_history_url}
2. Wait until the text "Billing & Payment Activity" is visible
3. If "Oops, something went wrong." appears, STOP the task with status "Failed"
4. Click only the "View Bill" button in the FIRST row
5. Wait until the bill PDF finishes downloading
6. Use the 'done' action with output: "Successfully downloaded one bill"
"""
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
"""
}

def get_provider_prompt(provider_name: str, task_step: str = None) -> str:
    """
    Get the appropriate prompt for a provider based on the provider name.
    For Duke Energy, task_step can be: 'task1_login', 'task2_2fa', 'task3_download'
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
    
    prompt_data = PROVIDER_PROMPTS.get(provider_key, PROVIDER_PROMPTS["duke_energy"])
    
    # If Duke Energy and task_step specified, return specific task
    if provider_key == "duke_energy" and task_step and isinstance(prompt_data, dict):
        return prompt_data.get(task_step, prompt_data.get("task1_login"))
    
    # For non-Duke providers or if dict not used, return as-is
    if isinstance(prompt_data, dict):
        # Duke Energy without task_step - return task1 for backward compatibility
        return prompt_data.get("task1_login")
    
    return prompt_data