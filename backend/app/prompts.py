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
3. Log in with:
   • email : {email}
   • password : {password}
4. Wait until the account dashboard is fully loaded
5. Navigate to {billing_history_url}
6. Wait until the text "Billing Accounts" is visible. If not, wait 5 seconds and check again.
7. Identify the COMPLETE list of all billing accounts shown in the table (each with an account number and selection radio button).
8. For EACH account in the list (process ALL accounts, one by one):
   a. Select the account by clicking its radio button
   b. Wait at least 8 seconds for the selection to register
   c. Navigate to the billing tab
   d. Wait until the text "Billing History" is visible and go to the Statements tab
   e. If "Oops, something went wrong." appears, STOP the task with status "Failed"
   f. Click only the download button in the FIRST row to download the latest bill
   g. Wait until the bill PDF finishes downloading
   h. Navigate back to {billing_history_url}
   and confirm that the billing accounts list is visible before continuing
9. Repeat step 8 until EVERY account in the list has been processed and its bill downloaded.
10. ONLY AFTER all accounts have been processed, finish the task by calling 'done' with the message:
    "Successfully downloaded all bills"
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