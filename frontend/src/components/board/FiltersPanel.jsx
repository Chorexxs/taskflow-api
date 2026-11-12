import { X } from 'lucide-react'

/**
 * Filter bar for the Kanban board (T-127).
 */
export default function FiltersPanel({ filters, teamMembers, onChange, onClear }) {
  return (
    <div className="border-b border-subtle bg-[var(--color-bg-secondary)]/30 px-4 py-3">
      <div className="max-w-7xl mx-auto flex flex-wrap gap-3 items-center">
        <select
          id="filter-status"
          name="filter-status"
          aria-label="Filter by status"
          value={filters.status}
          onChange={(e) => onChange('status', e.target.value)}
          className="input-field w-auto py-1.5 text-sm"
        >
          <option value="">All Status</option>
          <option value="todo">To Do</option>
          <option value="in_progress">In Progress</option>
          <option value="done">Done</option>
        </select>

        <select
          id="filter-priority"
          name="filter-priority"
          aria-label="Filter by priority"
          value={filters.priority}
          onChange={(e) => onChange('priority', e.target.value)}
          className="input-field w-auto py-1.5 text-sm"
        >
          <option value="">All Priorities</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        <select
          id="filter-assignee"
          name="filter-assignee"
          aria-label="Filter by assignee"
          value={filters.assigned_to}
          onChange={(e) => onChange('assigned_to', e.target.value)}
          className="input-field w-auto py-1.5 text-sm"
        >
          <option value="">All Assignees</option>
          {teamMembers?.map((member) => (
            <option key={member.user_id} value={member.user_id}>{member.user?.email}</option>
          ))}
        </select>

        <button
          onClick={onClear}
          className="text-sm text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] flex items-center gap-1 transition-colors"
        >
          <X className="w-4 h-4" />
          Clear
        </button>
      </div>
    </div>
  )
}
