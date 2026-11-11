import { describe, expect, it } from 'vitest'

import { POSITION_GAP, positionBetween, toPosition } from '../utils/kanban'

describe('kanban position helpers', () => {
  it('coerces missing or invalid positions to zero', () => {
    expect(toPosition(undefined)).toBe(0)
    expect(toPosition(null)).toBe(0)
    expect(toPosition('not-a-number')).toBe(0)
    expect(toPosition('2048')).toBe(2048)
  })

  it('appends after the last card when there is no next neighbour', () => {
    expect(positionBetween(1024, null)).toBe(1024 + POSITION_GAP)
    expect(positionBetween(null, null)).toBe(POSITION_GAP)
  })

  it('inserts a card at the top of a column', () => {
    expect(positionBetween(null, 1024)).toBe(512)
  })

  it('inserts a card between two neighbours', () => {
    expect(positionBetween(1024, 2048)).toBe(1536)
  })

  it('keeps a stable slot when neighbours are out of order', () => {
    expect(positionBetween(2048, 1024)).toBe(2048 + POSITION_GAP / 2)
  })
})
