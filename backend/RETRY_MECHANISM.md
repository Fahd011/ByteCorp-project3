# Retry Mechanism Implementation

## Overview

This implementation adds a robust retry mechanism to the bill download process. Each credential will be retried up to 5 times before being marked as failed, with proper error tracking and user feedback.

## Features

### 1. Retry Logic
- **Max Retries**: 5 attempts per credential
- **Retry Delay**: 10 seconds between attempts
- **Individual Processing**: Each credential is processed independently
- **Error Tracking**: Specific error messages for each failure

### 2. Database Changes
- **retry_attempts**: Number of attempts made (0-5)
- **final_error**: Final error message after all retries exhausted

### 3. Frontend Enhancements
- **Retry Information**: Shows number of attempts made
- **Error Display**: Clear error messages with color coding
- **Status Indicators**: Visual status indicators (success/error)

## Implementation Details

### Backend Changes

#### 1. Database Model (`models.py`)
```python
class ImportResult(db.Model):
    # ... existing fields ...
    retry_attempts = db.Column(db.Integer, default=0)
    final_error = db.Column(db.String)
```

#### 2. Browser Script (`browser.py`)
- `process_single_email_with_retry()`: Main retry function
- `write_real_time_result()`: Real-time result tracking
- 5-attempt retry loop with 10-second delays

#### 3. Agent Runner (`agent_runner.py`)
- Updated to handle retry information
- Stores retry attempts and final errors in database

#### 4. API Routes (`job_routes.py`)
- Enhanced to return retry information
- Updated both `/details` and `/realtime` endpoints

### Frontend Changes

#### 1. Types (`types/index.ts`)
```typescript
export interface JobDetailResult {
  // ... existing fields ...
  retry_attempts?: number;
  final_error?: string;
}
```

#### 2. Bills Page (`pages/Bills.tsx`)
- Enhanced display with retry information
- Color-coded status indicators
- Retry attempt count display

## Setup Instructions

### 1. Database Migration
Run the migration script to add new columns:

```bash
cd backend
python add_retry_fields.py
```

### 2. Verify Installation
Check that the new columns were added:

```sql
-- Check table structure
\d import_results

-- Should show:
-- retry_attempts | integer | default 0
-- final_error    | text    | 
```

## Usage

### Normal Operation
1. Upload CSV with credentials
2. Start job processing
3. System automatically retries failed downloads
4. View results with retry information

### Error Scenarios Handled
- **Network Timeouts**: Retried automatically
- **Login Failures**: Retried with fresh browser session
- **Website Loading Issues**: Retried with delays
- **Browser Automation Errors**: Retried with new browser instance

### Frontend Display
- **Success**: Green status with attempt count
- **Failure**: Red status with error message and attempt count
- **Retry Info**: Shows "X attempts" in display name

## Configuration

### Retry Settings
- **Max Attempts**: 5 (configurable in `browser.py`)
- **Delay Between Attempts**: 10 seconds (configurable)
- **Timeout Per Attempt**: 5 minutes (existing)

### Customization
To change retry settings, modify in `browser.py`:

```python
async def process_single_email_with_retry(email, password, user_id, login_url, billing_url, downloads_folder, max_retries=5):
    # Change max_retries parameter
    # Change await asyncio.sleep(10) for different delay
```

## Monitoring

### Log Messages
- `[EMAIL] Processing: email@example.com (Attempt 1/5)`
- `[RETRY] Failed to process email@example.com on attempt 1`
- `[SUCCESS] Successfully processed email@example.com on attempt 3`
- `[FAILED] All 5 attempts failed for email@example.com`

### Database Tracking
- `retry_attempts`: Number of attempts made
- `final_error`: Final error message after all retries
- `status`: 'success' or 'error'
- `error`: Current error message

## Benefits

1. **Improved Success Rate**: Handles temporary issues automatically
2. **Better User Experience**: Clear feedback on retry attempts
3. **Error Transparency**: Specific error messages for debugging
4. **Resilient Processing**: Continues processing other credentials even if some fail
5. **Audit Trail**: Complete history of retry attempts and failures

## Troubleshooting

### Common Issues

1. **Migration Fails**: Ensure database is accessible and user has ALTER permissions
2. **Retry Not Working**: Check browser script logs for retry messages
3. **Frontend Not Showing Retry Info**: Verify API responses include retry_attempts field

### Debug Commands
```bash
# Check database structure
python -c "from migrations import app, db; from models.models import ImportResult; app.app_context().push(); print(ImportResult.__table__.columns.keys())"

# Test retry mechanism
# Run a job with known failing credentials to see retry behavior
```
