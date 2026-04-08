/**
 * NotFound.jsx - 404 Error Page Component
 * 
 * Displayed when users navigate to a non-existent route in the application.
 * Provides a friendly error message and a link back to the dashboard.
 * 
 * Features:
 * - Centralized 404 error display
 * - Warning icon for visual feedback
 * - Link to navigate back to dashboard
 * - Responsive centered layout
 * 
 * @requires react-router-dom - For navigation link
 * @requires lucide-react - For icons
 */

import { Link } from 'react-router-dom'
import { Home, AlertTriangle } from 'lucide-react'

/**
 * NotFound Component - 404 error page
 * 
 * Displays when a user visits a non-existent route.
 * Provides a link back to the main dashboard.
 * 
 * @returns {JSX.Element} Rendered 404 error page
 * 
 * @example
 * // Automatically rendered by React Router for unknown routes
 * <Route path="*" element={<NotFound />} />
 */

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="text-center">
        <AlertTriangle className="w-16 h-16 mx-auto text-yellow-500 mb-4" />
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">404</h1>
        <p className="text-xl text-gray-600 dark:text-gray-400 mb-6">Page not found</p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          <Home className="w-4 h-4" />
          Go to Dashboard
        </Link>
      </div>
    </div>
  )
}
