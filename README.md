# ByteCorp - Automation Job Management System

A full-stack web application for managing automated browser tasks with a React TypeScript frontend and Flask Python backend.

## 🚀 Features

### Backend (Flask + Python)
- **Authentication**: JWT-based user authentication
- **Job Management**: Create, run, stop, and delete automation jobs
- **File Upload**: CSV file upload to Supabase storage
- **Browser Automation**: Playwright-based web automation
- **Database**: PostgreSQL with SQLAlchemy ORM
- **API**: RESTful API with proper error handling

### Frontend (React + TypeScript)
- **Modern UI**: Clean, responsive design
- **Authentication**: Login/signup with token management
- **Dashboard**: Real-time job status monitoring
- **Job Management**: Intuitive job creation and control
- **File Upload**: Drag-and-drop CSV upload
- **Real-time Updates**: Live status updates

## 📁 Project Structure

```
python-project-bytcorp/
├── ByteCorp-project3/          # Backend (Flask)
│   ├── backend/
│   │   ├── app.py             # Main Flask application
│   │   ├── routes/            # API routes
│   │   ├── models/            # Database models
│   │   ├── agent_runner.py    # Browser automation
│   │   └── supabase_client.py # File storage
│   ├── requirements.txt       # Python dependencies
│   └── config.json           # Configuration
├── frontend/                  # Frontend (React)
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/           # Page components
│   │   ├── services/        # API services
│   │   ├── contexts/        # React contexts
│   │   └── types/          # TypeScript types
│   └── package.json         # Node dependencies
└── start_app.py             # Startup script
```

## 🛠️ Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL database
- Supabase account

### 1. Backend Setup

```bash
# Navigate to backend directory
cd ByteCorp-project3

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database and Supabase credentials

# Initialize database
python -c "from backend.db import db; from backend.app import app; app.app_context().push(); db.create_all()"
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

### 3. Quick Start (Both Servers)

```bash
# From project root
python start_app.py
```

This will start both backend (port 5000) and frontend (port 3000) servers.

## 🔧 Configuration

### Backend Environment Variables (.env)
```
DATABASE_URL=postgresql://user:password@localhost/dbname
JWT_SECRET_KEY=your-secret-key
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
```

### Frontend Configuration
The frontend is configured to connect to `http://localhost:5000` for the backend API.

## 📖 API Documentation

### Authentication
- `POST /auth/login` - User login
- `POST /auth/signup` - User registration

### Jobs
- `GET /api/jobs` - Get all jobs for user
- `POST /api/jobs` - Create new job (multipart form)
- `POST /api/jobs/{id}/run` - Run a job
- `POST /api/jobs/{id}/stop` - Stop a job
- `DELETE /api/jobs/{id}` - Delete a job
- `GET /api/jobs/{id}` - Get job details and results

## 🎯 Usage Workflow

1. **Login**: Users authenticate with email/password
2. **Create Job**: Upload CSV file with login and billing URLs
3. **Run Job**: Start the automation process
4. **Monitor**: Track job status in real-time
5. **Results**: View and download generated files
6. **Manage**: Stop or delete jobs as needed

## 🔄 Job Lifecycle

1. **Idle**: Job created, ready to run
2. **Running**: Automation in progress
3. **Completed**: Job finished successfully
4. **Stopped**: Job manually stopped
5. **Error**: Job failed with error

## 🛡️ Security Features

- JWT token authentication
- CORS protection
- Input validation
- SQL injection prevention
- File upload security

## 🚀 Deployment

### Backend Deployment
```bash
# Production setup
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 backend.app:app
```

### Frontend Deployment
```bash
# Build for production
npm run build

# Serve with nginx or similar
```

## 🧪 Testing

### Backend Tests
```bash
cd ByteCorp-project3
python -m pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the documentation
2. Review existing issues
3. Create a new issue with detailed information

---

**ByteCorp** - Streamlining automation workflows with modern web technology.
