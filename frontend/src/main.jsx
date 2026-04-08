/**
 * TaskFlow Frontend - Application Bootstrap
 * 
 * This is the entry point for the React application. It sets up all
 * necessary providers and initializes the application.
 * 
 * Providers configured:
 * 1. StrictMode - Development-only checks for potential problems
 * 2. QueryClientProvider - React Query for data fetching
 * 3. BrowserRouter - React Router for navigation
 * 4. AuthProvider - Authentication state management
 * 5. Toaster - Toast notifications
 * 
 * The application is mounted to the DOM element with id 'root'.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import './index.css';
import App from './App.jsx';
import { AuthProvider } from './context/AuthContext';

/**
 * React Query client configuration.
 * - staleTime: Data is considered fresh for 1 minute
 * - retry: Failed queries are retried once
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      retry: 1,
    },
  },
});

/**
 * Mount the React application to the DOM.
 * 
 * The application is wrapped with:
 * - StrictMode for development checks
 * - QueryClientProvider for React Query
 * - BrowserRouter for routing
 * - AuthProvider for authentication
 * - Toaster for notifications
 * - Grain overlay for visual effect
 * 
 * @example
 * // The application renders into:
 * <div id="root">
 *   <StrictMode>
 *     <QueryClientProvider>
 *       <BrowserRouter>
 *         <AuthProvider>
 *           <App />
 *           <Toaster />
 *           <div className="grain-overlay" />
 *         </AuthProvider>
 *       </BrowserRouter>
 *     </QueryClientProvider>
 *   </StrictMode>
 * </div>
 */
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
          {/* Toast notification container */}
          <Toaster 
            position="top-right"
            toastOptions={{
              className: 'toast-custom',
              duration: 3000,
              style: {
                background: 'var(--color-bg-secondary)',
                color: 'var(--color-text-primary)',
                border: '1px solid var(--color-border)',
                borderRadius: '8px',
                fontSize: '14px',
              },
              success: {
                iconTheme: {
                  primary: 'var(--color-accent)',
                  secondary: 'var(--color-bg-primary)',
                },
              },
              error: {
                iconTheme: {
                  primary: 'var(--color-priority-high)',
                  secondary: 'var(--color-bg-primary)',
                },
              },
            }}
          />
          {/* Grain texture overlay for visual effect */}
          <div className="grain-overlay"></div>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
