/**
 * Single source of truth for the browser token storage (T-122).
 *
 * The API client and the auth context must agree on where the session lives;
 * keeping the keys and the reads/writes here avoids two components fighting
 * over `localStorage` and makes the storage easy to replace.
 */

const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
const LEGACY_USER_ID_KEY = 'user_id'

function storage() {
  return typeof localStorage === 'undefined' ? null : localStorage
}

export function getAccessToken() {
  return storage()?.getItem(ACCESS_TOKEN_KEY) ?? null
}

export function getRefreshToken() {
  return storage()?.getItem(REFRESH_TOKEN_KEY) ?? null
}

export function storeTokens({ access_token, refresh_token }) {
  if (access_token !== undefined) storeAccessToken(access_token)
  if (refresh_token !== undefined) storeRefreshToken(refresh_token)
}

export function storeAccessToken(token) {
  const store = storage()
  if (!store) return
  if (token) store.setItem(ACCESS_TOKEN_KEY, token)
  else store.removeItem(ACCESS_TOKEN_KEY)
}

export function storeRefreshToken(token) {
  const store = storage()
  if (!store) return
  if (token) store.setItem(REFRESH_TOKEN_KEY, token)
  else store.removeItem(REFRESH_TOKEN_KEY)
}

export function clearStoredTokens() {
  const store = storage()
  if (!store) return
  store.removeItem(ACCESS_TOKEN_KEY)
  store.removeItem(REFRESH_TOKEN_KEY)
  store.removeItem(LEGACY_USER_ID_KEY)
}

export const TOKEN_STORAGE_KEYS = {
  access: ACCESS_TOKEN_KEY,
  refresh: REFRESH_TOKEN_KEY,
}
