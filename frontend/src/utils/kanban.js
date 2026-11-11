/**
 * Kanban ordering helpers (FR-TASK-08).
 *
 * Tasks keep a fractional `position` inside each (project, status) column. When
 * a card is dropped between two neighbours the client sends the midpoint, so
 * only the moved task has to be updated.
 */

export const POSITION_GAP = 1024

/**
 * Coerce a position coming from the API into a finite number.
 *
 * @param {unknown} value
 * @returns {number}
 */
export function toPosition(value) {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

/**
 * Position for a card dropped between two neighbours.
 *
 * `previous` is the card above the drop slot (or `null` at the top) and `next`
 * is the card below it (or `null` at the bottom).
 *
 * @param {unknown} previous
 * @param {unknown} next
 * @returns {number}
 */
export function positionBetween(previous, next) {
  const before = previous == null ? 0 : toPosition(previous)
  if (next == null) return before + POSITION_GAP
  const after = toPosition(next)
  if (after <= before) return before + POSITION_GAP / 2
  return before + (after - before) / 2
}
