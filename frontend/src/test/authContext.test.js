import { describe, expect, it } from 'vitest'
import { getJwtExpiry } from '../context/auth-context'

function tokenWithPayload(payload) {
  const encoded = btoa(JSON.stringify(payload))
    .replace(/=+$/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
  return `header.${encoded}.signature`
}

describe('getJwtExpiry', () => {
  it('reads the exp claim as milliseconds', () => {
    const token = tokenWithPayload({ sub: 'user@example.com', exp: 1_700_000_000 })
    expect(getJwtExpiry(token)).toBe(1_700_000_000_000)
  })

  it('returns null for malformed tokens', () => {
    expect(getJwtExpiry('not-a-jwt')).toBeNull()
    expect(getJwtExpiry('header.payload.signature')).toBeNull()
  })
})
