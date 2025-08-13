# Job Scheduling with APScheduler

This project now supports automatic job scheduling using APScheduler. You can configure jobs to run automatically on a weekly, daily, or custom schedule.

## Features

- **Weekly Scheduling**: Run jobs on specific days of the week at specified times
- **Daily Scheduling**: Run jobs every day at a specific time
- **Custom Cron**: Use custom cron expressions for advanced scheduling
- **Visual Indicators**: See which jobs are scheduled and when they'll run next
- **Automatic Execution**: Jobs run automatically without manual intervention

## Setup

### 1. Install Dependencies

The required dependencies are already included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 2. Database Migration

Run the database migration script to add scheduling fields:

```bash
cd backend
python add_scheduling_fields.py
```

**Note**: Update the `DATABASE_URL` in the migration script to match your database configuration.

### 3. Start the Backend

The backend now includes APScheduler and will automatically handle scheduled jobs:

```bash
cd backend
python app.py
```

## Usage

### Creating a Scheduled Job

1. **Open the Create Job Modal**: Click "Create New Job" in the dashboard
2. **Fill in Job Details**: Provide CSV file, login URL, and billing URL
3. **Enable Scheduling**: Check the "Schedule this job to run automatically" checkbox
4. **Configure Schedule**:
   - **Weekly**: Choose day of week, hour, and minute
   - **Daily**: Choose hour and minute
   - **Custom**: Enter a cron expression (e.g., `0 9 * * 1` for Monday 9:00 AM)
5. **Create Job**: Click "Create Job" to save the scheduled job

### Schedule Types

#### Weekly

- **Example**: Every Monday at 9:00 AM
- **Use Case**: Regular weekly data collection

#### Daily

- **Example**: Every day at 2:00 AM
- **Use Case**: Daily maintenance or data updates

#### Custom Cron

- **Format**: `minute hour day month day-of-week`
- **Examples**:
  - `0 9 * * 1` = Monday 9:00 AM
  - `0 2 * * *` = Every day at 2:00 AM
  - `0 12 * * 1,3,5` = Monday, Wednesday, Friday at 12:00 PM

### Managing Scheduled Jobs

- **View Schedule**: Scheduled jobs show a 📅 badge and schedule information
- **Next Run**: See when the job will run next
- **Last Run**: Track when the job last ran automatically
- **Status**: Jobs maintain their normal status (idle, running, completed, etc.)

## Backend Implementation

### Key Components

1. **APScheduler**: Background scheduler for job execution
2. **Database Fields**: New fields in `ImportSession` model for scheduling
3. **Scheduling Logic**: Functions to calculate next run times and manage schedules
4. **Integration**: Seamless integration with existing job execution system

### Database Schema

The `import_sessions` table now includes:

- `is_scheduled`: Boolean flag for scheduled jobs
- `schedule_type`: Type of schedule (weekly, daily, monthly, custom)
- `schedule_config`: JSON configuration for schedule details
- `next_run`: Timestamp of next scheduled execution
- `last_scheduled_run`: Timestamp of last automatic execution

### API Endpoints

- **POST /api/jobs**: Create job with optional scheduling
- **GET /api/jobs**: List jobs with scheduling information
- **POST /api/jobs/{id}/run**: Manually run a job (scheduled jobs can still be run manually)

## Troubleshooting

### Common Issues

1. **Jobs Not Running**:

   - Check backend logs for scheduler errors
   - Verify APScheduler is running (`scheduler.start()`)
   - Check database connection and scheduling fields

2. **Schedule Not Saving**:

   - Verify database migration completed successfully
   - Check frontend form validation
   - Review backend error logs

3. **Time Zone Issues**:
   - All times are stored in UTC
   - Frontend displays times in local timezone
   - Consider timezone differences when scheduling

### Logs

The backend logs scheduling activities:

- Job scheduling success/failure
- Scheduled job execution
- Next run time calculations
- Scheduler errors

## Security Considerations

- **Authentication**: All scheduling operations require valid JWT tokens
- **User Isolation**: Users can only schedule their own jobs
- **Input Validation**: Schedule configurations are validated before saving
- **Rate Limiting**: Consider implementing rate limits for job creation

## Future Enhancements

- **Pause/Resume**: Temporarily disable scheduled jobs
- **Edit Schedules**: Modify existing job schedules
- **Bulk Operations**: Schedule multiple jobs at once
- **Advanced Cron**: More sophisticated cron expression support
- **Email Notifications**: Notify users of scheduled job results
- **Retry Logic**: Automatic retry for failed scheduled jobs

## Support

For issues or questions about job scheduling:

1. Check the backend logs for error messages
2. Verify database schema is up to date
3. Test with simple schedules first
4. Review the APScheduler documentation for advanced features
