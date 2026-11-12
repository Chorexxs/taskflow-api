import { Activity, X } from 'lucide-react'

import { useDialogA11y } from '../../hooks/useDialogA11y'
import { formatActivityAction, formatActivityActor, formatActivityValue } from '../../utils/activity'

/**
 * Paginated project activity modal (T-127).
 */
export default function ProjectActivityDialog({ activity, page, onPrevious, onNext, onClose }) {
  const dialogRef = useDialogA11y(true, onClose)

  return (
    <div ref={dialogRef} className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" role="dialog" aria-modal="true" aria-label="Project activity">
      <div className="bg-[var(--color-bg-secondary)] rounded-xl shadow-xl max-w-lg w-full max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-subtle">
          <h2 className="text-lg font-medium text-[var(--color-text-primary)]">Project Activity</h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)]">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {activity?.items?.length > 0 ? (
            <div className="space-y-3">
              {activity.items.map((log) => {
                const oldValue = formatActivityValue(log.old_value)
                const newValue = formatActivityValue(log.new_value)
                return (
                  <div key={log.id} className="p-3 bg-[var(--color-bg-tertiary)] rounded-lg text-sm">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-medium text-[var(--color-accent)]">
                        {formatActivityAction(log.action)}
                      </span>
                      <span className="text-xs text-[var(--color-text-muted)]">
                        {new Date(log.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div className="text-xs text-[var(--color-text-muted)]">by {formatActivityActor(log)}</div>
                    {oldValue && newValue && (
                      <div className="text-[var(--color-text-secondary)] mt-1">
                        <span className="line-through text-[var(--color-text-muted)] mr-1">{oldValue}</span>
                        <span className="text-[var(--color-text-primary)]">→ {newValue}</span>
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
              {activity.pages > 1 && (
                <div className="flex items-center justify-between pt-2">
                  <button
                    onClick={onPrevious}
                    disabled={page <= 1}
                    className="text-xs text-[var(--color-accent)] disabled:text-[var(--color-text-muted)] disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  <span className="text-xs text-[var(--color-text-muted)]">
                    Page {activity.page} of {activity.pages}
                  </span>
                  <button
                    onClick={onNext}
                    disabled={!activity.has_next}
                    className="text-xs text-[var(--color-accent)] disabled:text-[var(--color-text-muted)] disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-[var(--color-text-muted)]">
              <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No activity yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
