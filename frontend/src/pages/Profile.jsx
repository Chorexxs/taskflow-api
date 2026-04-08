import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import toast from 'react-hot-toast'
import { ArrowLeft, LogOut, User, Shield } from 'lucide-react'

export default function Profile() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="card p-6 md:p-8">
      <div className="flex items-center gap-4 mb-8">
        <div className="w-14 h-14 rounded-2xl bg-[var(--color-accent)] flex items-center justify-center">
          <User className="w-7 h-7 text-[var(--color-bg-primary)]" />
        </div>
        <div>
          <h2 className="text-lg font-medium text-[var(--color-text-primary)]">Account Settings</h2>
          <p className="text-sm text-[var(--color-text-muted)]">Manage your account preferences</p>
        </div>
      </div>
      
      <div className="space-y-6">
        <div className="space-y-2">
          <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Email</label>
          <input
            type="email"
            value={user?.email || ''}
            disabled
            className="input-field bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)]"
          />
          <p className="text-xs text-[var(--color-text-muted)]">Email cannot be changed</p>
        </div>

        <div className="pt-6 border-t border-subtle">
          <div className="flex items-center gap-2 mb-6">
            <Shield className="w-4 h-4 text-[var(--color-text-muted)]" />
            <h3 className="text-sm font-medium text-[var(--color-text-secondary)]">Change Password</h3>
          </div>
          
          <div className="space-y-5">
            <div className="space-y-2">
              <label className="block text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">New Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter new password"
                className="input-field"
              />
            </div>

            <div className="space-y-2">
              <label className="block text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm new password"
                className="input-field"
              />
            </div>

            <div className="pt-2">
              <button
                onClick={() => toast.success('Password updated!')}
                className="btn-primary text-sm"
              >
                Update Password
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8 pt-6 border-t border-subtle">
        <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-5">Session</h3>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2.5 bg-[var(--color-priority-high)]/10 text-[var(--color-priority-high)] rounded-lg hover:bg-[var(--color-priority-high)]/20 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Log Out
        </button>
      </div>
    </div>
  )
}