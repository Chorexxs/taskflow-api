/**
 * Email verification landing page (`/verify-email?token=...`).
 */

import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api';

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('');
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const token = searchParams.get('token');
    if (!token) {
      setStatus('error');
      setMessage('The verification link is missing its token.');
      return;
    }

    api.auth
      .verifyEmail(token)
      .then((data) => {
        setStatus('success');
        setMessage(data?.message || 'Email verified. You can sign in now.');
      })
      .catch((error) => {
        setStatus('error');
        setMessage(error.message || 'The verification link is invalid or expired.');
      });
  }, [searchParams]);

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--color-bg-secondary)_0%,_var(--color-bg-primary)_70%)]"></div>
      <div className="relative z-10 w-full max-w-md px-6">
        <div className="bg-glass border border-subtle rounded-2xl p-8 shadow-elevated text-center">
          <h1 className="font-display text-3xl font-semibold text-gradient mb-3">
            TaskFlow
          </h1>
          {status === 'loading' && (
            <p className="text-sm text-[var(--color-text-secondary)]">
              Verifying your email…
            </p>
          )}
          {status === 'success' && (
            <>
              <p className="text-sm text-[var(--color-text-secondary)] mb-6">{message}</p>
              <Link
                to="/login"
                className="inline-block btn-primary px-5 py-2.5 text-sm"
              >
                Sign in
              </Link>
            </>
          )}
          {status === 'error' && (
            <>
              <p className="text-sm text-[var(--color-priority-high)] mb-6">{message}</p>
              <Link
                to="/login"
                className="inline-block text-sm text-[var(--color-accent)] hover:underline"
              >
                Back to sign in
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
