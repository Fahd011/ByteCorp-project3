// AuthContext with proper TypeScript types
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authAPI } from '../services/api';
import { AuthContextType, User, LoginCredentials, RegisterData } from '../types';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      // You could verify the token here if needed
      setUser({ id: 'temp', email: 'user@example.com', created_at: new Date().toISOString() }); // For now, just set basic user info
    }
    setLoading(false);
  }, [token]);

  const login = async (credentials: LoginCredentials) => {
    try {
      const response = await authAPI.login(credentials);
      const { access_token } = response.data;
      
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser({ id: 'temp', email: credentials.email, created_at: new Date().toISOString() });
      
      return { success: true };
    } catch (error: any) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Login failed' 
      };
    }
  };

  const register = async (userData: RegisterData) => {
    try {
      const response = await authAPI.register(userData);
      const { access_token } = response.data;
      
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser({ id: 'temp', email: userData.email, created_at: new Date().toISOString() });
      
      return { success: true };
    } catch (error: any) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Registration failed' 
      };
    }
  };

  const createTestUser = async () => {
    try {
      const response = await authAPI.createTestUser();
      return { success: true, data: response.data };
    } catch (error: any) {
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Failed to create test user' 
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    loading,
    login,
    register,
    logout,
    createTestUser,
    isAuthenticated: !!token,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
