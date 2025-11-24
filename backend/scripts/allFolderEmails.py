
import requests
import sys
from time import sleep
import os
from dotenv import load_dotenv


class GraphAPIEmailClient:
    """Client for accessing Microsoft Graph API to retrieve emails from Outlook mailboxes."""
    
    def __init__(self, tenant_id=None, client_id=None, client_secret=None, mailbox_guid=None):
        """
        Initialize the Outlook Mailbox Client.
        
        Args:
            tenant_id: Azure AD tenant ID (defaults to env var)
            client_id: Azure AD application client ID (defaults to env var)
            client_secret: Azure AD application client secret (defaults to env var)
            mailbox_guid: Target mailbox GUID or UPN (defaults to env var)
        """
        load_dotenv()
        
        self.tenant_id = tenant_id or os.getenv("TENANT_ID")
        self.client_id = client_id or os.getenv("CLIENT_ID")
        self.client_secret = client_secret or os.getenv("CLIENT_SECRET")
        self.mailbox_guid = mailbox_guid or os.getenv("TARGET_MAILBOX_GUID")
        
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.graph_api_url = "https://graph.microsoft.com/v1.0"
        self.scope = "https://graph.microsoft.com/.default"
        
        self.access_token = None
    
    def get_access_token(self):
        """Retrieves an access token using the Client Credentials Flow."""
        print("--- Requesting Access Token ---")
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
            "grant_type": "client_credentials"
        }
        try:
            response = requests.post(self.token_url, data=data)
            response.raise_for_status()
            self.access_token = response.json()["access_token"]
            print("Successfully retrieved access token.")
            return self.access_token
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Could not retrieve token. Check credentials and tenant ID. {e}")
            raise
    
    def get_child_folder_id(self, folder_name):
        """
        Finds the unique ID (FolderID) for a child folder by its display name.
        
        Args:
            folder_name: Name of the folder to search for
            
        Returns:
            Folder ID if found, None otherwise
        """
        if not self.access_token:
            self.get_access_token()
        
        print(f"\n--- Searching for folder '{folder_name}' ---")
        
        folder_url = (
            f"{self.graph_api_url}/users/{self.mailbox_guid}/mailFolders/Inbox/childFolders"
            f"?$select=displayName,id"
        )
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
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
    
    def get_all_emails_from_folder(self, folder_id, folder_name):
        """
        Retrieves ALL emails from the specified folder using pagination.
        
        Args:
            folder_id: The unique ID of the folder
            folder_name: Display name of the folder (for logging)
            
        Returns:
            List of email messages
        """
        if not self.access_token:
            self.get_access_token()
        
        print(f"\n--- Fetching all messages from '{folder_name}' ---")
        
        initial_url = (
            f"{self.graph_api_url}/users/{self.mailbox_guid}/mailFolders/{folder_id}/messages"
            f"?$top=50&$select=subject,sender,receivedDateTime,bodyPreview,body"
        )
        
        current_url = initial_url
        all_emails = []
        page_count = 0
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Prefer": 'outlook.body-content-type="text"'
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
                
                current_url = messages_result.get('@odata.nextLink')
                
                if current_url:
                    sleep(0.3)
            
            except requests.exceptions.RequestException as e:
                print(f"ERROR during email retrieval: {e}")
                return []
        
        return all_emails
    
    def get_emails_by_folder_name(self, folder_name):
        """
        Convenience method to get all emails from a folder by name.
        
        Args:
            folder_name: Name of the folder to retrieve emails from
            
        Returns:
            List of email messages
        """
        folder_id = self.get_child_folder_id(folder_name)
        if not folder_id:
            return []
        
        return self.get_all_emails_from_folder(folder_id, folder_name)

def main():
    """Main execution function."""
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
        folder_name = "Ecolab"
    else:
        folder_name = sys.argv[1]
    
    # Initialize the client
    client = GraphAPIEmailClient()
    
    # Get emails from the specified folder
    emails = client.get_emails_by_folder_name(folder_name)
    
    # Output Results
    print("\n" + "=" * 80)
    print(f"TOTAL EMAILS RETRIEVED from '{folder_name}': {len(emails)}")
    print("=" * 80)
    
    if emails:
        # Display the first 10 emails as a summary
        for i, mail in enumerate(emails[:10]):
            print("-" * 55)
            print(f"Message {i + 1}:")
            print("  From:", mail.get("sender", {}).get("emailAddress", {}).get("address", "N/A"))
            print("  Subject:", mail.get("subject", "N/A"))
            print("  Received:", mail.get("receivedDateTime", "N/A"))
            
            body_dict = mail.get("body", {})
            full_body = body_dict.get("content", "N/A")
            
            print("  Full Message Body:")
            print(full_body)
            print("-" * 55)


if __name__ == "__main__":
    main()