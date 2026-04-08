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
 * import { useAuth } from './context/AuthContext';
 * 
 * function MyComponent() {
 *   const { user, logout } = useAuth();
 *   // Use user data or logout function
 * }
 */

import { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api';

/**
 * Authentication context - provides auth state and methods
 * @type {React.Context<null>}
 */
const AuthContext = createContext(null);

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

  /**
   * Effect: Validate token and fetch user on mount/token change
   * Runs when accessToken changes to validate the session
   */
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
    throw new Error(data.detail || 'Login failed');
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
    throw new Error(data.detail || 'Registration failed');
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
      api.auth.logout(accessToken).catch(() => {});
    }
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
  };

  /**
   * Get Authorization header object for API requests.
   * 
   * @returns {Object} Headers object with Bearer token
   * 
   * @example
   * const headers = getAuthHeader();
   * // { Authorization: 'Bearer eyJhbGc...' }
   */
  const getAuthHeader = () => ({ Authorization: `Bearer ${accessToken}` });

  return (
    <AuthContext.Provider value={{ user, accessToken, loading, login, register, logout, getAuthHeader }}>
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Hook to access authentication context.
 * Must be used within an AuthProvider.
 * 
 * @returns {Object} Auth context with user, tokens, and methods
 * @throws {Error} If used outside AuthProvider
 * 
 * @example
 * function Dashboard() {
 *   const { user, logout } = useAuth();
 *   
 *   return (
 *     <div>
 *       <p>Welcome, {user.email}</p>
 *       <button onClick={logout}>Logout</button>
 *     </div>
 *   );
 * }
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
