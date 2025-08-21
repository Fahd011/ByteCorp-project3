# Sagility Backend

A FastAPI-based backend for billing automation with modular agent integration and cloud storage support.

## Features

- ✅ **User Authentication** - JWT-based authentication
- ✅ **Credential Management** - Upload CSV files with billing credentials
- ✅ **Agent Control** - Start/stop agents for each credential
- ✅ **PDF Management** - Upload and download billing PDFs
- ✅ **Scheduling** - Weekly automated job scheduling
- ✅ **Modular Architecture** - Easy agent and storage provider integration
- ✅ **Cloud Storage Ready** - Support for Azure Blob Storage and AWS S3

## Architecture

### Core Components

1. **Main Application** (`main.py`)
   - FastAPI application with all endpoints
   - Database models and migrations
   - Authentication and authorization

2. **Agent Service** (`agent_service.py`)
   - Abstract layer for agent operations
   - Easy integration of different agent types
   - Storage provider abstraction

3. **Configuration** (`config.py`)
   - Centralized configuration management
   - Environment variable support
   - Easy switching between providers

### Database Models

- `User` - User accounts and authentication
- `UserBillingCredential` - Billing credentials with metadata
- `ImportSession` - CSV upload sessions
- `ImportResult` - Agent execution results

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Node.js (for frontend)

### Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   # Database
   export DATABASE_URL="postgresql://user:password@localhost:5432/dbname"
   
   # Security
   export SECRET_KEY="your-secret-key"
   
   # Storage (optional - defaults to local)
   export STORAGE_PROVIDER="local"  # or "azure", "aws"
   
   # Agent type (optional - defaults to simulation)
   export AGENT_TYPE="simulation"  # or "selenium", "playwright"
   ```

3. **Run the application:**
   ```bash
   python main.py
   ```
   
## Agent Integration

### Current Agent Types

1. **Simulation Agent** (default)
   - Simulates agent work for testing
   - No external dependencies

2. **Selenium Agent** (future)
   - Browser automation with Selenium
   - Real web scraping capabilities

3. **Playwright Agent** (future)
   - Modern browser automation
   - Better performance and reliability

### Adding a New Agent Type

1. **Create agent class:**
   ```python
   class SeleniumAgent(AgentService):
       async def _execute_agent_work(self, credential):
           # Implement Selenium automation
           from selenium import webdriver
           driver = webdriver.Chrome()
           # ... automation logic
           driver.quit()
   ```

2. **Update configuration:**
   ```python
   AGENT_TYPE = "selenium"
   ```

3. **Register agent:**
   ```python
   # In agent_service.py
   if config.AGENT_TYPE == "selenium":
       agent_service = SeleniumAgent()
   ```

## Storage Integration

### Current Storage Providers

1. **Local Storage** (default)
   - Files stored in `./uploads/` directory
   - Simple file system operations

2. **Azure Blob Storage** (ready for implementation)
   - Cloud-based file storage
   - Scalable and reliable

3. **AWS S3** (ready for implementation)
   - Amazon S3 integration
   - High availability

### Adding Azure Storage

1. **Install Azure SDK:**
   ```bash
   pip install azure-storage-blob
   ```

2. **Set environment variables:**
   ```bash
   export STORAGE_PROVIDER="azure"
   export AZURE_STORAGE_CONNECTION_STRING="your-connection-string"
   export AZURE_STORAGE_CONTAINER="sagility-files"
   ```

3. **Implement Azure methods in AgentService:**
   ```python
   def _upload_to_azure(self, file_data, filename):
       from azure.storage.blob import BlobServiceClient
       # Implementation here
   ```

## API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /create-test-user` - Create test user (dev only)

### Credentials
- `POST /credentials/upload` - Upload CSV with credentials
- `GET /credentials` - Get all user credentials
- `POST /credentials/{id}/agent` - Control agent (RUN/STOPPED)
- `POST /credentials/{id}/upload_pdf` - Upload billing PDF
- `GET /credentials/{id}/download_pdf` - Download billing PDF
- `DELETE /credentials/{id}` - Delete credential

### Scheduling
- `POST /schedule/weekly` - Schedule weekly runs

### Utility
- `GET /health` - Health check
- `GET /sessions` - Get import sessions
- `GET /results/{session_id}` - Get session results

## Future Enhancements

### Planned Features

1. **Real Agent Integration**
   - Selenium/Playwright automation
   - Browser-based billing portal access
   - PDF generation and processing

2. **Cloud Storage**
   - Azure Blob Storage integration
   - AWS S3 integration
   - File versioning and backup

3. **Advanced Scheduling**
   - Custom cron expressions
   - Multiple schedule types
   - Schedule management UI

4. **Monitoring & Logging**
   - Agent execution logs
   - Performance metrics
   - Error tracking and alerting

5. **Multi-tenancy**
   - Organization-based access
   - User roles and permissions
   - Resource isolation

### Integration Points

1. **Agent Framework**
   - Easy plugin system for new agents
   - Standardized agent interface
   - Agent marketplace concept

2. **Storage Framework**
   - Pluggable storage providers
   - File lifecycle management
   - CDN integration

3. **Notification System**
   - Email notifications
   - Webhook support
   - Real-time updates

## Development

### Code Structure

```
backend/
├── main.py              # FastAPI application
├── config.py            # Configuration management
├── agent_service.py     # Agent abstraction layer
├── models.py            # Database models (if separated)
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

### Testing

```bash
# Run tests (when implemented)
pytest

# Run with coverage
pytest --cov=.
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

## Deployment

### Docker (recommended)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

```bash
# Production settings
export DATABASE_URL="postgresql://user:pass@host:5432/db"
export SECRET_KEY="your-production-secret"
export STORAGE_PROVIDER="azure"
export AZURE_STORAGE_CONNECTION_STRING="your-azure-connection"
export AGENT_TYPE="selenium"
export LOG_LEVEL="INFO"
```

## Support

For questions or issues:
1. Check the documentation
2. Review the code structure
3. Create an issue with detailed information

## License

This project is proprietary software. All rights reserved.
