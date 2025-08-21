# Sagility Frontend

A modern React frontend for the Sagility billing automation platform.

## 🚀 Features

- **Modern React 18** with hooks and functional components
- **Clean Architecture** with organized folder structure
- **JWT Authentication** with protected routes
- **Responsive Design** with modern UI/UX
- **Real-time Updates** with toast notifications
- **File Upload** for CSV credentials
- **Session Management** with detailed results
- **Agent Control** for running/stopping automation

## 📁 Project Structure

```
src/
├── components/          # Reusable UI components
│   └── Navigation.js   # Sidebar navigation
├── context/            # React context providers
│   └── AuthContext.js  # Authentication state management
├── pages/              # Page components
│   ├── Login.js        # Login page
│   ├── Register.js     # Registration page
│   ├── Dashboard.js    # Main dashboard
│   ├── Credentials.js  # Credentials management
│   └── Sessions.js     # Import sessions
├── services/           # API services
│   └── api.js         # Axios configuration and API calls
├── styles/            # CSS styles
│   ├── index.css      # Global styles
│   └── App.css        # App-specific styles
├── utils/             # Utility functions
│   └── helpers.js     # Helper functions
├── App.js             # Main app component
└── index.js           # React entry point
```

## 🛠️ Tech Stack

- **React 18** - UI library
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **React Hot Toast** - Toast notifications
- **Lucide React** - Icon library
- **CSS3** - Styling (no external UI libraries)

## 🚀 Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- Backend API running on `http://localhost:8000`

### Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm start
   ```

3. **Open your browser:**
   Navigate to `http://localhost:3000`

## 📋 Available Scripts

- `npm start` - Start development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm eject` - Eject from Create React App

## 🔐 Authentication

The app uses JWT tokens for authentication:

- **Login**: `/login` - User authentication
- **Register**: `/register` - User registration
- **Protected Routes**: All main pages require authentication
- **Auto Logout**: Token expiration handling

## 📊 Features Overview

### Dashboard
- Overview statistics
- Quick action buttons
- Recent activity feed

### Credentials Management
- CSV file upload
- URL configuration (login/billing)
- Agent control (start/stop)
- Bulk scheduling
- Status monitoring

### Sessions
- Import session history
- Detailed results view
- Error tracking
- File downloads

## 🎨 UI Components

### Buttons
- Primary, Secondary, Success, Danger variants
- Loading states
- Icon support

### Forms
- Input validation
- Error handling
- Loading states

### Tables
- Responsive design
- Status badges
- Action buttons

### Cards
- Clean layout
- Shadow effects
- Responsive grid

## 🔧 Configuration

### API Configuration
The app automatically connects to the backend at `http://localhost:8000`. To change this:

1. Create a `.env` file in the root directory
2. Add: `REACT_APP_API_URL=your_backend_url`

### Proxy Configuration
The app includes a proxy configuration in `package.json` for development:
```json
{
  "proxy": "http://localhost:8000"
}
```

## 📱 Responsive Design

The app is fully responsive and works on:
- Desktop (1200px+)
- Tablet (768px - 1199px)
- Mobile (< 768px)

## 🚀 Deployment

### Build for Production
```bash
npm run build
```

### Deploy to Static Hosting
The `build` folder contains the production-ready files that can be deployed to:
- Netlify
- Vercel
- AWS S3
- GitHub Pages

## 🔍 Development

### Code Style
- Functional components with hooks
- Consistent naming conventions
- Proper error handling
- Loading states for all async operations

### State Management
- React Context for global state (auth)
- Local state for component-specific data
- No external state management libraries

### Error Handling
- Toast notifications for user feedback
- Graceful error fallbacks
- Loading states during operations

## 🤝 Contributing

1. Follow the existing code structure
2. Use functional components and hooks
3. Add proper error handling
4. Include loading states
5. Test on different screen sizes

## 📄 License

This project is part of the Sagility billing automation platform.
