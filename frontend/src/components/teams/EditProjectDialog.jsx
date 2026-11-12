import { X } from 'lucide-react'

import { useDialogA11y } from '../../hooks/useDialogA11y'

/**
 * Modal to edit a project from the team page (T-127).
 */
export default function EditProjectDialog({ form, onChange, onSubmit, isPending, onClose }) {
  const dialogRef = useDialogA11y(true, onClose)

  return (
    <div ref={dialogRef} className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" role="dialog" aria-modal="true" aria-label="Edit project">
      <div className="bg-[var(--color-bg-secondary)] rounded-xl shadow-xl max-w-md w-full">
        <div className="flex items-center justify-between p-4 border-b border-subtle">
          <h2 className="text-lg font-medium text-[var(--color-text-primary)]">Edit Project</h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)]">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={onSubmit} className="p-4 space-y-4">
          <div className="space-y-2">
            <label htmlFor="team-edit-project-name" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Name</label>
            <input
              type="text"
              id="team-edit-project-name"
              name="name"
              value={form.name}
              onChange={(e) => onChange({ ...form, name: e.target.value })}
              required
              className="input-field"
              placeholder="My Project"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="team-edit-project-description" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Description</label>
            <textarea
              id="team-edit-project-description"
              name="description"
              value={form.description}
              onChange={(e) => onChange({ ...form, description: e.target.value })}
              className="input-field min-h-[80px] resize-none"
              placeholder="Optional description..."
            />
          </div>
          <div className="flex gap-3 justify-end pt-2">
            <button type="button" onClick={onClose} className="btn-secondary text-sm">Cancel</button>
            <button type="submit" disabled={isPending || !form.name.trim()} className="btn-primary text-sm">
              {isPending ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
