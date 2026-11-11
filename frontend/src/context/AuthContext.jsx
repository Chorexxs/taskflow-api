/**
 * TaskFlow Frontend - Authentication Context
 * 
 * This module provides authentication state management for the application.
 * It uses React Context to provide authentication status and methods
 * to all components in the application.
 * 
 * Features:
 * - Automatic token storage in localStorage
 * - Session persistence across page refreshes
 * - Login, logout, and registration methods
 * - Automatic user profile fetching on authentication
 * 
 * The context provides:
 * - user: Current authenticated user object (null if not authenticated)
 * - accessToken: JWT access token for API requests
 * - refreshToken: JWT refresh token for token refresh
 * - loading: Boolean indicating initial auth check in progress
 * - login(email, password): Authenticate user
 * - register(email, password): Create new account
 * - logout(): Clear session and tokens
 * - getAuthHeader(): Get Authorization header object
 * 
 * Usage:
 * import { useAuth } from './context/auth-context';
 * 
 * function MyComponent() {
 *   const { user, logout } = useAuth();
 *   // Use user data or logout function
 * }
 */

import { useCallback, useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import { AuthContext, getJwtExpiry } from './auth-context';

/**
 * Authentication provider component.
 * Wraps the application to provide authentication functionality.
 * 
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Child components
 * @returns {JSX.Element} AuthProvider wrapper
 * 
 * @example
 * <AuthProvider>
 *   <App />
 * </AuthProvider>
 */
export function AuthProvider({ children }) {
  // Current authenticated user
  const [user, setUser] = useState(null);
  
  // JWT access token (persisted in localStorage)
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem('access_token'));
  
  // JWT refresh token (persisted in localStorage)
  const [refreshToken, setRefreshToken] = useState(() => localStorage.getItem('refresh_token'));
  
  // Loading state during initial auth check
  const [loading, setLoading] = useState(true);
  const queryClient = useQueryClient();

  /**
   * Clear the local session without a network round-trip. Used when the
   * session is already invalid (expired/revoked token), so there is nothing to
   * revoke server-side.
   */
  const clearSession = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
    localStorage.removeItem('user_id');
    // Do not keep another user's teams/tasks visible in the same tab.
    queryClient.clear();
  }, [queryClient]);

  /**
   * Effect: Validate token and fetch user on mount/token change
   * Runs when accessToken changes to validate the session
   */
  useEffect(() => {
    if (accessToken) {
      api.users.me(accessToken)
        .then(data => {
          if (data.id) {
            setUser(data);
          } else {
            clearSession();
          }
        })
        .catch(() => clearSession())
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [accessToken, clearSession]);

  /**
   * Effect: Persist accessToken to localStorage
   * Runs whenever accessToken changes
   */
  useEffect(() => {
    if (accessToken) {
      localStorage.setItem('access_token', accessToken);
    } else {
      localStorage.removeItem('access_token');
    }
  }, [accessToken]);

  /**
   * Effect: Persist refreshToken to localStorage
   * Runs whenever refreshToken changes
   */
  useEffect(() => {
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    } else {
      localStorage.removeItem('refresh_token');
    }
  }, [refreshToken]);

  /**
   * Effect: Keep tabs in sync. Refresh rotation invalidates the previous
   * token, so every tab must adopt the newest pair written by whichever tab
   * refreshed first.
   */
  useEffect(() => {
    const syncSession = (event) => {
      if (event.storageArea && event.storageArea !== localStorage) return;
      if (event.key === 'access_token') {
        setAccessToken(event.newValue);
        if (!event.newValue) setUser(null);
      }
      if (event.key === 'refresh_token') setRefreshToken(event.newValue);
    };

    window.addEventListener('storage', syncSession);
    return () => window.removeEventListener('storage', syncSession);
  }, []);

  /**
   * Effect: Adopt sessions refreshed by the API client (same tab) and clear
   * state when the client detects an unrecoverable 401.
   */
  useEffect(() => {
    const onSession = (event) => {
      if (event.detail?.access_token) setAccessToken(event.detail.access_token);
      if (event.detail?.refresh_token) setRefreshToken(event.detail.refresh_token);
    };
    const onLogout = () => {
      setUser(null);
      setAccessToken(null);
      setRefreshToken(null);
      localStorage.removeItem('user_id');
      queryClient.clear();
    };

    window.addEventListener('taskflow:session', onSession);
    window.addEventListener('taskflow:logout', onLogout);
    return () => {
      window.removeEventListener('taskflow:session', onSession);
      window.removeEventListener('taskflow:logout', onLogout);
    };
  }, [queryClient]);

  /**
   * Login user with email and password.
   * 
   * @async
   * @param {string} email - User's email address
   * @param {string} password - User's password
   * @returns {Promise<Object>} Authenticated user object
   * @throws {Error} If login fails
   * 
   * @example
   * try {
   *   const user = await login('user@example.com', 'password');
   *   console.log('Logged in:', user.email);
   * } catch (error) {
   *   console.error('Login failed:', error.message);
   * }
   */
  const login = async (email, password) => {
    const data = await api.auth.login({ email, password });
    if (data.access_token) {
      setAccessToken(data.access_token);
      setRefreshToken(data.refresh_token);
      const user = await api.users.me(data.access_token);
      setUser(user);
      return user;
    }
    throw new Error(data?.detail || 'Login failed');
  };

  /**
   * Register a new user and automatically log them in.
   * 
   * @async
   * @param {string} email - User's email address
   * @param {string} password - User's password
   * @returns {Promise<Object>} Newly created user object
   * @throws {Error} If registration fails
   * 
   * @example
   * try {
   *   const user = await register('new@example.com', 'securePassword');
   *   console.log('Registered:', user.email);
   * } catch (error) {
   *   console.error('Registration failed:', error.message);
   * }
   */
  const register = async (email, password) => {
    const data = await api.auth.register({ email, password });
    if (data.id) {
      return login(email, password);
    }
    if (data.message) {
      return { message: data.message };
    }
    throw new Error(data?.detail || 'Registration failed');
  };

  /**
   * Logout user and clear all authentication data.
   * Calls the logout API endpoint and clears local state.
   * 
   * @example
   * logout();
   * // User is redirected to login or app resets to unauthenticated state
   */
  const logout = () => {
    if (accessToken) {
      // Revoke both tokens server-side. The local session is cleared even if
      // the network call fails, so logout always works for the user.
      api.auth.logout(accessToken, refreshToken).catch(() => {});
    }
    clearSession();
  };

  /**
   * Proactively refresh the session shortly before the access token expires.
   * This keeps the user logged in without waiting for a 401. Refresh tokens
   * are single-use: the API rotates them on every call.
   */
  useEffect(() => {
    if (!accessToken || !refreshToken) return undefined;

    const expiresAt = getJwtExpiry(accessToken);
    if (!expiresAt) return undefined;

    const delay = Math.max(expiresAt - Date.now() - 60_000, 5_000);
    const timer = setTimeout(async () => {
      const performRefresh = async () => {
        // Another tab may have refreshed while this one waited for the lock.
        const currentAccess = localStorage.getItem('access_token');
        const currentRefresh = localStorage.getItem('refresh_token');

        if (currentAccess && currentAccess !== accessToken && currentRefresh) {
          setAccessToken(currentAccess);
          setRefreshToken(currentRefresh);
          return;
        }

        if (!currentRefresh) {
          clearSession();
          return;
        }

        const data = await api.auth.refresh(currentRefresh);
        setAccessToken(data.access_token);
        setRefreshToken(data.refresh_token);
      };

      try {
        // Web Locks serializes refresh across tabs. Without it, the
        // localStorage comparison above still prevents most duplicate calls.
        if (typeof navigator !== 'undefined' && navigator.locks?.request) {
          await navigator.locks.request('taskflow-auth-refresh', performRefresh);
        } else {
          await performRefresh();
        }
      } catch {
        clearSession();
      }
    }, delay);

    return () => clearTimeout(timer);
  }, [accessToken, refreshToken, clearSession]);

  /**
   * Get Authorization header object for API requests.
   * 
   * @returns {Object} Headers object with Bearer token
   * 
   * @example
   * const headers = getAuthHeader();
   * // { Authorization: 'Bearer eyJhbGc...' }
   */
  const getAuthHeader = () =>
    accessToken ? { Authorization: `Bearer ${accessToken}` } : {};

  return (
    <AuthContext.Provider value={{ user, accessToken, refreshToken, loading, login, register, logout, getAuthHeader }}>
      {children}
    </AuthContext.Provider>
  );
}

