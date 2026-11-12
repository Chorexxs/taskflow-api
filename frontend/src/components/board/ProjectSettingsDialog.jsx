import { Archive, X } from 'lucide-react'

import { useDialogA11y } from '../../hooks/useDialogA11y'

/**
 * Modal with the project edit form and the archive action (T-127).
 */
export default function ProjectSettingsDialog({ form, onChange, onSubmit, onArchive, isSaving, isArchiving, onClose }) {
  const dialogRef = useDialogA11y(true, onClose)

  return (
    <div ref={dialogRef} className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-label="Project settings">
      <div className="bg-[var(--color-bg-secondary)] border border-subtle rounded-2xl p-6 w-full max-w-md shadow-elevated fade-in">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-medium text-[var(--color-text-primary)]">Project Settings</h3>
          <button onClick={onClose} className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="edit-project-name" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Project Name</label>
            <input
              type="text"
              id="edit-project-name"
              name="name"
              value={form.name}
              onChange={(e) => onChange({ ...form, name: e.target.value })}
              required
              className="input-field"
              placeholder="Project name"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="edit-project-description" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Description</label>
            <textarea
              id="edit-project-description"
              name="description"
              value={form.description}
              onChange={(e) => onChange({ ...form, description: e.target.value })}
              className="input-field min-h-[80px] resize-none"
              placeholder="Optional description..."
            />
          </div>
          <div className="flex gap-3 justify-end pt-2">
            <button type="button" onClick={onClose} className="btn-secondary text-sm">Cancel</button>
            <button type="submit" disabled={isSaving} className="btn-primary text-sm">
              {isSaving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>

        <div className="mt-6 pt-4">
          <button
            onClick={onArchive}
            disabled={isArchiving}
            className="flex items-center gap-2 px-4 py-2 bg-[var(--color-priority-high)]/10 text-[var(--color-priority-high)] rounded-lg hover:bg-[var(--color-priority-high)]/20 transition-colors text-sm w-full justify-center"
          >
            <Archive className="w-4 h-4" />
            {isArchiving ? 'Archiving...' : 'Archive Project'}
          </button>
        </div>
      </div>
    </div>
  )
}
