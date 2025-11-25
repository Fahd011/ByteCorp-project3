"""
Script to retrieve emails sent to a specific recipient from a folder in Outlook.
Uses Microsoft Graph API with $search parameter for efficient server-side filtering.
"""

import requests
import sys
import re
from time import sleep
import os
from dotenv import load_dotenv


class GraphAPIEmailClient:
    """Client for accessing Microsoft Graph API to retrieve and filter emails from Outlook mailboxes."""
    
    def __init__(self, tenant_id=None, client_id=None, client_secret=None, mailbox_guid=None):
        """
        Initialize the Graph API Email Client.
        
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
    
    def get_emails_by_recipient(self, folder_id, folder_name, recipient_email):
        """
        Retrieves emails sent to a specific recipient using $filter.
        This is more reliable than $search, especially for email addresses with special characters.
        
        Args:
            folder_id: The unique ID of the folder
            folder_name: Display name of the folder (for logging)
            recipient_email: Email address to filter by
            
        Returns:
            List of email messages sent to the specified recipient
        """
        if not self.access_token:
            self.get_access_token()
        
        print(f"\n--- Searching for messages sent to '{recipient_email}' in '{folder_name}' ---")
        
        # Use $filter to find emails where the recipient matches
        filter_query = f"toRecipients/any(r:r/emailAddress/address eq '{recipient_email}')"
        
        initial_url = (
            f"{self.graph_api_url}/users/{self.mailbox_guid}/mailFolders/{folder_id}/messages"
            f"?$filter={filter_query}"
            f"&$top=50"
            f"&$select=subject,sender,receivedDateTime,bodyPreview,body,toRecipients"
            f"&$orderby=receivedDateTime desc"
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
                print(f"Response: {e.response.text if hasattr(e, 'response') else 'No response'}")
                return []
        
        print(f"Successfully retrieved {len(all_emails)} emails sent to '{recipient_email}' from the folder.")
        return all_emails
    
    def get_emails_by_recipient_from_folder_name(self, folder_name, recipient_email):
        """
        Convenience method to get all emails sent to a specific recipient from a folder by name.
        
        Args:
            folder_name: Name of the folder to retrieve emails from
            recipient_email: Email address to filter by
            
        Returns:
            List of email messages sent to the specified recipient
        """
        folder_id = self.get_child_folder_id(folder_name)
        if not folder_id:
            return []
        
        return self.get_emails_by_recipient(folder_id, folder_name, recipient_email)
    
    def get_latest_emails_from_inbox(self, count=3):
        """
        Get the latest N emails from the Inbox without any filtering.
        
        Args:
            count: Number of latest emails to retrieve (default: 3)
            
        Returns:
            List of the latest email messages
        """
        if not self.access_token:
            self.get_access_token()
        
        print(f"\n--- Retrieving latest {count} messages from Inbox ---")
        
        url = (
            f"{self.graph_api_url}/users/{self.mailbox_guid}/mailFolders/Inbox/messages"
            f"?$top={count}"
            f"&$select=subject,sender,receivedDateTime,bodyPreview,body,toRecipients"
            f"&$orderby=receivedDateTime desc"
        )
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Prefer": 'outlook.body-content-type="text"'
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            messages_result = response.json()
            emails = messages_result.get('value', [])
            
            print(f"Successfully retrieved {len(emails)} emails from Inbox.")
            return emails
        
        except requests.exceptions.RequestException as e:
            print(f"ERROR during email retrieval: {e}")
            if hasattr(e, 'response'):
                print(f"Response: {e.response.text}")
            return []
    
    @staticmethod
    def extract_otp_from_email(email):
        """
        Extract OTP/verification code from an email message.
        
        Args:
            email: Email message object from Graph API
            
        Returns:
            OTP code as string if found, None otherwise
        """
        # Get email body content
        body_dict = email.get("body", {})
        body_content = body_dict.get("content", "")
        
        # Also check body preview as fallback
        body_preview = email.get("bodyPreview", "")
        
        # Combine both for searching
        search_text = f"{body_content} {body_preview}"
        
        # Common OTP patterns (prioritize by length)
        otp_patterns = [
            r'\b(\d{6})\b',  # 6-digit code (most common)
            r'\b(\d{8})\b',  # 8-digit code
            r'\b(\d{5})\b',  # 5-digit code
            r'\b(\d{4})\b',  # 4-digit code
        ]
        
        for pattern in otp_patterns:
            match = re.search(pattern, search_text)
            if match:
                return match.group(1)
        
        return None
    
    def get_latest_otp_from_inbox(self, sender_filter=None, max_emails=5):
        """
        Get the OTP code from the latest email in Inbox.
        Optionally filter by sender email address.
        
        Args:
            sender_filter: Optional sender email address to filter by (e.g., "no-reply@verify.dukeenergy.com")
            max_emails: Maximum number of recent emails to check (default: 5)
            
        Returns:
            Tuple of (otp_code, email_subject, sender_address) if found, (None, None, None) otherwise
        """
        if not self.access_token:
            self.get_access_token()
        
        print(f"\n--- Searching for OTP code in latest {max_emails} emails ---")
        if sender_filter:
            print(f"Filtering by sender: {sender_filter}")
        
        # Get latest emails
        emails = self.get_latest_emails_from_inbox(max_emails)
        
        if not emails:
            print("No emails found.")
            return None, None, None
        
        # Search through emails for OTP
        for email in emails:
            sender = email.get("sender", {}).get("emailAddress", {}).get("address", "")
            subject = email.get("subject", "N/A")
            
            # If sender filter is provided, skip emails not from that sender
            if sender_filter and sender_filter.lower() not in sender.lower():
                continue
            
            # Try to extract OTP from this email
            otp = self.extract_otp_from_email(email)
            
            if otp:
                print(f"\n✅ Found OTP: {otp}")
                print(f"   From: {sender}")
                print(f"   Subject: {subject}")
                return otp, subject, sender
        
        print("❌ No OTP code found in recent emails.")
        return None, None, None
    
    def get_emails_by_recipient_from_inbox(self, recipient_email):
        """
        Search for emails sent to a specific recipient directly in the Inbox.
        This searches the entire Inbox without needing to specify a child folder.
        
        Args:
            recipient_email: Email address to filter by
            
        Returns:
            List of email messages sent to the specified recipient
        """
        if not self.access_token:
            self.get_access_token()
        
        print(f"\n--- Searching Inbox for messages sent to '{recipient_email}' ---")
        
        # Use $filter to find emails where the recipient matches
        # We need to filter by toRecipients/emailAddress/address
        filter_query = f"toRecipients/any(r:r/emailAddress/address eq '{recipient_email}')"
        
        initial_url = (
            f"{self.graph_api_url}/users/{self.mailbox_guid}/mailFolders/Inbox/messages"
            f"?$filter={filter_query}"
            f"&$top=50"
            f"&$select=subject,sender,receivedDateTime,bodyPreview,body,toRecipients"
            f"&$orderby=receivedDateTime desc"
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
                print(f"Response: {e.response.text if hasattr(e, 'response') else 'No response'}")
                return []
        
        print(f"Successfully retrieved {len(all_emails)} emails sent to '{recipient_email}' from Inbox.")
        return all_emails

def main():
    """Main execution function."""
    # Default recipient filter
    recipient_filter = "billing+ree@sagiliti.com"
    
    # Check for folder name argument
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python to_specific_email.py otp [sender_email]  - Extract OTP from latest emails")
        print("  python to_specific_email.py latest [count]  - Get latest N emails (default: 3)")
        print("  python to_specific_email.py inbox [recipient_email]  - Filter by recipient")
        print("  python to_specific_email.py [folder_name] [recipient_email]  - Filter in folder")
        print("\nExamples:")
        print("  python to_specific_email.py otp")
        print("  python to_specific_email.py otp no-reply@verify.dukeenergy.com")
        print("  python to_specific_email.py latest 5")
        print("  python to_specific_email.py inbox billing+rtx@sagiliti.com")
        print("  python to_specific_email.py Ecolab billing-ecolab@jitservicesinc.com")
        print("\nNo arguments provided. Extracting OTP from latest emails...")
        folder_name = "otp"
    else:
        folder_name = sys.argv[1]
    
    # Initialize the client
    client = GraphAPIEmailClient()
    
    # Handle "otp" command to extract OTP from latest emails
    if folder_name.lower() == "otp":
        sender_filter = None
        if len(sys.argv) >= 3:
            sender_filter = sys.argv[2]
        
        otp, subject, sender = client.get_latest_otp_from_inbox(sender_filter)
        
        if otp:
            print("\n" + "=" * 80)
            print(f"OTP CODE: {otp}")
            print(f"From: {sender}")
            print(f"Subject: {subject}")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("No OTP code found in recent emails.")
            print("=" * 80)
        return
    
    # Handle "latest" command to get most recent emails
    elif folder_name.lower() == "latest":
        count = 3  # Default
        if len(sys.argv) >= 3:
            try:
                count = int(sys.argv[2])
            except ValueError:
                print(f"Invalid count: {sys.argv[2]}, using default of 3")
        
        print(f"Getting latest {count} emails from Inbox...")
        emails = client.get_latest_emails_from_inbox(count)
        location = "Inbox (latest)"
        recipient_filter = None
    # Search Inbox directly if folder is "inbox", otherwise search child folder
    elif folder_name.lower() == "inbox":
        # Optional: Accept recipient email as second argument
        if len(sys.argv) >= 3:
            recipient_filter = sys.argv[2]
        
        print(f"Searching entire Inbox for emails sent to: {recipient_filter}")
        emails = client.get_emails_by_recipient_from_inbox(recipient_filter)
        location = "Inbox"
    else:
        # Optional: Accept recipient email as second argument
        if len(sys.argv) >= 3:
            recipient_filter = sys.argv[2]
        
        print(f"Searching folder '{folder_name}' for emails sent to: {recipient_filter}")
        emails = client.get_emails_by_recipient_from_folder_name(folder_name, recipient_filter)
        location = f"'{folder_name}'"
    
    # Output Results
    print("\n" + "=" * 80)
    if recipient_filter:
        print(f"TOTAL EMAILS RETRIEVED from {location} sent to: {recipient_filter}: {len(emails)}")
    else:
        print(f"TOTAL EMAILS RETRIEVED from {location}: {len(emails)}")
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