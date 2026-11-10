import { describe, expect, it } from 'vitest'
import {
  formatActivityAction,
  formatActivityActor,
  formatActivityValue,
} from '../utils/activity'

describe('activity formatting', () => {
  it('turns machine actions into readable labels', () => {
    expect(formatActivityAction('updated_status')).toBe('Status changed')
    expect(formatActivityAction('custom_action')).toBe('Custom Action')
  })

  it('shows the actor without falling back to raw ids', () => {
    expect(formatActivityActor({ actor: { email: 'ana@example.com' } })).toBe(
      'ana@example.com',
    )
    expect(formatActivityActor({ changed_by: 3 })).toBe('Unknown user')
  })

  it('hides raw numeric ids in values', () => {
    expect(formatActivityValue('done')).toBe('done')
    expect(formatActivityValue('42')).toBe('a user')
    expect(formatActivityValue(null)).toBe('')
  })
})
