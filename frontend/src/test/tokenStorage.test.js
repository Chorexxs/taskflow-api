import { beforeEach, describe, expect, it } from 'vitest'

import {
  clearStoredTokens,
  getAccessToken,
  getRefreshToken,
  storeAccessToken,
  storeRefreshToken,
  storeTokens,
  TOKEN_STORAGE_KEYS,
} from '../api/tokenStorage'

describe('tokenStorage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('stores and reads the token pair', () => {
    storeTokens({ access_token: 'access', refresh_token: 'refresh' })

    expect(getAccessToken()).toBe('access')
    expect(getRefreshToken()).toBe('refresh')
    expect(localStorage.getItem(TOKEN_STORAGE_KEYS.access)).toBe('access')
    expect(localStorage.getItem(TOKEN_STORAGE_KEYS.refresh)).toBe('refresh')
  })

  it('removes a single token when it is set to null', () => {
    storeTokens({ access_token: 'access', refresh_token: 'refresh' })

    storeAccessToken(null)
    storeRefreshToken(null)

    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
  })

  it('clears the session including the legacy user_id', () => {
    localStorage.setItem('user_id', '1')
    storeTokens({ access_token: 'access', refresh_token: 'refresh' })

    clearStoredTokens()

    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
    expect(localStorage.getItem('user_id')).toBeNull()
  })
})
