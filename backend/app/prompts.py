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
3. Log-in with:
• email : {email}
• password : {password}

5. Wait until the Billing Accounts text is visible. If not, wait 5 seconds and check again.
6. IMPORTANT: If there are multiple accounts, look for and select the account number: {account_number}
7. Navigate to {billing_history_url} or click the billing tab
8. Wait until the text "Billing History" is visible and navigate to the statements tab
9. If "Oops, something went wrong." appears, STOP the task with status "Failed"
10. Click only the download button in the FIRST row
11. Wait until the bill PDF finishes downloading
12. Use the 'done' action to mark the task as finished with message "Successfully downloaded bill for account {account_number}"
""",

    "xcel_energy_collect_accounts": """
1. Go to {signin_url}
2. Wait for the page to fully load (this site is slow)
3. Log-in with:
• email : {email}
• password : {password}

5. Wait until the dashboard finishes loading
6. Navigate to {billing_history_url} (Billing Accounts page)
7. Wait until the text "Billing Accounts" or account list is visible
8. Extract all account numbers visible on the page (they are usually labeled as "Account Number" or similar)
9. Store the list of account numbers
10. Use the 'done' action to mark the task as finished with message "Collected account numbers: [list them here]"
"""
}

def get_provider_prompt(provider_name: str, mode: str = "download") -> str:
    """
    Get the appropriate prompt for a provider based on the provider name.
    Returns Duke Energy prompt as default if provider not found.
    
    Args:
        provider_name: Name of the provider
        mode: "download" (default) or "collect_accounts" (for Xcel Energy)
    """
    # Normalize provider name to match our keys
    provider_key = provider_name.lower().replace(" ", "_").replace("-", "_")
    
    # Handle common variations
    if "duke" in provider_key:
        provider_key = "duke_energy"
    elif "xcel" in provider_key:
        if mode == "collect_accounts":
            provider_key = "xcel_energy_collect_accounts"
        else:
            provider_key = "xcel_energy"
    
    return PROVIDER_PROMPTS.get(provider_key, PROVIDER_PROMPTS["duke_energy"])