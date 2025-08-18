# Environment Configuration

## Backend URL Configuration

The frontend application uses environment variables to configure the backend API URL. This allows for easy deployment to different environments without hardcoding URLs.

### Environment Variables

Create a `.env` file in the `frontend` directory with the following variable:

```env
REACT_APP_API_BASE_URL=http://127.0.0.1:5000
```

### Available Environment Variables

- `REACT_APP_API_BASE_URL`: The base URL for the backend API (defaults to `http://127.0.0.1:5000` if not set)

### Environment-Specific Files

You can create environment-specific files for different deployment environments:

- `.env.development` - For development environment
- `.env.production` - For production environment
- `.env.local` - For local overrides (gitignored)

### Example Configurations

**Development:**
```env
REACT_APP_API_BASE_URL=http://127.0.0.1:5000
```

**Production:**
```env
REACT_APP_API_BASE_URL=https://your-production-api.com
```

**Staging:**
```env
REACT_APP_API_BASE_URL=https://your-staging-api.com
```

### Important Notes

1. **React Environment Variables**: All environment variables must be prefixed with `REACT_APP_` to be accessible in the React application.

2. **Restart Required**: After changing environment variables, you need to restart the development server for changes to take effect.

3. **Build Time**: Environment variables are embedded at build time, not runtime.

4. **Security**: Never commit sensitive information like API keys to version control. Use `.env.local` for local secrets.

### Usage in Code

The backend URL is automatically used in all API calls through the centralized `api.ts` service:

```typescript
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://127.0.0.1:5000";
```

All API calls use this base URL, so no additional configuration is needed in individual components.
