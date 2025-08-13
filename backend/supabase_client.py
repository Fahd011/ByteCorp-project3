from supabase import create_client
from config import Config

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

BUCKET = "browser-use-cred"  # Change as needed
BILLS_BUCKET = "bills"  # New bucket for PDF bills

def upload_csv_to_supabase(file, filename):
    # file: Flask FileStorage object
    file_bytes = file.read()  # Read the file contents as bytes
    res = supabase.storage.from_(BUCKET).upload(filename, file_bytes)
    if hasattr(res, 'error') and res.error:
        raise Exception(f"Supabase upload error: {res.error}")
    return supabase.storage.from_(BUCKET).get_public_url(filename)

def upload_file_to_supabase(file_bytes, filename):
    res = supabase.storage.from_(BUCKET).upload(filename, file_bytes)
    if hasattr(res, 'error') and res.error:
        raise Exception(f"Supabase upload error: {res.error}")
    return supabase.storage.from_(BUCKET).get_public_url(filename)

def upload_pdf_to_bills_bucket(file_bytes, filename, user_id):
    """Upload PDF to bills bucket with user-specific folder structure"""
    # Create user-specific folder structure: {user_id}/{filename}
    user_filename = f"{user_id}/{filename}"
    
    # Upload with explicit content type for PDF
    res = supabase.storage.from_(BILLS_BUCKET).upload(
        user_filename, 
        file_bytes,
        {
            "content-type": "application/pdf",
            "upsert": "true"
        }
    )
    
    if hasattr(res, 'error') and res.error:
        raise Exception(f"Supabase bills upload error: {res.error}")
    
    public_url = supabase.storage.from_(BILLS_BUCKET).get_public_url(user_filename)
    
    return public_url

def download_file_from_supabase(file_url):
    import urllib.parse
    parsed = urllib.parse.urlparse(file_url)
    path = parsed.path.split(f"/{BUCKET}/")[-1]
    res = supabase.storage.from_(BUCKET).download(path)
    if hasattr(res, 'error') and res.error:
        raise Exception(f"Supabase download error: {res.error}")
    return res

def get_csv_public_url(csv_url):
    """Get the public URL for a CSV file stored in Supabase"""
    import urllib.parse
    parsed = urllib.parse.urlparse(csv_url)
    path = parsed.path.split(f"/{BUCKET}/")[-1]
    return supabase.storage.from_(BUCKET).get_public_url(path)

def get_bills_bucket_public_url(file_path):
    """Get the public URL for a file stored in the bills bucket"""
    try:
        return supabase.storage.from_(BILLS_BUCKET).get_public_url(file_path)
    except Exception as e:
        raise Exception(f"Supabase bills bucket public URL error: {e}")

def download_from_bills_bucket(file_path):
    """Download a file from the bills bucket"""
    try:
        response = supabase.storage.from_(BILLS_BUCKET).download(file_path)
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Supabase bills download error: {response.error}")
        return response
    except Exception as e:
        raise Exception(f"Supabase bills bucket download error: {e}")

def delete_file_from_bucket(file_path, bucket_name=None):
    """Delete a file from a specified bucket (defaults to main BUCKET)"""
    try:
        bucket = bucket_name or BUCKET
        res = supabase.storage.from_(bucket).remove([file_path])
        if hasattr(res, 'error') and res.error:
            raise Exception(f"Supabase delete error: {res.error}")
        return True
    except Exception as e:
        raise Exception(f"Supabase delete error: {e}")

def list_files_in_bucket(bucket_name=None, folder_path=""):
    """List files in a specified bucket (defaults to main BUCKET)"""
    try:
        bucket = bucket_name or BUCKET
        res = supabase.storage.from_(bucket).list(folder_path)
        if hasattr(res, 'error') and res.error:
            raise Exception(f"Supabase list error: {res.error}")
        return res
    except Exception as e:
        raise Exception(f"Supabase list error: {e}")

def get_file_info(file_path, bucket_name=None):
    """Get information about a file in a specified bucket"""
    try:
        bucket = bucket_name or BUCKET
        # Note: Supabase doesn't have a direct "get file info" method
        # This is a placeholder for future implementation
        # For now, we can try to get the public URL to verify the file exists
        return supabase.storage.from_(bucket).get_public_url(file_path)
    except Exception as e:
        raise Exception(f"Supabase file info error: {e}")