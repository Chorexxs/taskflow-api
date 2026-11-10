/**
 * Human-readable helpers for activity log entries.
 *
 * The API returns machine actions and raw values; the UI must never show raw
 * IDs or snake_case to users.
 */

const ACTION_LABELS = {
  created: 'Created',
  deleted: 'Deleted',
  updated_status: 'Status changed',
  updated_title: 'Title changed',
  updated_description: 'Description changed',
  updated_priority: 'Priority changed',
  updated_due_date: 'Due date changed',
  assigned: 'Assigned',
  unassigned: 'Unassigned',
  uploaded: 'Attachment uploaded',
  role_changed: 'Role changed',
  member_added: 'Member added',
  member_removed: 'Member removed',
}

export function formatActivityAction(action) {
  if (ACTION_LABELS[action]) return ACTION_LABELS[action]
  return String(action || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function formatActivityActor(log) {
  return log?.actor?.email || log?.actor?.name || 'Unknown user'
}

export function formatActivityValue(value) {
  if (value === null || value === undefined || value === '') return ''
  const text = String(value)
  // Assignment logs store user IDs; showing a bare number is noise.
  if (/^\d+$/.test(text)) return 'a user'
  return text
}
