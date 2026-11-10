import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, nextSseBackoff, parseSseFrame } from '../api'

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

describe('API client', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sends the refresh token in the JSON body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ access_token: 'a', refresh_token: 'b', token_type: 'bearer' }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await api.auth.refresh('refresh-token')

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toContain('/api/v1/auth/refresh')
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body)).toEqual({ refresh_token: 'refresh-token' })
  })

  it('throws a typed ApiError for non-2xx responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(() =>
        Promise.resolve(jsonResponse({ detail: 'Incorrect email or password' }, 401)),
      ),
    )

    await expect(api.auth.refresh('invalid')).rejects.toMatchObject({
      name: 'ApiError',
      status: 401,
      message: 'Incorrect email or password',
    })
  })

  it('sends user_id (not assigned_to) when assigning a task', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1 }))
    vi.stubGlobal('fetch', fetchMock)

    await api.tasks.assign('token', 'team', 'project', 'task', 42)

    const [, options] = fetchMock.mock.calls[0]
    expect(JSON.parse(options.body)).toEqual({ user_id: 42 })
  })

  it('returns null for 204 responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))

    await expect(api.tasks.delete('token', 'team', 'project', 'task')).resolves.toBeNull()
  })

  it('refreshes once on 401 and retries the original request', async () => {
    localStorage.setItem('refresh_token', 'old-refresh')
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: 'expired' }, 401))
      .mockResolvedValueOnce(
        jsonResponse({ access_token: 'new-access', refresh_token: 'new-refresh' }),
      )
      .mockResolvedValueOnce(jsonResponse({ id: 1, email: 'user@example.com' }))
    vi.stubGlobal('fetch', fetchMock)

    const user = await api.users.me('old-access')

    expect(user.email).toBe('user@example.com')
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe('Bearer new-access')
    expect(localStorage.getItem('access_token')).toBe('new-access')
    expect(localStorage.getItem('refresh_token')).toBe('new-refresh')
  })

  it('clears the session when the refresh token is rejected', async () => {
    localStorage.setItem('access_token', 'old-access')
    localStorage.setItem('refresh_token', 'old-refresh')
    localStorage.setItem('user_id', '1')
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: 'expired' }, 401))
      .mockResolvedValueOnce(jsonResponse({ detail: 'reuse' }, 401))
    vi.stubGlobal('fetch', fetchMock)

    await expect(api.users.me('old-access')).rejects.toThrow()

    expect(localStorage.getItem('access_token')).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
    expect(localStorage.getItem('user_id')).toBeNull()
  })

  it('does not retry auth endpoints with a refresh', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: 'bad credentials' }, 401))
    vi.stubGlobal('fetch', fetchMock)

    await expect(api.auth.login({ email: 'a@b.c', password: 'x' })).rejects.toThrow()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('parses SSE data frames and ignores heartbeats', () => {
    expect(
      parseSseFrame('id: 7\nevent: notification\ndata: {"id":7,"message":"Hi"}'),
    ).toEqual({ id: 7, message: 'Hi' })
    expect(parseSseFrame(': heartbeat')).toBeNull()
  })

  it('backs off exponentially for SSE reconnects', () => {
    expect(nextSseBackoff(0, { random: () => 0 })).toBe(1000)
    expect(nextSseBackoff(1, { random: () => 0 })).toBe(2000)
    expect(nextSseBackoff(2, { random: () => 0 })).toBe(4000)
    expect(nextSseBackoff(10, { random: () => 0 })).toBe(30000)
    expect(nextSseBackoff(1, { random: () => 1 })).toBe(2400)
  })
})
