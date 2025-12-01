import { createContext, useContext, useState, useEffect, ReactNode, useMemo } from "react";
import * as React from "react";
import { authAPI } from "@/services/api";
import { LoginCredentials, RegisterData, Token, User } from "@/types";
import { extractErrorMessage } from "@/utils/errorHandling";

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  readonly children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Check for existing token on mount
  useEffect(() => {
    const storedToken = localStorage.getItem("token");
    if (storedToken) {
      setToken(storedToken);
      // Optionally decode token to get user info
      try {
        const payload = JSON.parse(atob(storedToken.split(".")[1]));
        setUser({ email: payload.sub || payload.email });
      } catch (e) {
        // Token might not be JWT, that's okay - use default user
        console.debug("Token parsing failed, using default user:", e);
        setUser({ email: "user" });
      }
    }
    setLoading(false);
  }, []);

  const login = async (credentials: LoginCredentials) => {
    try {
      const response = await authAPI.login(credentials);
      const tokenData: Token = response.data;
      const accessToken = tokenData.access_token;
      
      localStorage.setItem("token", accessToken);
      setToken(accessToken);
      
      // Decode token to get user info
      try {
        const payload = JSON.parse(atob(accessToken.split(".")[1]));
        setUser({ email: payload.sub || payload.email || credentials.email });
      } catch (e) {
        // Token parsing failed, use email from credentials
        console.debug("Token parsing failed, using credentials email:", e);
        setUser({ email: credentials.email });
      }
    } catch (error: unknown) {
      throw new Error(extractErrorMessage(error, "Login failed"));
    }
  };

  const register = async (data: RegisterData) => {
    try {
      const response = await authAPI.register(data);
      const tokenData: Token = response.data;
      const accessToken = tokenData.access_token;
      
      localStorage.setItem("token", accessToken);
      setToken(accessToken);
      setUser({ email: data.email });
    } catch (error: unknown) {
      throw new Error(extractErrorMessage(error, "Registration failed"));
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
    // Clear any React Query cache if needed
  };

  // Memoize context value to prevent unnecessary re-renders
  const contextValue = useMemo(
    () => ({
      user,
      token,
      loading,
      login,
      register,
      logout,
      isAuthenticated: !!token,
    }),
    [user, token, loading, login, register, logout]
  );

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

