"""
Provider-specific prompts for browser automation tasks
"""

PROVIDER_PROMPTS = {
    "duke_energy": """
1. Go to {signin_url}
2. Wait for the page to fully load (this site is slow)
3. Log-in with:
     • email    : {email}
     • password : {password}
4. If unable to login, STOP the task with status "Failed"
5. Wait until dashboard finishes loading
6. Navigate to {billing_history_url}
7. Wait until the text "Billing & Payment Activity" is visible
8. If "Oops, something went wrong." appears, STOP the task with status "Failed"
9. Click only the "View Bill" button in the FIRST row
10. Wait until the bill PDF finishes downloading
11. Use the 'done' action to mark the task as finished with message "Successfully downloaded one bill"
""",
    
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

def get_provider_prompt(provider_name: str) -> str:
    """
    Get the appropriate prompt for a provider based on the provider name.
    Returns Duke Energy prompt as default if provider not found.
    """
    # Normalize provider name to match our keys
    provider_key = provider_name.lower().replace(" ", "_").replace("-", "_")
    
    # Handle common variations
    if "duke" in provider_key:
        provider_key = "duke_energy"
    elif "xcel" in provider_key:
        provider_key = "xcel_energy"
    
    return PROVIDER_PROMPTS.get(provider_key, PROVIDER_PROMPTS["duke_energy"])