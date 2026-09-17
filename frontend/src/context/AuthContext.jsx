import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api, { getStoredToken, setStoredToken, clearStoredToken } from '../lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('exportos_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [organisation, setOrganisation] = useState(() => {
    const saved = localStorage.getItem('exportos_org');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => getStoredToken());
  const [isLoading, setIsLoading] = useState(true);

  // Sync state with storage and fetch latest profile
  const fetchCurrentUser = useCallback(async () => {
    const activeToken = getStoredToken();
    if (!activeToken) {
      setUser(null);
      setOrganisation(null);
      setToken(null);
      setIsLoading(false);
      return;
    }

    try {
      const data = await api.get('/auth/me');
      setUser(data.user);
      setOrganisation(data.organisation);
      localStorage.setItem('exportos_user', JSON.stringify(data.user));
      localStorage.setItem('exportos_org', JSON.stringify(data.organisation));
    } catch (err) {
      console.error('Failed to load active user session:', err);
      clearStoredToken();
      setUser(null);
      setOrganisation(null);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentUser();

    // Listen for global unauthorized events
    const handleUnauthorized = () => {
      setUser(null);
      setOrganisation(null);
      setToken(null);
    };

    window.addEventListener('exportos:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('exportos:unauthorized', handleUnauthorized);
    };
  }, [fetchCurrentUser]);

  // Login handler
  const login = async (email, password) => {
    const data = await api.post('/auth/login', { email, password });
    setStoredToken(data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    setOrganisation(data.organisation);
    localStorage.setItem('exportos_user', JSON.stringify(data.user));
    localStorage.setItem('exportos_org', JSON.stringify(data.organisation));
    return data;
  };

  // Register handler
  const register = async (payload) => {
    const data = await api.post('/auth/register', payload);
    setStoredToken(data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    setOrganisation(data.organisation);
    localStorage.setItem('exportos_user', JSON.stringify(data.user));
    localStorage.setItem('exportos_org', JSON.stringify(data.organisation));
    return data;
  };

  // Logout handler
  const logout = () => {
    clearStoredToken();
    setUser(null);
    setOrganisation(null);
    setToken(null);
  };

  const value = {
    user,
    organisation,
    token,
    isAuthenticated: !!token && !!user,
    isAdmin: user?.role === 'ADMIN',
    isLoading,
    login,
    register,
    logout,
    refreshUser: fetchCurrentUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
