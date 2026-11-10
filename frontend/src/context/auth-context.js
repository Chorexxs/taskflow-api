/**
 * Authentication primitives shared by the provider and consumers.
 *
 * Keeping the context object, the hook and the JWT helper in a non-component
 * module lets `AuthContext.jsx` export only the provider, so Fast Refresh keeps
 * working during development.
 */

import { createContext, useContext } from 'react';

/**
 * Read the `exp` claim (milliseconds) from a JWT without verifying it.
 * Verification is the server's job; the client only uses this to schedule a
 * proactive refresh.
 *
 * @param {string} token - Encoded JWT
 * @returns {number|null} Expiration in milliseconds, or null if unreadable
 */
export function getJwtExpiry(token) {
  try {
    const payload = token.split('.')[1];
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized.padEnd(
      normalized.length + ((4 - (normalized.length % 4)) % 4),
      '=',
    );
    const decoded = JSON.parse(atob(padded));
    return decoded.exp ? decoded.exp * 1000 : null;
  } catch {
    return null;
  }
}

/**
 * Authentication context.
 * @type {React.Context<null>}
 */
export const AuthContext = createContext(null);

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
