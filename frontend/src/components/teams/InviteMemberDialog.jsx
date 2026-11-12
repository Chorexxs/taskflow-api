import { X } from 'lucide-react'

import { useDialogA11y } from '../../hooks/useDialogA11y'

/**
 * Modal to add an existing user to the team (T-127).
 */
export default function InviteMemberDialog({ email, role, onEmailChange, onRoleChange, onSubmit, isPending, onClose }) {
  const dialogRef = useDialogA11y(true, onClose)

  return (
    <div ref={dialogRef} className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-label="Add team member">
      <div className="bg-[var(--color-bg-secondary)] border border-subtle rounded-2xl p-6 w-full max-w-md shadow-elevated fade-in">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-medium text-[var(--color-text-primary)]">Invite Member</h3>
          <button onClick={onClose} className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="invite-email" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Email</label>
            <input
              type="email"
              id="invite-email"
              name="email"
              value={email}
              onChange={(e) => onEmailChange(e.target.value)}
              required
              className="input-field"
              placeholder="colleague@example.com"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="invite-role" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Role</label>
            <select
              id="invite-role"
              name="role"
              value={role}
              onChange={(e) => onRoleChange(e.target.value)}
              className="input-field"
            >
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div className="flex gap-3 justify-end pt-2">
            <button type="button" onClick={onClose} className="btn-secondary text-sm">Cancel</button>
            <button type="submit" disabled={isPending} className="btn-primary text-sm">
              {isPending ? 'Sending...' : 'Send Invite'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
