import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { User } from "../types";

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string, user: User, expiresAt: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(
    localStorage.getItem("token")
  );

  useEffect(() => {
    // Check if token exists and is valid
    const storedToken = localStorage.getItem("token");
    const storedExpiresAt = localStorage.getItem("tokenExpiresAt");

    if (storedToken && storedExpiresAt) {
      const expiresAt = new Date(storedExpiresAt);
      const now = new Date();

      if (expiresAt > now) {
        // Token is still valid
        setToken(storedToken);
        const storedUser = localStorage.getItem("user");
        if (storedUser) {
          setUser(JSON.parse(storedUser));
        }

        // Set up automatic logout when token expires
        const timeUntilExpiry = expiresAt.getTime() - now.getTime();

        if (timeUntilExpiry > 0) {
          const logoutTimer = setTimeout(() => {
            logout();
          }, timeUntilExpiry);

          return () => clearTimeout(logoutTimer);
        }
      } else {
        // Token has expired, clear it
        logout();
      }
    }
  }, []);

  const login = (newToken: string, userData: User, expiresAt: string) => {
    localStorage.setItem("token", newToken);
    localStorage.setItem("tokenExpiresAt", expiresAt);
    localStorage.setItem("user", JSON.stringify(userData));

    setToken(newToken);
    setUser(userData);

    // Set up automatic logout - use UTC for consistent timezone handling
    const expiresAtDate = new Date(expiresAt);
    const now = new Date();
    const timeUntilExpiry = expiresAtDate.getTime() - now.getTime();

    if (timeUntilExpiry > 0) {
      setTimeout(() => {
        logout();
      }, timeUntilExpiry);
    } else {
      logout();
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("tokenExpiresAt");
    localStorage.removeItem("user");
    setToken(null);
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    token,
    login,
    logout,
    isAuthenticated: !!token,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
