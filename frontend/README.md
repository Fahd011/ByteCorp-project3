# ByteCorp Frontend

A React TypeScript frontend for the ByteCorp job management system.

## Features

- **Authentication**: Login/signup with JWT token management
- **Dashboard**: View and manage automation jobs
- **Job Management**: Create, run, stop, and delete jobs
- **File Upload**: Upload CSV files with login and billing URLs
- **Real-time Status**: Track job status and results
- **Responsive Design**: Modern, clean UI

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

3. The app will open at `http://localhost:3000`

## Backend Integration

This frontend connects to the Flask backend running on `http://localhost:5000`. Make sure the backend is running before using the frontend.

## API Endpoints Used

- `POST /auth/login` - User authentication
- `POST /auth/signup` - User registration
- `GET /api/jobs` - Get all jobs for user
- `POST /api/jobs` - Create new job
- `POST /api/jobs/{id}/run` - Run a job
- `POST /api/jobs/{id}/stop` - Stop a job
- `DELETE /api/jobs/{id}` - Delete a job
- `GET /api/jobs/{id}` - Get job details and results

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── Header.tsx     # App header with user info
│   ├── Sidebar.tsx    # Navigation sidebar
│   ├── Login.tsx      # Login/signup form
│   ├── ImportModal.tsx # Job creation modal
│   ├── JobCard.tsx    # Individual job display
│   ├── Layout.tsx     # Main layout wrapper
│   └── ProtectedRoute.tsx # Auth protection
├── pages/              # Page components
│   ├── Dashboard.tsx  # Main dashboard
│   └── Bills.tsx      # Bills page (placeholder)
├── contexts/           # React contexts
│   └── AuthContext.tsx # Authentication state
├── services/           # API services
│   └── api.ts         # API functions
├── types/              # TypeScript interfaces
│   └── index.ts       # Type definitions
└── App.tsx            # Main app component
```

## Usage

1. **Login**: Users are redirected to login page on first visit
2. **Dashboard**: View all jobs with their current status
3. **Create Job**: Click "Import New Job" to upload CSV and URLs
4. **Manage Jobs**: Run, stop, or delete jobs based on their status
5. **View Results**: Access job results when completed

## Development

- Built with React 18 and TypeScript
- Uses React Router for navigation
- Axios for API communication
- Context API for state management
- Inline styles for simplicity
