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
        self.token_expires_at = None  # Track when token expires
    
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
    
    def get_access_token(self, force_refresh=False):
        """
        Retrieves an access token using the Client Credentials Flow.
        Automatically refreshes if expired.
        
        Args:
            force_refresh: Force token refresh even if not expired
        """
        # Check if we have a valid token
        if not force_refresh and self.access_token and self.token_expires_at:
            # Add 5 minute buffer before expiry
            if datetime.now(timezone.utc) < self.token_expires_at - timedelta(minutes=5):
                return self.access_token
        
        # Token is missing, expired, or forced refresh - get new token
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
            "grant_type": "client_credentials"
        }
        
        response = requests.post(self.token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        
        # Calculate expiry time (expires_in is in seconds)
        expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
        self.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        print(f"[INFO] Token acquired, expires at {self.token_expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return self.access_token
    
    def is_token_valid(self):
        """Check if current token is still valid (with 5 minute buffer)."""
        if not self.access_token or not self.token_expires_at:
            return False
        
        return datetime.now(timezone.utc) < self.token_expires_at - timedelta(minutes=5)
    
    def get_latest_emails_from_inbox(self, count=3, mailbox_guid=None):
        """Get the latest N emails from the Inbox without any filtering."""
        if not self.is_token_valid():
            self.get_access_token()
        
        mailbox = mailbox_guid or self.mailbox_guid  # Use parameter or default
        
        url = (
            f"{self.graph_api_url}/users/{mailbox}/mailFolders/Inbox/messages"
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
    
    def get_emails_by_search(self, recipient_email, mailbox_guid=None):
        """Retrieve emails sent to a specific recipient using Graph $search parameter."""
        if not self.is_token_valid():
            self.get_access_token()

        encoded_recipient = quote(recipient_email, safe='@._-')
        search_query = f"to:{encoded_recipient}"
        mailbox = mailbox_guid or self.mailbox_guid

        url = (
            f"{self.graph_api_url}/users/{mailbox}/messages"
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
        mailbox_to_use = self.mailbox_guid  # Default fallback
        if recipient_email:
            detected_mailbox = self.get_mailbox_guid_for_recipient(recipient_email)
            if detected_mailbox:
                print(f"📬 Auto-detected mailbox for {recipient_email}: {detected_mailbox}")
                mailbox_to_use = detected_mailbox
        
        if not self.is_token_valid():
            self.get_access_token()

        # Query logic
        if recipient_email:
            emails = self.get_emails_by_search(recipient_email, mailbox_to_use)  # uses $search
        else:
            emails = self.get_latest_emails_from_inbox(max_emails, mailbox_to_use)  # fallback

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