/**
 * Consistent error state for failed queries.
 *
 * Shows a short message and an optional retry action instead of a blank page.
 */
export default function QueryError({
  title = 'Something went wrong',
  message = 'We could not load this data. Please try again.',
  onRetry,
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center" role="alert">
      <div className="w-12 h-12 rounded-full bg-[var(--color-bg-tertiary)] flex items-center justify-center mb-4">
        <span aria-hidden="true" className="text-xl">!</span>
      </div>
      <h3 className="text-base font-medium text-[var(--color-text-primary)] mb-2">
        {title}
      </h3>
      <p className="text-sm text-[var(--color-text-muted)] max-w-sm mb-4">
        {message}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="px-4 py-2 rounded-lg bg-[var(--color-accent)] text-[var(--color-bg-primary)] text-sm font-medium hover:bg-[var(--color-accent-hover)] transition-colors"
        >
          Try again
        </button>
      )}
    </div>
  )
}
