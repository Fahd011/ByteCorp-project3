#!/usr/bin/env python3
"""
Azure Blob Storage Service for PDF uploads and downloads
"""

import os
import io
from datetime import datetime
from typing import Tuple, List, Optional
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

class AzureStorageService:
    def __init__(self):
        # Azure Storage Configuration - Load from environment variables
        self.connection_string = os.getenv(
            "AZURE_STORAGE_CONNECTION_STRING",
        )
        self.storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.storage_account_key = os.getenv(
            "AZURE_STORAGE_ACCOUNT_KEY", 
            
        )
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER")
        
        # Initialize Azure Blob Service Client
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
            print(f"✅ Azure Storage connected successfully to container: {self.container_name}")
        except Exception as e:
            print(f"❌ Error connecting to Azure Storage: {e}")
            raise
    
    def create_dummy_pdf(self, username: str, timestamp: str) -> bytes:
        """
        Create a dummy PDF file for testing purposes
        
        Args:
            username: User's email/username
            timestamp: Timestamp string
            
        Returns:
            PDF content as bytes
        """
        try:
            # Create PDF in memory
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            
            # Add content to PDF
            p.setFont("Helvetica-Bold", 16)
            p.drawString(1*inch, 10*inch, f"Sample Bill Report")
            
            p.setFont("Helvetica", 12)
            p.drawString(1*inch, 9.5*inch, f"Generated for: {username}")
            p.drawString(1*inch, 9.2*inch, f"Timestamp: {timestamp}")
            p.drawString(1*inch, 8.9*inch, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            p.setFont("Helvetica", 10)
            p.drawString(1*inch, 8*inch, "This is a dummy PDF file created for testing Azure storage integration.")
            p.drawString(1*inch, 7.7*inch, "In a real scenario, this would contain actual billing information.")
            p.drawString(1*inch, 7.4*inch, "The file is uploaded to Azure Blob Storage for secure storage and retrieval.")
            
            # Add some sample data
            p.drawString(1*inch, 6.5*inch, "Sample Billing Data:")
            p.drawString(1*inch, 6.2*inch, "• Account Number: 123456789")
            p.drawString(1*inch, 6.0*inch, "• Bill Amount: $150.00")
            p.drawString(1*inch, 5.8*inch, "• Due Date: 2024-01-15")
            p.drawString(1*inch, 5.6*inch, "• Service Period: December 2023")
            
            p.save()
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            print(f"❌ Error creating dummy PDF: {e}")
            raise
    
    def upload_pdf_to_azure(self, pdf_content: bytes, email: str, original_filename: str) -> Tuple[bool, str, str]:
        """
        Upload PDF to Azure Blob Storage with year/month organization
        
        Args:
            pdf_content: PDF file content as bytes
            email: User's email
            original_filename: Original filename
            
        Returns:
            Tuple of (success, blob_url, blob_name)
        """
        try:
            # Create year/month path
            current_date = datetime.now()
            year_month_path = f"{current_date.year}/{current_date.month:02d}"
            
            # Create blob name with path
            blob_name = f"{year_month_path}/{original_filename}"
            
            # Get blob client
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Upload the PDF
            blob_client.upload_blob(pdf_content, overwrite=True)
            
            # Generate the full URL
            blob_url = f"https://{self.storage_account_name}.blob.core.windows.net/{self.container_name}/{blob_name}"
            
            print(f"✅ PDF uploaded successfully to Azure: {blob_url}")
            return True, blob_url, blob_name
            
        except Exception as e:
            print(f"❌ Error uploading PDF to Azure: {e}")
            return False, "", ""
    
    def download_pdf_from_azure(self, blob_name: str) -> Tuple[bool, bytes]:
        """
        Download PDF from Azure Blob Storage
        
        Args:
            blob_name: Name of the blob to download
            
        Returns:
            Tuple of (success, pdf_content)
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Download the blob
            blob_data = blob_client.download_blob()
            pdf_content = blob_data.readall()
            
            print(f"✅ PDF downloaded successfully from Azure: {blob_name}")
            return True, pdf_content
            
        except Exception as e:
            print(f"❌ Error downloading PDF from Azure: {e}")
            return False, b""
    
    def get_blob_url(self, blob_name: str) -> str:
        """
        Generate the full URL for a blob
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            Full URL to the blob
        """
        return f"https://{self.storage_account_name}.blob.core.windows.net/{self.container_name}/{blob_name}"
    
    
    def delete_blob(self, blob_name: str):
        """
        Delete a single blob by name
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_client.delete_blob()
            return True
        except Exception as e:
            print(f"❌ Failed to delete blob {blob_name}: {e}")
            return False

    
    def list_blobs(self, prefix: Optional[str] = None) -> List[str]:
        """
        List all blobs in the container
        
        Args:
            prefix: Optional prefix to filter blobs
            
        Returns:
            List of blob names
        """
        try:
            blobs = []
            blob_list = self.container_client.list_blobs(name_starts_with=prefix)
            
            for blob in blob_list:
                blobs.append(blob.name)
            
            return blobs
            
        except Exception as e:
            print(f"❌ Error listing blobs: {e}")
            return []

    def upload_manual_credential_pdf(self, pdf_content: bytes, user_id: str, credential_id: str, original_filename: str) -> Tuple[bool, str, str]:
        """
        Upload manual credential PDF to Azure Blob Storage with user_credentials_bills_manual/year/month path
        
        Args:
            pdf_content: PDF file content as bytes
            user_id: User ID
            credential_id: Credential ID
            original_filename: Original filename
            
        Returns:
            Tuple of (success, blob_url, blob_name)
        """
        try:
            # Create year/month path
            current_date = datetime.now()
            year_month_path = f"{current_date.year}/{current_date.month:02d}"
            
            # Create blob name with manual credential path
            blob_name = f"user_credentials_bills_manual/{year_month_path}/{user_id}_{credential_id}_{original_filename}"
            
            # Get blob client
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Upload the PDF
            blob_client.upload_blob(pdf_content, overwrite=True)
            
            # Generate the full URL
            blob_url = f"https://{self.storage_account_name}.blob.core.windows.net/{self.container_name}/{blob_name}"
            
            print(f"✅ Manual credential PDF uploaded successfully to Azure: {blob_url}")
            return True, blob_url, blob_name
            
        except Exception as e:
            print(f"❌ Error uploading manual credential PDF to Azure: {e}")
            return False, "", ""

    def download_manual_credential_pdf(self, blob_name: str) -> Tuple[bool, bytes]:
        """
        Download manual credential PDF from Azure Blob Storage
        
        Args:
            blob_name: Name of the blob to download
            
        Returns:
            Tuple of (success, pdf_content)
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Download the blob
            blob_data = blob_client.download_blob()
            pdf_content = blob_data.readall()
            
            print(f"✅ Manual credential PDF downloaded successfully from Azure: {blob_name}")
            return True, pdf_content
            
        except Exception as e:
            print(f"❌ Error downloading manual credential PDF from Azure: {e}")
            return False, b""

# Create global instance
azure_storage_service = AzureStorageService()