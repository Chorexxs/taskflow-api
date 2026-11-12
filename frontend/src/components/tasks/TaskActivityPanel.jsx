import { Activity } from 'lucide-react'

import { formatActivityAction, formatActivityActor, formatActivityValue } from '../../utils/activity'

/**
 * Paginated activity list for a task (T-127).
 */
export default function TaskActivityPanel({ activity, activityPage, page, onPrevious, onNext }) {
  if (!activityPage?.total) return null

  return (
    <div className="mt-8">
      <h3 className="text-sm font-medium text-[var(--color-text-secondary)] uppercase tracking-wider mb-4 flex items-center gap-2">
        <Activity className="w-4 h-4" />
        Activity ({activityPage.total})
      </h3>
      <div className="space-y-2">
        {activity.map((log) => {
          const oldValue = formatActivityValue(log.old_value)
          const newValue = formatActivityValue(log.new_value)
          return (
            <div key={log.id} className="p-3 bg-[var(--color-bg-tertiary)] rounded-lg text-xs">
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="font-medium text-[var(--color-accent)]">
                  {formatActivityAction(log.action)}
                </span>
                <span className="text-[var(--color-text-muted)]">
                  {new Date(log.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <div className="text-[var(--color-text-muted)]">by {formatActivityActor(log)}</div>
              {oldValue && newValue && (
                <div className="text-[var(--color-text-secondary)] mt-1">
                  <span className="line-through text-[var(--color-text-muted)] mr-1">{oldValue}</span>
                  <span className="text-[var(--color-text-primary)]">→ {newValue}</span>
                </div>
              )}
              {oldValue && !newValue && (
                <div className="text-[var(--color-text-secondary)] mt-1">
                  Removed: <span className="text-[var(--color-text-muted)]">{oldValue}</span>
                </div>
              )}
              {!oldValue && newValue && log.action !== 'created' && (
                <div className="text-[var(--color-text-secondary)] mt-1">
                  Set to: <span className="text-[var(--color-text-primary)]">{newValue}</span>
                </div>
              )}
            </div>
          )
        })}
        {activityPage.pages > 1 && (
          <div className="flex items-center justify-between pt-2">
            <button
              onClick={onPrevious}
              disabled={page <= 1}
              className="text-xs text-[var(--color-accent)] disabled:text-[var(--color-text-muted)] disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-xs text-[var(--color-text-muted)]">
              Page {activityPage.page} of {activityPage.pages}
            </span>
            <button
              onClick={onNext}
              disabled={!activityPage.has_next}
              className="text-xs text-[var(--color-accent)] disabled:text-[var(--color-text-muted)] disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
