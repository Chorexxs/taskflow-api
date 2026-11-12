import { X } from 'lucide-react'

import { useDialogA11y } from '../../hooks/useDialogA11y'

/**
 * Modal for creating a task on the Kanban board (T-127).
 */
export default function CreateTaskDialog({ form, onChange, onSubmit, onClose, teamMembers, isPending }) {
  const dialogRef = useDialogA11y(true, onClose)

  return (
    <div ref={dialogRef} className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-label="Create task">
      <div className="bg-[var(--color-bg-secondary)] border border-subtle rounded-2xl p-6 w-full max-w-md shadow-elevated fade-in">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-medium text-[var(--color-text-primary)]">Create Task</h3>
          <button onClick={onClose} className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="create-task-title" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Title</label>
            <input
              type="text"
              id="create-task-title"
              name="title"
              value={form.title}
              onChange={(e) => onChange({ ...form, title: e.target.value })}
              required
              className="input-field"
              placeholder="Task title"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="create-task-description" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Description</label>
            <textarea
              id="create-task-description"
              name="description"
              value={form.description}
              onChange={(e) => onChange({ ...form, description: e.target.value })}
              className="input-field min-h-[80px] resize-none"
              placeholder="Optional description..."
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label htmlFor="create-task-priority" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Priority</label>
              <select
                id="create-task-priority"
                name="priority"
                value={form.priority}
                onChange={(e) => onChange({ ...form, priority: e.target.value })}
                className="input-field"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <div className="space-y-2">
              <label htmlFor="create-task-due-date" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Due Date</label>
              <input
                type="date"
                id="create-task-due-date"
                name="due_date"
                value={form.due_date || ''}
                onChange={(e) => onChange({ ...form, due_date: e.target.value || null })}
                className="input-field"
              />
            </div>
          </div>
          <div className="space-y-2">
            <label htmlFor="create-task-assignee" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Assign to</label>
            <select
              id="create-task-assignee"
              name="assigned_to"
              value={form.assigned_to || ''}
              onChange={(e) => onChange({ ...form, assigned_to: e.target.value ? parseInt(e.target.value) : null })}
              className="input-field"
            >
              <option value="">Unassigned</option>
              {teamMembers?.map((member) => (
                <option key={member.user_id} value={member.user_id}>{member.user?.email}</option>
              ))}
            </select>
          </div>
          <div className="flex gap-3 justify-end pt-2">
            <button type="button" onClick={onClose} className="btn-secondary text-sm">Cancel</button>
            <button type="submit" disabled={isPending} className="btn-primary text-sm">
              {isPending ? 'Creating...' : 'Create Task'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
