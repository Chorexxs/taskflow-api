/**
 * TaskFlow Frontend - API client.
 *
 * A single, consistent wrapper around `fetch` that:
 * - attaches the bearer token;
 * - serializes JSON and multipart bodies correctly;
 * - throws a typed `ApiError` for non-2xx responses;
 * - returns `null` for 204 responses.
 *
 * Set `VITE_API_URL` to point at the backend. It defaults to localhost.
 */

const API_URL =
  globalThis.__TASKFLOW_API_URL__ ||
  import.meta.env.VITE_API_URL ||
  'http://localhost:8000';

export class ApiError extends Error {
  constructor(message, { status, code, details, data, retryAfter } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.data = data;
    this.retryAfter = retryAfter ?? null;
  }
}

function buildQuery(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined),
  );
  const query = new URLSearchParams(clean).toString();
  return query ? `?${query}` : '';
}

async function parseResponse(response) {
  if (response.status === 204) return null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json().catch(() => null);
  }
  return response.text();
}

function emitSessionEvent(name, detail) {
  if (typeof window !== 'undefined' && window.dispatchEvent) {
    window.dispatchEvent(new CustomEvent(name, { detail }));
  }
}

/**
 * Generate a key for the `Idempotency-Key` header.
 *
 * A retry (including the transparent 401 refresh) reuses the same key, so the
 * API replays the original response instead of creating a duplicate resource.
 */
export function newIdempotencyKey() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `tf-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function clearStoredSession() {
  if (typeof localStorage === 'undefined') return;
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user_id');
}

let refreshPromise = null;

/**
 * Refresh the session once for every caller (single-flight) and persist the
 * rotated pair. Throws `ApiError` when the refresh token is no longer valid.
 */
async function refreshSession() {
  if (refreshPromise) return refreshPromise;

  const refreshToken =
    typeof localStorage !== 'undefined'
      ? localStorage.getItem('refresh_token')
      : null;
  if (!refreshToken) {
    clearStoredSession();
    emitSessionEvent('taskflow:logout');
    throw new ApiError('Session expired', { status: 401, code: 'UNAUTHORIZED' });
  }

  refreshPromise = (async () => {
    const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    const data = await parseResponse(response);
    if (!response.ok) {
      const errorPayload = data?.error || {};
      throw new ApiError(errorPayload.message || 'Session expired', {
        status: response.status,
        code: errorPayload.code || 'UNAUTHORIZED',
        details: errorPayload.details,
        data,
      });
    }

    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    emitSessionEvent('taskflow:session', data);
    return data.access_token;
  })().finally(() => {
    refreshPromise = null;
  });

  try {
    return await refreshPromise;
  } catch (error) {
    clearStoredSession();
    emitSessionEvent('taskflow:logout');
    throw error;
  }
}

async function request(
  path,
  { method = 'GET', token, body, headers = {}, signal, retry = false, idempotencyKey } = {},
) {
  const isFormData = body instanceof FormData;
  const isUrlEncoded = body instanceof URLSearchParams;

  const requestHeaders = {
    ...(body !== undefined && !isFormData && !isUrlEncoded
      ? { 'Content-Type': 'application/json' }
      : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}),
    ...headers,
  };

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers: requestHeaders,
    body:
      body === undefined
        ? undefined
        : isFormData || isUrlEncoded
          ? body
          : JSON.stringify(body),
    signal,
  });

  const data = await parseResponse(response);

  if (!response.ok) {
    const isAuthEndpoint = path.startsWith('/api/v1/auth/');
    if (response.status === 401 && token && !retry && !isAuthEndpoint) {
      const newToken = await refreshSession();
      return request(path, {
        method,
        token: newToken,
        body,
        headers,
        signal,
        retry: true,
        idempotencyKey,
      });
    }

    const errorPayload = data?.error || {};
    const detail = data?.detail;
    const message =
      errorPayload.message ||
      (typeof detail === 'string' ? detail : null) ||
      (Array.isArray(detail) ? detail.map((item) => item.msg).join(', ') : null) ||
      data?.message ||
      `Request failed with status ${response.status}`;

    throw new ApiError(message, {
      status: response.status,
      code: errorPayload.code,
      details: errorPayload.details,
      data,
    });
  }

  return data;
}

async function requestBlob(path, { token, signal, retry = false } = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    signal,
  });

  if (!response.ok) {
    if (response.status === 401 && token && !retry) {
      const newToken = await refreshSession();
      return requestBlob(path, { token: newToken, signal, retry: true });
    }
    let data = null;
    try {
      data = await response.json();
    } catch {
      // Binary endpoints may not return JSON on error.
    }
    const errorPayload = data?.error || {};
    throw new ApiError(errorPayload.message || data?.detail || 'Download failed', {
      status: response.status,
      code: errorPayload.code,
      details: errorPayload.details,
      data,
    });
  }

  return response.blob();
}

/**
 * Parse one SSE frame (already split on the blank line).
 * Returns the decoded JSON payload or `null` for heartbeats/comments.
 */
export function parseSseFrame(frame) {
  const data = frame
    .split('\n')
    .filter((line) => line.startsWith('data: '))
    .map((line) => line.slice(6))
    .join('\n');
  if (!data) return null;
  try {
    return JSON.parse(data);
  } catch {
    return null;
  }
}

/**
 * Exponential backoff with jitter for SSE reconnects.
 *
 * The first retry waits ~1 s, then ~2 s, 4 s… capped at 30 s. "Reconnect in
 * under 5 s" holds for the first two attempts after a drop.
 */
export function nextSseBackoff(
  attempt,
  { baseMs = 1000, maxMs = 30000, random = Math.random } = {},
) {
  const exponential = Math.min(maxMs, baseMs * 2 ** Math.max(0, attempt));
  const jitter = exponential * 0.2 * random();
  return Math.min(maxMs, Math.round(exponential + jitter));
}

/**
 * Subscribe to notification SSE with the bearer token.
 *
 * EventSource cannot send custom headers, so this uses `fetch` streaming.
 * Resolves when the stream closes or the caller aborts; rejects on HTTP error
 * so the caller can fall back to polling and reconnect with backoff.
 */
async function streamNotifications(token, { signal, onEvent, onOpen } = {}) {
  const response = await fetch(`${API_URL}/api/v1/notifications/stream`, {
    headers: {
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    signal,
  });

  if (!response.ok || !response.body) {
    const data = await response.json().catch(() => null);
    const retryAfter = Number(response.headers.get('Retry-After'));
    throw new ApiError(data?.detail || 'Notification stream unavailable', {
      status: response.status,
      code: data?.error?.code,
      retryAfter: Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : null,
    });
  }

  onOpen?.();
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let boundary = buffer.indexOf('\n\n');
      while (boundary !== -1) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const payload = parseSseFrame(frame);
        if (payload) onEvent?.(payload);
        boundary = buffer.indexOf('\n\n');
      }
    }
  } finally {
    reader.releaseLock?.();
  }
}

export const api = {
  baseURL: API_URL,

  auth: {
    register: (data) =>
      request('/api/v1/auth/register', { method: 'POST', body: data }),

    login: (credentials) => {
      const body = new URLSearchParams();
      body.append('username', credentials.email);
      body.append('password', credentials.password);
      return request('/api/v1/auth/login', { method: 'POST', body });
    },

    refresh: (refreshToken) =>
      request('/api/v1/auth/refresh', {
        method: 'POST',
        body: { refresh_token: refreshToken },
      }),

    logout: (token, refreshToken) =>
      request('/api/v1/auth/logout', {
        method: 'POST',
        token,
        body: refreshToken ? { refresh_token: refreshToken } : {},
      }),
  },

  users: {
    me: (token) => request('/api/v1/users/me', { token }),
    update: (token, data) =>
      request('/api/v1/users/me', { method: 'PUT', token, body: data }),
  },

  teams: {
    list: (token, params = {}) =>
      request(`/api/v1/teams/${buildQuery(params)}`, { token }).then(
        (data) => data.items ?? data,
      ),
    get: (token, teamId) => request(`/api/v1/teams/${teamId}`, { token }),
    listMembers: (token, teamId, params = {}) =>
      request(`/api/v1/teams/${teamId}/members${buildQuery(params)}`, { token }).then(
        (data) => data.items ?? data,
      ),
    create: (token, data, idempotencyKey = newIdempotencyKey()) =>
      request('/api/v1/teams/', {
        method: 'POST',
        token,
        body: data,
        idempotencyKey,
      }),
    update: (token, teamId, data) =>
      request(`/api/v1/teams/${teamId}`, { method: 'PATCH', token, body: data }),
    addMember: (token, teamId, email, role) =>
      request(`/api/v1/teams/${teamId}/members`, {
        method: 'POST',
        token,
        body: { email, role },
      }),
    removeMember: (token, teamId, userId) =>
      request(`/api/v1/teams/${teamId}/members/${userId}`, {
        method: 'DELETE',
        token,
      }),
    updateMemberRole: (token, teamId, userId, role) =>
      request(`/api/v1/teams/${teamId}/members/${userId}`, {
        method: 'PATCH',
        token,
        body: { role },
      }),
    search: (token, teamId, query, params = {}) =>
      request(
        `/api/v1/teams/${teamId}/search${buildQuery({ q: query, ...params })}`,
        { token },
      ),
  },

  projects: {
    list: (token, teamId, params = {}) =>
      request(`/api/v1/teams/${teamId}/projects/${buildQuery(params)}`, {
        token,
      }).then((data) => data.items ?? data),
    get: (token, teamId, projectId) =>
      request(`/api/v1/teams/${teamId}/projects/${projectId}`, { token }),
    create: (token, teamId, data, idempotencyKey = newIdempotencyKey()) =>
      request(`/api/v1/teams/${teamId}/projects/`, {
        method: 'POST',
        token,
        body: data,
        idempotencyKey,
      }),
    update: (token, teamId, projectId, data) =>
      request(`/api/v1/teams/${teamId}/projects/${projectId}`, {
        method: 'PATCH',
        token,
        body: data,
      }),
    delete: (token, teamId, projectId) =>
      request(`/api/v1/teams/${teamId}/projects/${projectId}`, {
        method: 'DELETE',
        token,
      }),
    archive: (token, teamId, projectId) =>
      request(`/api/v1/teams/${teamId}/projects/${projectId}/archive`, {
        method: 'POST',
        token,
      }),
    restore: (token, teamId, projectId) =>
      request(`/api/v1/teams/${teamId}/projects/${projectId}/restore`, {
        method: 'POST',
        token,
      }),
    getActivity: (token, teamId, projectId, params = {}) =>
      request(
        `/api/v1/teams/${teamId}/projects/${projectId}/activity${buildQuery(params)}`,
        { token },
      ),
  },

  tasks: {
    list: (token, teamId, projectId, params = {}) =>
      request(
        `/api/v1/teams/${teamId}/projects/${projectId}/tasks/${buildQuery(params)}`,
        { token },
      ),
    get: (token, teamId, projectId, taskId) =>
      request(`/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}`, {
        token,
      }),
    create: (token, teamId, projectId, data, idempotencyKey = newIdempotencyKey()) =>
      request(`/api/v1/teams/${teamId}/projects/${projectId}/tasks/`, {
        method: 'POST',
        token,
        body: data,
        idempotencyKey,
      }),
    update: (token, teamId, projectId, taskId, data) =>
      request(`/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}`, {
        method: 'PATCH',
        token,
        body: data,
      }),
    updateStatus: (token, teamId, projectId, taskId, status, position) =>
      request(`/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/status`, {
        method: 'PATCH',
        token,
        body: position == null ? { status } : { status, position },
      }),
    delete: (token, teamId, projectId, taskId) =>
      request(`/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}`, {
        method: 'DELETE',
        token,
      }),
    assign: (token, teamId, projectId, taskId, userId) =>
      request(
        `/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/assign`,
        {
          method: 'PATCH',
          token,
          body: { user_id: userId },
        },
      ),
    getActivity: (token, teamId, projectId, taskId, params = {}) =>
      request(
        `/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/activity${buildQuery(params)}`,
        { token },
      ),
  },

  comments: {
    list: (token, teamId, projectId, taskId, params = {}) =>
      request(
        `/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/comments/${buildQuery(params)}`,
        { token },
      ),
    create: (token, teamId, projectId, taskId, data, idempotencyKey = newIdempotencyKey()) =>
      request(
        `/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/comments/`,
        { method: 'POST', token, body: data, idempotencyKey },
      ),
    update: (token, teamId, projectId, taskId, commentId, data) =>
      request(
        `/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/comments/${commentId}`,
        { method: 'PATCH', token, body: data },
      ),
    delete: (token, teamId, projectId, taskId, commentId) =>
      request(
        `/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/comments/${commentId}`,
        { method: 'DELETE', token },
      ),
  },

  attachments: {
    upload: (token, teamId, projectId, taskId, formData, idempotencyKey = newIdempotencyKey()) =>
      request(
        `/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/attachments/`,
        { method: 'POST', token, body: formData, idempotencyKey },
      ),
    list: (token, teamId, projectId, taskId, params = {}) =>
      request(
        `/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/attachments/${buildQuery(params)}`,
        { token },
      ).then((data) => data.items ?? data),
    download: (token, teamId, projectId, taskId, attachmentId) =>
      requestBlob(
        `/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/attachments/${attachmentId}/download`,
        { token },
      ),
    delete: (token, teamId, projectId, taskId, attachmentId) =>
      request(
        `/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/attachments/${attachmentId}`,
        { method: 'DELETE', token },
      ),
  },

  notifications: {
    list: (token, params = {}) =>
      request(`/api/v1/notifications/${buildQuery(params)}`, { token }),
    unreadCount: (token) =>
      request('/api/v1/notifications/unread-count', { token }),
    markRead: (token, id) =>
      request(`/api/v1/notifications/${id}/read`, { method: 'PATCH', token }),
    markAllRead: (token) =>
      request('/api/v1/notifications/read-all', { method: 'PATCH', token }),
    stream: (token, { signal, onEvent, onOpen } = {}) =>
      streamNotifications(token, { signal, onEvent, onOpen }),
  },
};
