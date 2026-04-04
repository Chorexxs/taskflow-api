const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
  baseURL: API_URL,
  
  auth: {
    register: (data) => fetch(`${API_URL}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(r => r.json()),
    
    login: (credentials) => {
      const params = new URLSearchParams();
      params.append('username', credentials.email);
      params.append('password', credentials.password);
      return fetch(`${API_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: params,
      }).then(r => r.json());
    },
    
    refresh: (refreshToken) => fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).then(r => r.json()),
    
    logout: (token) => fetch(`${API_URL}/api/v1/auth/logout`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
    }).then(r => r.json()),
  },
  
  users: {
    me: (token) => fetch(`${API_URL}/api/v1/users/me`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    update: (token, data) => fetch(`${API_URL}/api/v1/users/me`, {
      method: 'PUT',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    }).then(r => r.json()),
  },
  
  teams: {
    list: (token) => fetch(`${API_URL}/api/v1/teams/`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    get: (token, teamId) => fetch(`${API_URL}/api/v1/teams/${teamId}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    create: (token, data) => fetch(`${API_URL}/api/v1/teams/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    }).then(r => r.json()),
    
    addMember: (token, teamId, email, role) => fetch(`${API_URL}/api/v1/teams/${teamId}/members`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify({ email, role }),
    }).then(r => r.json()),
    
    removeMember: (token, teamId, userId) => fetch(`${API_URL}/api/v1/teams/${teamId}/members/${userId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    updateMemberRole: (token, teamId, userId, role) => fetch(`${API_URL}/api/v1/teams/${teamId}/members/${userId}`, {
      method: 'PATCH',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify({ role }),
    }).then(r => r.json()),
  },
  
  projects: {
    list: (token, teamId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    get: (token, teamId, projectId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    create: (token, teamId, data) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    }).then(r => r.json()),
    
    update: (token, teamId, projectId, data) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}`, {
      method: 'PATCH',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    }).then(r => r.json()),
    
    delete: (token, teamId, projectId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    archive: (token, teamId, projectId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/archive`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
  },
  
  tasks: {
    list: (token, teamId, projectId, params = {}) => {
      const query = new URLSearchParams(params).toString();
      return fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/?${query}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }).then(r => r.json());
    },
    
    get: (token, teamId, projectId, taskId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    create: (token, teamId, projectId, data) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    }).then(r => r.json()),
    
    update: (token, teamId, projectId, taskId, data) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}`, {
      method: 'PATCH',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    }).then(r => r.json()),
    
    delete: (token, teamId, projectId, taskId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    assign: (token, teamId, projectId, taskId, userId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/assign`, {
      method: 'PATCH',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify({ assigned_to: userId }),
    }).then(r => r.json()),
  },
  
  comments: {
    list: (token, teamId, projectId, taskId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/comments/`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    create: (token, teamId, projectId, taskId, data) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/comments/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    }).then(r => r.json()),
    
    delete: (token, teamId, projectId, taskId, commentId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/comments/${commentId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
  },
  
  notifications: {
    list: (token) => fetch(`${API_URL}/api/v1/notifications/`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    markRead: (token, id) => fetch(`${API_URL}/api/v1/notifications/${id}/read`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    markAllRead: (token) => fetch(`${API_URL}/api/v1/notifications/read-all`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
  },
};
