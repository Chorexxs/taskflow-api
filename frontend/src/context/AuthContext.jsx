import { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem('access_token'));
  const [refreshToken, setRefreshToken] = useState(() => localStorage.getItem('refresh_token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (accessToken) {
      api.users.me(accessToken)
        .then(data => {
          if (data.id) setUser(data);
          else logout();
        })
        .catch(() => logout())
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    if (accessToken) {
      localStorage.setItem('access_token', accessToken);
    } else {
      localStorage.removeItem('access_token');
    }
  }, [accessToken]);

  useEffect(() => {
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    } else {
      localStorage.removeItem('refresh_token');
    }
  }, [refreshToken]);

  const login = async (email, password) => {
    const data = await api.auth.login({ email, password });
    if (data.access_token) {
      setAccessToken(data.access_token);
      setRefreshToken(data.refresh_token);
      const user = await api.users.me(data.access_token);
      setUser(user);
      return user;
    }
    throw new Error(data.detail || 'Login failed');
  };

  const register = async (email, password) => {
    const data = await api.auth.register({ email, password });
    if (data.id) {
      return login(email, password);
    }
    throw new Error(data.detail || 'Registration failed');
  };

  const logout = () => {
    if (accessToken) {
      api.auth.logout(accessToken).catch(() => {});
    }
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
  };

  const getAuthHeader = () => ({ Authorization: `Bearer ${accessToken}` });

  return (
    <AuthContext.Provider value={{ user, accessToken, loading, login, register, logout, getAuthHeader }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
