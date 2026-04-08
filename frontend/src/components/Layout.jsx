/**
 * TaskFlow Frontend - Layout Component
 * 
 * This component provides the main layout structure for the application.
 * It includes the header with navigation and the main content area.
 * 
 * Features:
 * - Sticky header with app branding
 * - Navigation to dashboard
 * - Notifications bell icon
 * - Settings link
 * - Logout button
 * - Responsive design
 */

import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import NotificationsBell from './NotificationsBell';
import { Settings, LogOut } from 'lucide-react';

/**
 * Main layout component that wraps page content.
 * 
 * @param {Object} props - Component props
 * @param {React.ReactNode} props.children - Page content to render
 * @param {boolean} [props.hideNav] - Whether to hide navigation (optional)
 * @returns {JSX.Element} Layout with header and content
 * 
 * @example
 * // Basic usage
 * <Layout>
 *   <Dashboard />
 * </Layout>
 * 
 * @example
 * // With hidden navigation
 * <Layout hideNav>
 *   <FullScreenContent />
 * </Layout>
 */
export default function Layout({ children, hideNav }) {
  const { logout } = useAuth();
  const navigate = useNavigate();

  /**
   * Handle user logout and redirect to login.
   * Calls the logout function and navigates to login page.
   */
  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      {/* Header with navigation */}
      <header className="border-b border-subtle bg-[var(--color-bg-secondary)]/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo and app name */}
            <div className="flex items-center gap-3">
              <Link to="/" className="flex items-center gap-3 group">
                <div className="w-8 h-8 rounded-lg bg-[var(--color-accent)] flex items-center justify-center group-hover:scale-105 transition-transform">
                  <span className="text-sm font-bold text-[var(--color-bg-primary)]">T</span>
                </div>
                <span className="font-display text-xl font-semibold text-gradient hidden sm:block">TaskFlow</span>
              </Link>
            </div>
            
            {/* Right side actions */}
            <div className="flex items-center gap-2">
              {/* Notifications bell */}
              <NotificationsBell />
              
              {/* Settings link */}
              <Link 
                to="/profile"
                className="p-2 rounded-lg text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-all"
              >
                <Settings className="w-5 h-5" />
              </Link>
              
              {/* Logout button */}
              <button
                onClick={handleLogout}
                className="p-2 rounded-lg text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-[var(--color-priority-high)] transition-all"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content area */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
