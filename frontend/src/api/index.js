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

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(message, { status, code, details, data } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.data = data;
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

async function request(path, { method = 'GET', token, body, headers = {}, signal } = {}) {
  const isFormData = body instanceof FormData;
  const isUrlEncoded = body instanceof URLSearchParams;

  const requestHeaders = {
    ...(body !== undefined && !isFormData && !isUrlEncoded
      ? { 'Content-Type': 'application/json' }
      : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
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

async function requestBlob(path, { token, signal } = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    signal,
  });

  if (!response.ok) {
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
    create: (token, data) =>
      request('/api/v1/teams/', { method: 'POST', token, body: data }),
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
    create: (token, teamId, data) =>
      request(`/api/v1/teams/${teamId}/projects/`, {
        method: 'POST',
        token,
        body: data,
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
    create: (token, teamId, projectId, data) =>
      request(`/api/v1/teams/${teamId}/projects/${projectId}/tasks/`, {
        method: 'POST',
        token,
        body: data,
      }),
    update: (token, teamId, projectId, taskId, data) =>
      request(`/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}`, {
        method: 'PATCH',
        token,
        body: data,
      }),
    updateStatus: (token, teamId, projectId, taskId, status) =>
      request(`/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/status`, {
        method: 'PATCH',
        token,
        body: { status },
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
    create: (token, teamId, projectId, taskId, data) =>
      request(
        `/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/comments/`,
        { method: 'POST', token, body: data },
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
    upload: (token, teamId, projectId, taskId, formData) =>
      request(
        `/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/attachments/`,
        { method: 'POST', token, body: formData },
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
  },
};
