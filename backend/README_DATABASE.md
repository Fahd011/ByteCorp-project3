# Database Setup Guide for ByteCorp

This guide will help you set up the database locally for the ByteCorp project.

## Prerequisites

1. **PostgreSQL Database**: You need a PostgreSQL database running locally or remotely
2. **Python Environment**: Python 3.8+ with virtual environment
3. **Environment Variables**: Configure your database connection

## Quick Setup

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy the example environment file
cp env.example .env

# Edit .env with your actual database credentials
# Example for local PostgreSQL:
DATABASE_URL=postgresql://username:password@localhost:5432/bytecorp_db
JWT_SECRET_KEY=your-secret-key-here
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
```

### 3. Run Database Setup
```bash
# Option 1: Use the setup script (recommended)
python setup_database.py

# Option 2: Use the migration script
python migrations.py

# Option 3: Use the management CLI
python manage.py init-db
```

## Database Schema

The application creates the following tables:

### Users Table
- `id` (UUID, Primary Key)
- `email` (String, Unique)
- `password_hash` (String)
- `created_at` (DateTime)

### Import Sessions Table
- `id` (UUID, Primary Key)
- `user_id` (UUID, Foreign Key to users.id)
- `csv_url` (String)
- `login_url` (String)
- `billing_url` (String)
- `status` (String, default: "idle")
- `created_at` (DateTime)

### Import Results Table
- `id` (UUID, Primary Key)
- `session_id` (UUID, Foreign Key to import_sessions.id)
- `email` (String)
- `status` (String)
- `error` (String)
- `file_url` (String)
- `created_at` (DateTime)

## Advanced Database Management

### Using Flask-Migrate (for schema changes)

If you need to make changes to the database schema:

```bash
# Initialize migrations (first time only)
flask db init

# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback last migration
flask db downgrade
```

### Using the Management CLI

```bash
# Initialize database
python manage.py init-db

# Create migration
python manage.py create-migration

# Upgrade database
python manage.py upgrade-db

# Downgrade database
python manage.py downgrade-db

# Reset database (WARNING: This will delete all data)
python manage.py reset-db
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check your `DATABASE_URL` in `.env`
   - Ensure PostgreSQL is running
   - Verify database exists and user has permissions

2. **Permission Denied**
   - Make sure your database user has CREATE, ALTER, DROP permissions
   - For local development, you might need to create the database first:
     ```sql
     CREATE DATABASE bytecorp_db;
     ```

3. **Missing Dependencies**
   - Run `pip install -r requirements.txt`
   - Ensure `psycopg2-binary` is installed for PostgreSQL

### Verification

After setup, you can verify the database is working:

```bash
# Start the Flask application
python app.py

# The application should start without database errors
# You can also check the database directly:
psql -d bytecorp_db -c "\dt"
```

## Production Considerations

For production deployment:

1. **Use Environment Variables**: Never hardcode database credentials
2. **Database Migrations**: Use proper migrations for schema changes
3. **Backup Strategy**: Implement regular database backups
4. **Connection Pooling**: Consider using connection pooling for better performance
5. **SSL**: Use SSL connections for production databases

## Support

If you encounter issues:

1. Check the error messages in the console
2. Verify your environment variables
3. Ensure PostgreSQL is running and accessible
4. Check the database logs for connection issues
