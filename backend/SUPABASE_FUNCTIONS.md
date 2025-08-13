# Supabase Functions Reference

All Supabase operations are centralized in `supabase_client.py` for easier management and consistency.

## File Upload Functions

### `upload_csv_to_supabase(file, filename)`

- **Purpose**: Upload CSV files to the main bucket
- **Parameters**:
  - `file`: Flask FileStorage object
  - `filename`: Name for the file in storage
- **Returns**: Public URL of the uploaded file
- **Bucket**: `browser-use-cred`

### `upload_file_to_supabase(file_bytes, filename)`

- **Purpose**: Upload any file bytes to the main bucket
- **Parameters**:
  - `file_bytes`: File content as bytes
  - `filename`: Name for the file in storage
- **Returns**: Public URL of the uploaded file
- **Bucket**: `browser-use-cred`

### `upload_pdf_to_bills_bucket(file_bytes, filename, user_id)`

- **Purpose**: Upload PDF files to bills bucket with user-specific folders
- **Parameters**:
  - `file_bytes`: PDF content as bytes
  - `filename`: Name for the PDF file
  - `user_id`: User ID for folder organization
- **Returns**: Public URL of the uploaded PDF
- **Bucket**: `bills`
- **Folder Structure**: `{user_id}/{filename}`

## File Download Functions

### `download_file_from_supabase(file_url)`

- **Purpose**: Download files from the main bucket
- **Parameters**: `file_url`: Full Supabase URL of the file
- **Returns**: File content as bytes
- **Bucket**: `browser-use-cred`

### `download_from_bills_bucket(file_path)`

- **Purpose**: Download files from the bills bucket
- **Parameters**: `file_path`: Path to file within the bills bucket
- **Returns**: File content as bytes
- **Bucket**: `bills`

## URL Generation Functions

### `get_csv_public_url(csv_url)`

- **Purpose**: Get public URL for CSV files
- **Parameters**: `csv_url`: Full Supabase URL
- **Returns**: Public URL for the file
- **Bucket**: `browser-use-cred`

### `get_bills_bucket_public_url(file_path)`

- **Purpose**: Get public URL for files in bills bucket
- **Parameters**: `file_path`: Path to file within the bills bucket
- **Returns**: Public URL for the file
- **Bucket**: `bills`

## File Management Functions

### `delete_file_from_bucket(file_path, bucket_name=None)`

- **Purpose**: Delete files from any bucket
- **Parameters**:
  - `file_path`: Path to file within the bucket
  - `bucket_name`: Optional bucket name (defaults to main bucket)
- **Returns**: True if successful
- **Buckets**: Any specified bucket or main bucket

### `list_files_in_bucket(bucket_name=None, folder_path="")`

- **Purpose**: List files in a bucket
- **Parameters**:
  - `bucket_name`: Optional bucket name (defaults to main bucket)
  - `folder_path`: Optional folder path within the bucket
- **Returns**: List of files
- **Buckets**: Any specified bucket or main bucket

### `get_file_info(file_path, bucket_name=None)`

- **Purpose**: Get information about a file (placeholder for future implementation)
- **Parameters**:
  - `file_path`: Path to file within the bucket
  - `bucket_name`: Optional bucket name (defaults to main bucket)
- **Returns**: Public URL (currently just verifies file exists)
- **Buckets**: Any specified bucket or main bucket

## Configuration

### Bucket Names

- **Main Bucket**: `browser-use-cred` (for CSV files and general uploads)
- **Bills Bucket**: `bills` (for PDF bills with user-specific folders)

### Error Handling

All functions include proper error handling and will raise exceptions with descriptive error messages if Supabase operations fail.

## Usage Example

```python
from supabase_client import upload_pdf_to_bills_bucket, download_from_bills_bucket

# Upload a PDF
pdf_url = upload_pdf_to_bills_bucket(pdf_bytes, "bill.pdf", user_id)

# Download a PDF
pdf_content = download_from_bills_bucket("user123/bill.pdf")
```

## Benefits of Centralization

1. **Consistent Error Handling**: All Supabase operations use the same error handling patterns
2. **Easy Maintenance**: Changes to Supabase logic only need to be made in one place
3. **Reusability**: Functions can be easily imported and used across different modules
4. **Testing**: Easier to mock and test Supabase operations
5. **Configuration Management**: Bucket names and other settings are centralized
