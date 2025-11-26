"""
Simplified script to retrieve OTP codes from emails using Microsoft Graph API.
"""

import requests
import re
import os
from urllib.parse import quote
from html import unescape
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone



class GraphAPIEmailClient:
    """Client for extracting OTP codes from Outlook emails via Microsoft Graph API."""
    
    # Default mailbox GUID (sagility.com mailbox)
    DEFAULT_MAILBOX_GUID = "8a570157-0bb9-4090-a5c2-ed200b210c8b"
    
    # Mailbox mapping - automatically selects correct mailbox based on recipient email domain
    MAILBOX_MAP = {
        "sagiliti.com": DEFAULT_MAILBOX_GUID,
        "jitservicesinc.com": "c1aeadae-eda7-4a1e-bd60-f8997d3b2c47"
    }
    
    def __init__(self, tenant_id=None, client_id=None, client_secret=None, mailbox_guid=None):
        """Initialize the Graph API Email Client."""
        load_dotenv()
        
        self.tenant_id = tenant_id or os.getenv("TENANT_ID")
        self.client_id = client_id or os.getenv("CLIENT_ID")
        self.client_secret = client_secret or os.getenv("CLIENT_SECRET")
        self.mailbox_guid = mailbox_guid or os.getenv("TARGET_MAILBOX_GUID")
        
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.graph_api_url = "https://graph.microsoft.com/v1.0"
        self.scope = "https://graph.microsoft.com/.default"
        
        self.access_token = None
    
    @staticmethod
    def get_mailbox_guid_for_recipient(recipient_email):
        """Determine which mailbox GUID to use based on recipient email domain."""
        if not recipient_email:
            return None
        
        domain = recipient_email.split('@')[-1].lower()
        mailbox = GraphAPIEmailClient.MAILBOX_MAP.get(domain)
        
        if not mailbox:
            print(f"⚠️ WARNING: Unknown domain '{domain}'. Using default mailbox.")
            return GraphAPIEmailClient.DEFAULT_MAILBOX_GUID  # Use constant instead
    
        return mailbox
    
    def get_access_token(self):
        """Retrieves an access token using the Client Credentials Flow."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
            "grant_type": "client_credentials"
        }
        response = requests.post(self.token_url, data=data)
        response.raise_for_status()
        self.access_token = response.json()["access_token"]
        return self.access_token
    
    def get_latest_emails_from_inbox(self, count=3):
        """Get the latest N emails from the Inbox without any filtering."""
        if not self.access_token:
            self.get_access_token()
        
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
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get('value', [])
    
    @staticmethod
    def extract_otp_from_email(email):
        """Extract OTP code from email content."""
        body_dict = email.get("body", {}) or {}
        content = body_dict.get("content", "") or ""
        
        if isinstance(content, dict):
            content = content.get("content", "") or ""

        preview_raw = email.get("bodyPreview", "") or ""
        search_text = unescape(f"{content} {preview_raw}")
        
        # Clean text: remove URLs, HTML tags, and special characters
        search_text = re.sub(r'(https?:\/\/[^\s>]+)', ' ', search_text, flags=re.IGNORECASE)
        search_text = re.sub(r'<\s*http[^\s>]*>', ' ', search_text, flags=re.IGNORECASE)
        search_text = re.sub(r'<.*?>', ' ', search_text)
        search_text = re.sub(r'[^A-Za-z0-9\s]', ' ', search_text)
        search_text = re.sub(r'\s+', ' ', search_text).strip()
        
        # Search for OTP patterns
        otp_patterns = [
            r'(?<!\d)(\d{6})(?!\d)',  # 6-digit (most common)
            r'(?<!\d)(\d{8})(?!\d)',  # 8-digit
            r'(?<!\d)(\d{5})(?!\d)',  # 5-digit
            r'(?<!\d)(\d{4})(?!\d)',  # 4-digit
        ]

        for pattern in otp_patterns:
            matches = re.findall(pattern, search_text)
            if matches:
                return matches[0]

        return None
    
    def get_emails_by_search(self, recipient_email):
        """Retrieve emails sent to a specific recipient using Graph $search parameter."""
        if not self.access_token:
            self.get_access_token()

        encoded_recipient = quote(recipient_email, safe='@._-')
        search_query = f"to:{encoded_recipient}"

        url = (
            f"{self.graph_api_url}/users/{self.mailbox_guid}/messages"
            f"?$search=\"{search_query}\""
            f"&$select=id,subject,sender,toRecipients,receivedDateTime,bodyPreview,body"
            f"&$top=5"
        )

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "ConsistencyLevel": "eventual",
            "Prefer": 'outlook.body-content-type="text"'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        emails = response.json().get('value', [])
        
        return emails
    
    def get_latest_otp_from_inbox(
    self,
    sender_filter=None,
    recipient_email=None,
    max_emails=5,
    max_age_minutes=2):
        """
        Get the latest OTP code from inbox emails.
        Optionally filter by sender email and recipient email.
        Automatically selects the correct mailbox based on recipient email domain.
        
        Returns:
            (otp_code, subject, sender_address) or (None, None, None)
        """
        # Auto-detect mailbox based on recipient email domain
        if recipient_email:
            detected_mailbox = self.get_mailbox_guid_for_recipient(recipient_email)
            if detected_mailbox:
                print(f"📬 Auto-detected mailbox for {recipient_email}: {detected_mailbox}")
                self.mailbox_guid = detected_mailbox
        
        if not self.access_token:
            self.get_access_token()

        # Query logic
        if recipient_email:
            emails = self.get_emails_by_search(recipient_email)  # uses $search
        else:
            emails = self.get_latest_emails_from_inbox(max_emails)  # fallback

        if not emails:
            return None, None, None

        # Filter by time (recent emails only)
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)

        def parse_time(dt):
            return datetime.fromisoformat(dt.replace("Z", "+00:00"))

        emails = [
            e for e in emails
            if parse_time(e.get("receivedDateTime", "1970-01-01T00:00:00Z")) >= time_threshold
        ]

        if not emails:
            return None, None, None

        # Sort emails by received datetime DESC (latest first)
        emails = sorted(
            emails,
            key=lambda e: e.get("receivedDateTime", ""),
            reverse=True
        )

        # Search for sender match + OTP
        for email in emails:
            sender = email.get("sender", {}).get("emailAddress", {}).get("address", "")
            subject = email.get("subject", "N/A")

            if sender_filter and sender_filter.lower() not in sender.lower():
                continue

            otp = self.extract_otp_from_email(email)
            if otp:
                return otp, subject, sender

        return None, None, None

if __name__ == "__main__":
    # Test the OTP extraction
    client = GraphAPIEmailClient()
    
    recipient_email = "billing-pds@jitservicesinc.com"
    
    print(f"Searching for OTP in emails sent to: {recipient_email}")
    otp, subject, sender = client.get_latest_otp_from_inbox(
        recipient_email=recipient_email,
        max_emails=5
    )
    
    if otp:
        print("\n" + "=" * 60)
        print(f"✅ OTP FOUND: {otp}")
        print(f"   From: {sender}")
        print(f"   Subject: {subject}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ No OTP found in recent emails")
        print("=" * 60)