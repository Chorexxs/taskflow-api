/**
 * TaskFlow Frontend - 404 Error Page
 * 
 * Displayed when users navigate to a non-existent route in the application.
 * Provides a friendly error message and a link back to the dashboard.
 * 
 * Features:
 * - Cohesive dark theme matching TaskFlow design system
 * - Animated background effects
 * - Glass morphism card
 * - Smooth transitions
 */

import { Link } from 'react-router-dom'
import { Home, SearchX } from 'lucide-react'

/**
 * NotFound Component - 404 error page
 * 
 * Displays when a user visits a non-existent route.
 * Provides a link back to the main dashboard.
 * 
 * @returns {JSX.Element} Rendered 404 error page
 */
export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--color-bg-secondary)_0%,_var(--color-bg-primary)_70%)]"></div>
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-emerald-500/3 rounded-full blur-3xl"></div>
      
      {/* 404 Card */}
      <div className="relative z-10 w-full max-w-md px-6">
        <div className="bg-glass border border-subtle rounded-2xl p-12 shadow-elevated text-center">
          {/* Icon */}
          <div className="mb-6">
            <div className="w-20 h-20 mx-auto rounded-full bg-[var(--color-accent-muted)] flex items-center justify-center">
              <SearchX className="w-10 h-10 text-[var(--color-accent)]" />
            </div>
          </div>
          
          {/* Title */}
          <h1 className="font-display text-6xl font-bold text-gradient mb-3">
            404
          </h1>
          
          {/* Subtitle */}
          <p className="text-lg text-[var(--color-text-primary)] mb-3">
            Page not found
          </p>
          
          {/* Description */}
          <p className="text-sm text-[var(--color-text-muted)] mb-8">
            The page you're looking for doesn't exist or has been moved.
          </p>
          
          {/* CTA Button */}
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-[var(--color-accent)] text-[var(--color-bg-primary)] rounded-lg font-medium hover:bg-[var(--color-accent-hover)] transition-all duration-200"
          >
            <Home className="w-4 h-4" />
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  )
}