import requests
import json
import sys
from time import sleep
import os
from dotenv import load_dotenv

load_dotenv()
# --- 1. CONFIGURATION ---
# Use the credentials that successfully obtained the token
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# GUID of the Primary Mailbox (billing@sagility.com)
TARGET_MAILBOX_GUID = os.getenv("TARGET_MAILBOX_GUID")
# TARGET_MAILBOX_GUID = "billing@sagiliti.com"
# TARGET_MAILBOX_GUID = "c1aeadae-eda7-4a1e-bd60-f8997d3b2c47"    # GUID for billing@jitservicesinc.com
TARGET_MAILBOX_UPN = "billing@sagility.com" # For display

# API Endpoints
TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_API_URL = "https://graph.microsoft.com/v1.0"
SCOPE = "https://graph.microsoft.com/.default"

# --- 2. AUTHENTICATION ---

def get_access_token():
    """Retrieves an access token using the Client Credentials Flow."""
    print("--- 1. Requesting Access Token ---")
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPE,
        "grant_type": "client_credentials"
    }
    try:
        response = requests.post(TOKEN_URL, data=data)
        response.raise_for_status()
        print("Successfully retrieved access token.")
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not retrieve token. Check credentials and tenant ID. {e}")
        sys.exit(1)

# --- 3. FOLDER LOOKUP (Step 1) ---

def get_child_folder_id(token, folder_name):
    """
    Finds the unique ID (FolderID) for a child folder by its display name.
    """
    print(f"\n--- 2. Searching for folder '{folder_name}' ---")

    # API call to get all child folders of the Inbox, selecting only the name and ID
    folder_url = (
        f"{GRAPH_API_URL}/users/{TARGET_MAILBOX_GUID}/mailFolders/Inbox/childFolders"
        f"?$select=displayName,id"
    )
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(folder_url, headers=headers)
        response.raise_for_status()
        
        folders = response.json().get("value", [])
        
        for folder in folders:
            if folder.get("displayName") == folder_name:
                folder_id = folder.get("id")
                print(f"Found folder '{folder_name}'. ID: {folder_id}")
                return folder_id
        
        print(f"ERROR: Folder '{folder_name}' not found in the Inbox children.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"ERROR during folder lookup: {e}")
        return None

# --- 4. EMAIL RETRIEVAL (Step 2 - with Pagination) ---

def get_all_emails_from_folder(token, folder_id, folder_name):
    """
    Retrieves ALL emails from the specified folder using pagination.
    """
    print(f"\n--- 3. Fetching all messages from '{folder_name}' ---")
    
    # Initial URL for the first page (using $top=50 for larger batches)
    # MODIFIED: Added 'body' to the $select query to retrieve the full message content
    initial_url = (
        f"{GRAPH_API_URL}/users/{TARGET_MAILBOX_GUID}/mailFolders/{folder_id}/messages"
        f"?$top=50&$select=subject,sender,receivedDateTime,bodyPreview,body"
    )
    
    current_url = initial_url
    all_emails = []
    page_count = 0
    
    headers = {"Authorization": f"Bearer {token}",
        "Prefer": 'outlook.body-content-type="text"'  # <-- This is the fix}
    }

    while current_url:
        page_count += 1
        print(f"  Fetching page {page_count}...")
        
        try:
            response = requests.get(current_url, headers=headers)
            response.raise_for_status()
            
            messages_result = response.json()
            emails_in_page = messages_result.get('value', [])
            all_emails.extend(emails_in_page)
            
            # Get the link to the next page for pagination
            current_url = messages_result.get('@odata.nextLink')

            # Small delay to prevent hitting rate limits during heavy pagination
            if current_url:
                sleep(0.3) 

        except requests.exceptions.RequestException as e:
            print(f"ERROR during email retrieval: {e}")
            return []
            
    return all_emails

# --- 5. MAIN EXECUTION ---

if __name__ == "__main__":
    # Check for necessary imports
    try:
        import requests
    except ImportError:
        print("The 'requests' library is required. Install it using: pip install requests")
        sys.exit(1)

    # Check for folder name argument, otherwise default to Ecolab
    if len(sys.argv) < 2:
        print("No folder name provided via command line.")
        print("Defaulting to search for folder: 'Ecolab'")
        FOLDER_NAME = "Ecolab"
    else:
        FOLDER_NAME = sys.argv[1]

    # 1. Get Access Token
    token = get_access_token()

    # 2. Get Folder ID
    folder_id = get_child_folder_id(token, FOLDER_NAME)
    
    if not folder_id:
        sys.exit(1)

    # 3. Get All Emails from Folder
    emails = get_all_emails_from_folder(token, folder_id, FOLDER_NAME)
    
    # 4. Output Results
    print("\n" + "=" * 80)
    print(f"TOTAL EMAILS RETRIEVED from '{FOLDER_NAME}' ({TARGET_MAILBOX_UPN}): {len(emails)}")
    print("=" * 80)
    
    if emails:
        # Display the first 10 emails as a summary
        for i, mail in enumerate(emails[:10]):
            print("-" * 55)
            print(f"Message {i + 1}:")
            print("  From:", mail.get("sender", {}).get("emailAddress", {}).get("address", "N/A"))
            print("  Subject:", mail.get("subject", "N/A"))
            print("  Received:", mail.get("receivedDateTime", "N/A"))
            
            # NEW LOGIC: Print the entire message body content
            body_dict = mail.get("body", {})
            full_body = body_dict.get("content", "N/A")
            
            print("  Full Message Body:")
            print(full_body)
            print("-" * 55)