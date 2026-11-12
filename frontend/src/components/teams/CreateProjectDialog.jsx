import { X } from 'lucide-react'

import { useDialogA11y } from '../../hooks/useDialogA11y'

/**
 * Modal to create a project from the team page (T-127).
 */
export default function CreateProjectDialog({ form, onChange, onSubmit, isPending, onClose }) {
  const dialogRef = useDialogA11y(true, onClose)

  return (
    <div ref={dialogRef} className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-label="Create project">
      <div className="bg-[var(--color-bg-secondary)] border border-subtle rounded-2xl p-6 w-full max-w-md shadow-elevated fade-in">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-medium text-[var(--color-text-primary)]">Create Project</h3>
          <button onClick={onClose} className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="create-project-name" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Name</label>
            <input
              type="text"
              id="create-project-name"
              name="name"
              value={form.name}
              onChange={(e) => onChange({ ...form, name: e.target.value })}
              required
              className="input-field"
              placeholder="My Project"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="create-project-description" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Description</label>
            <textarea
              id="create-project-description"
              name="description"
              value={form.description}
              onChange={(e) => onChange({ ...form, description: e.target.value })}
              className="input-field min-h-[80px] resize-none"
              placeholder="Optional description..."
            />
          </div>
          <div className="flex gap-3 justify-end pt-2">
            <button type="button" onClick={onClose} className="btn-secondary text-sm">Cancel</button>
            <button type="submit" disabled={isPending} className="btn-primary text-sm">
              {isPending ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
