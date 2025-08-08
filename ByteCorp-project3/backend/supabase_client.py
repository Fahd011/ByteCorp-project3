from supabase import create_client
from backend.config import Config

supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

BUCKET = "browser-use-cred"  # Change as needed

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

def download_file_from_supabase(file_url):
    import urllib.parse
    parsed = urllib.parse.urlparse(file_url)
    path = parsed.path.split(f"/{BUCKET}/")[-1]
    res = supabase.storage.from_(BUCKET).download(path)
    if hasattr(res, 'error') and res.error:
        raise Exception(f"Supabase download error: {res.error}")
    return res