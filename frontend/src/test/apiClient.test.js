import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api, parseSseFrame } from '../api'

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

  it('parses SSE data frames and ignores heartbeats', () => {
    expect(
      parseSseFrame('id: 7\nevent: notification\ndata: {"id":7,"message":"Hi"}'),
    ).toEqual({ id: 7, message: 'Hi' })
    expect(parseSseFrame(': heartbeat')).toBeNull()
  })
})
