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