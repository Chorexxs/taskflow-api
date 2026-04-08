/**
 * TaskFlow Frontend - Register Page
 * 
 * This page allows new users to create an account.
 * On successful registration, the user is automatically logged in.
 * 
 * Features:
 * - Email, password, and confirm password fields
 * - Password matching validation
 * - Loading state during registration
 * - Error handling with toast notifications
 * - Link to login page
 * - Glass morphism design with background effects
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

/**
 * Registration page component.
 * 
 * @returns {JSX.Element} Registration page with form
 * 
 * @example
 * <Route path="/register" element={<Register />} />
 */
export default function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  /**
   * Handle form submission.
   * Validates passwords match, then registers user.
   * 
   * @param {React.FormEvent} e - Form submission event
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate password match
    if (password !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      await register(email, password);
      toast.success('Account created!');
      navigate('/');
    } catch (error) {
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--color-bg-secondary)_0%,_var(--color-bg-primary)_70%)]"></div>
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-emerald-500/3 rounded-full blur-3xl"></div>
      
      {/* Registration form */}
      <div className="relative z-10 w-full max-w-md px-6">
        <div className="bg-glass border border-subtle rounded-2xl p-8 shadow-elevated">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="font-display text-3xl font-semibold text-gradient mb-2">
              TaskFlow
            </h1>
            <p className="text-sm text-[var(--color-text-secondary)]">
              Create your account
            </p>
          </div>
          
          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email field */}
            <div className="space-y-2">
              <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="input-field"
                placeholder="you@example.com"
              />
            </div>
            
            {/* Password field */}
            <div className="space-y-2">
              <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                className="input-field"
                placeholder="••••••••"
              />
            </div>
            
            {/* Confirm password field */}
            <div className="space-y-2">
              <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">
                Confirm Password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={6}
                className="input-field"
                placeholder="••••••••"
              />
            </div>
            
            {/* Submit button */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-3 text-sm"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Creating account...
                </span>
              ) : (
                'Create account'
              )}
            </button>
          </form>
          
          {/* Login link */}
          <p className="mt-6 text-center text-sm text-[var(--color-text-muted)]">
            Already have an account?{' '}
            <Link to="/login" className="text-[var(--color-accent)] hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
