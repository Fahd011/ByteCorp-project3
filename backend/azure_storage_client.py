import os
import urllib.parse
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import AzureError
from config import Config
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Azure Storage Configuration
CONNECTION_STRING = Config.AZURE_CONNECTION_STRING
STORAGE_ACCOUNT_NAME = Config.STORAGE_ACCOUNT_NAME
STORAGE_ACCOUNT_KEY = Config.STORAGE_ACCOUNT_KEY
CONTAINER_NAME = Config.CONTAINER_NAME

# Folder structure within the single container
CREDENTIALS_FOLDER = "credentials"  # For CSV files (replaces browser-use-cred bucket)
BILLS_FOLDER = "bills"              # For PDF files (replaces bills bucket)

# Initialize Azure Blob Service Client
try:
    blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)
    logger.info("Successfully initialized Azure Blob Service Client")
except Exception as e:
    logger.error(f"Failed to initialize Azure Blob Service Client: {e}")
    blob_service_client = None
    container_client = None

def upload_csv_to_azure(file, filename):
    """Upload CSV file to Azure Storage (replaces upload_csv_to_supabase)"""
    try:
        # Read file bytes
        file_bytes = file.read()
        
        # Create blob path in credentials folder
        blob_path = f"{CREDENTIALS_FOLDER}/{filename}"
        
        # Get blob client
        blob_client = container_client.get_blob_client(blob_path)
        
        # Upload file
        blob_client.upload_blob(file_bytes, overwrite=True)
        
        # Return public URL (Azure doesn't have public URLs by default, so we'll use a custom endpoint)
        public_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{CONTAINER_NAME}/{blob_path}"
        
        logger.info(f"Successfully uploaded CSV: {blob_path}")
        return public_url
        
    except AzureError as e:
        logger.error(f"Azure upload error: {e}")
        raise Exception(f"Azure upload error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error uploading CSV: {e}")
        raise Exception(f"Upload error: {e}")

def upload_file_to_azure(file_bytes, filename):
    """Upload file bytes to Azure Storage (replaces upload_file_to_supabase)"""
    try:
        # Create blob path in credentials folder
        blob_path = f"{CREDENTIALS_FOLDER}/{filename}"
        
        # Get blob client
        blob_client = container_client.get_blob_client(blob_path)
        
        # Upload file
        blob_client.upload_blob(file_bytes, overwrite=True)
        
        # Return public URL
        public_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{CONTAINER_NAME}/{blob_path}"
        
        logger.info(f"Successfully uploaded file: {blob_path}")
        return public_url
        
    except AzureError as e:
        logger.error(f"Azure upload error: {e}")
        raise Exception(f"Azure upload error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error uploading file: {e}")
        raise Exception(f"Upload error: {e}")

def upload_pdf_to_bills_folder(file_bytes, filename, user_id):
    """Upload PDF to bills folder in Azure Storage (replaces upload_pdf_to_bills_bucket)"""
    try:
        # Create user-specific folder structure: bills/{user_id}/{filename}
        blob_path = f"{BILLS_FOLDER}/{user_id}/{filename}"
        
        # Get blob client
        blob_client = container_client.get_blob_client(blob_path)
        
        # Upload with content type for PDF
        content_settings = ContentSettings(content_type="application/pdf")
        blob_client.upload_blob(
            file_bytes, 
            overwrite=True,
            content_settings=content_settings
        )
        
        # Return public URL
        public_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{CONTAINER_NAME}/{blob_path}"
        
        logger.info(f"Successfully uploaded PDF: {blob_path}")
        return public_url
        
    except AzureError as e:
        logger.error(f"Azure bills upload error: {e}")
        raise Exception(f"Azure bills upload error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error uploading PDF: {e}")
        raise Exception(f"PDF upload error: {e}")

def download_file_from_azure(file_url):
    """Download file from Azure Storage (replaces download_file_from_supabase)"""
    try:
        # Parse the URL to extract blob path
        parsed = urllib.parse.urlparse(file_url)
        path_parts = parsed.path.split('/')
        
        # Find the container name and extract the blob path
        container_index = -1
        for i, part in enumerate(path_parts):
            if part == CONTAINER_NAME:
                container_index = i
                break
        
        if container_index == -1:
            raise Exception("Container name not found in URL")
        
        blob_path = '/'.join(path_parts[container_index + 1:])
        
        # Get blob client
        blob_client = container_client.get_blob_client(blob_path)
        
        # Download blob
        download_stream = blob_client.download_blob()
        file_content = download_stream.readall()
        
        logger.info(f"Successfully downloaded file: {blob_path}")
        return file_content
        
    except AzureError as e:
        logger.error(f"Azure download error: {e}")
        raise Exception(f"Azure download error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error downloading file: {e}")
        raise Exception(f"Download error: {e}")

def get_csv_public_url(csv_url):
    """Get the public URL for a CSV file stored in Azure (replaces get_csv_public_url)"""
    try:
        # Parse the URL to extract blob path
        parsed = urllib.parse.urlparse(csv_url)
        path_parts = parsed.path.split('/')
        
        # Find the container name and extract the blob path
        container_index = -1
        for i, part in enumerate(path_parts):
            if part == CONTAINER_NAME:
                container_index = i
                break
        
        if container_index == -1:
            raise Exception("Container name not found in URL")
        
        blob_path = '/'.join(path_parts[container_index + 1:])
        
        # Return the public URL (same as input since it's already a public URL)
        return csv_url
        
    except Exception as e:
        logger.error(f"Error getting CSV public URL: {e}")
        raise Exception(f"CSV URL error: {e}")

def get_bills_folder_public_url(file_path):
    """Get the public URL for a file stored in the bills folder (replaces get_bills_bucket_public_url)"""
    try:
        # Ensure the path starts with the bills folder
        if not file_path.startswith(f"{BILLS_FOLDER}/"):
            file_path = f"{BILLS_FOLDER}/{file_path}"
        
        # Return public URL
        public_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{CONTAINER_NAME}/{file_path}"
        
        logger.info(f"Generated bills public URL: {public_url}")
        return public_url
        
    except Exception as e:
        logger.error(f"Error getting bills public URL: {e}")
        raise Exception(f"Bills URL error: {e}")

def download_from_bills_folder(file_path):
    """Download a file from the bills folder (replaces download_from_bills_bucket)"""
    try:
        # Ensure the path starts with the bills folder
        if not file_path.startswith(f"{BILLS_FOLDER}/"):
            file_path = f"{BILLS_FOLDER}/{file_path}"
        
        # Get blob client
        blob_client = container_client.get_blob_client(file_path)
        
        # Download blob
        download_stream = blob_client.download_blob()
        file_content = download_stream.readall()
        
        logger.info(f"Successfully downloaded from bills folder: {file_path}")
        return file_content
        
    except AzureError as e:
        logger.error(f"Azure bills download error: {e}")
        raise Exception(f"Azure bills download error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error downloading from bills folder: {e}")
        raise Exception(f"Bills download error: {e}")

def delete_file_from_azure(file_path, folder_type=None):
    """Delete a file from Azure Storage (replaces delete_file_from_bucket)"""
    try:
        # Determine the folder based on folder_type or file_path
        if folder_type == "credentials":
            if not file_path.startswith(f"{CREDENTIALS_FOLDER}/"):
                file_path = f"{CREDENTIALS_FOLDER}/{file_path}"
        elif folder_type == "bills":
            if not file_path.startswith(f"{BILLS_FOLDER}/"):
                file_path = f"{BILLS_FOLDER}/{file_path}"
        
        # Get blob client
        blob_client = container_client.get_blob_client(file_path)
        
        # Delete blob
        blob_client.delete_blob()
        
        logger.info(f"Successfully deleted file: {file_path}")
        return True
        
    except AzureError as e:
        logger.error(f"Azure delete error: {e}")
        raise Exception(f"Azure delete error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error deleting file: {e}")
        raise Exception(f"Delete error: {e}")

def list_files_in_azure(folder_type=None, folder_path=""):
    """List files in Azure Storage (replaces list_files_in_bucket)"""
    try:
        # Determine the folder to list
        if folder_type == "credentials":
            prefix = f"{CREDENTIALS_FOLDER}/"
        elif folder_type == "bills":
            prefix = f"{BILLS_FOLDER}/"
        else:
            prefix = folder_path
        
        # List blobs with prefix
        blobs = container_client.list_blobs(name_starts_with=prefix)
        blob_list = list(blobs)
        
        logger.info(f"Found {len(blob_list)} files in {prefix}")
        return blob_list
        
    except AzureError as e:
        logger.error(f"Azure list error: {e}")
        raise Exception(f"Azure list error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error listing files: {e}")
        raise Exception(f"List error: {e}")

def get_file_info(file_path, folder_type=None):
    """Get information about a file in Azure Storage (replaces get_file_info)"""
    try:
        # Determine the folder based on folder_type or file_path
        if folder_type == "credentials":
            if not file_path.startswith(f"{CREDENTIALS_FOLDER}/"):
                file_path = f"{CREDENTIALS_FOLDER}/{file_path}"
        elif folder_type == "bills":
            if not file_path.startswith(f"{BILLS_FOLDER}/"):
                file_path = f"{BILLS_FOLDER}/{file_path}"
        
        # Get blob client
        blob_client = container_client.get_blob_client(file_path)
        
        # Get blob properties
        properties = blob_client.get_blob_properties()
        
        file_info = {
            'name': properties.name,
            'size': properties.size,
            'content_type': properties.content_settings.content_type,
            'last_modified': properties.last_modified,
            'public_url': f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{CONTAINER_NAME}/{file_path}"
        }
        
        logger.info(f"Retrieved file info for: {file_path}")
        return file_info
        
    except AzureError as e:
        logger.error(f"Azure file info error: {e}")
        raise Exception(f"Azure file info error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error getting file info: {e}")
        raise Exception(f"File info error: {e}")

# Legacy compatibility - maintain the same function names as Supabase client
def upload_csv_to_supabase(file, filename):
    """Legacy function name for compatibility"""
    return upload_csv_to_azure(file, filename)

def upload_file_to_supabase(file_bytes, filename):
    """Legacy function name for compatibility"""
    return upload_file_to_azure(file_bytes, filename)

def upload_pdf_to_bills_bucket(file_bytes, filename, user_id):
    """Legacy function name for compatibility"""
    return upload_pdf_to_bills_folder(file_bytes, filename, user_id)

def download_file_from_supabase(file_url):
    """Legacy function name for compatibility"""
    return download_file_from_azure(file_url)

def get_bills_bucket_public_url(file_path):
    """Legacy function name for compatibility"""
    return get_bills_folder_public_url(file_path)

def download_from_bills_bucket(file_path):
    """Legacy function name for compatibility"""
    return download_from_bills_folder(file_path)

def delete_file_from_bucket(file_path, bucket_name=None):
    """Legacy function name for compatibility"""
    folder_type = None
    if bucket_name == "browser-use-cred":
        folder_type = "credentials"
    elif bucket_name == "bills":
        folder_type = "bills"
    return delete_file_from_azure(file_path, folder_type)

def list_files_in_bucket(bucket_name=None, folder_path=""):
    """Legacy function name for compatibility"""
    folder_type = None
    if bucket_name == "browser-use-cred":
        folder_type = "credentials"
    elif bucket_name == "bills":
        folder_type = "bills"
    return list_files_in_azure(folder_type, folder_path)
