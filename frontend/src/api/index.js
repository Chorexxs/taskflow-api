/**
 * TaskFlow Frontend - API Client
 * 
 * This module provides a centralized API client for communicating with the TaskFlow backend.
 * It uses the native fetch API and handles authentication tokens automatically.
 * 
 * Configuration:
 * - API_URL: Base URL for the API (default: http://localhost:8000)
 * - Set VITE_API_URL environment variable to configure the production URL
 * 
 * The client is organized by resource type:
 * - auth: Authentication endpoints (login, register, logout, refresh)
 * - users: User management (get current user, update profile)
 * - teams: Team operations (list, create, manage members)
 * - projects: Project operations (list, create, update, delete, archive)
 * - tasks: Task operations (list, create, update, delete, assign)
 * - comments: Comment operations (list, create, delete)
 * - notifications: Notification operations (list, mark read)
 * 
 * All endpoints require a valid JWT token in the Authorization header.
 * Tokens are provided by the AuthContext and automatically included in requests.
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * API client object containing methods for all backend resources.
 * Each method returns a Promise that resolves to the JSON response.
 * 
 * @example
 * // Login user
 * const tokens = await api.auth.login({ email: 'user@example.com', password: 'password' });
 * 
 * // Get user profile
 * const user = await api.users.me(token);
 * 
 * // List teams
 * const teams = await api.teams.list(token);
 */
export const api = {
  /** Base URL for API requests */
  baseURL: API_URL,
  
  /**
   * Authentication endpoints.
   * Handles user registration, login, logout, and token refresh.
   */
  auth: {
    /**
     * Register a new user account.
     * 
     * @param {Object} data - User registration data
     * @param {string} data.email - User's email address
     * @param {string} data.password - User's password
     * @returns {Promise<Object>} Newly created user object
     * 
     * @example
     * const user = await api.auth.register({
     *   email: 'new@example.com',
     *   password: 'securePassword123'
     * });
     */
    register: (data) => fetch(`${API_URL}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(r => r.json()),
    
    /**
     * Authenticate user with email and password.
     * Returns JWT access and refresh tokens on success.
     * 
     * @param {Object} credentials - User credentials
     * @param {string} credentials.email - User's email
     * @param {string} credentials.password - User's password
     * @returns {Promise<Object>} Object with access_token, refresh_token, token_type
     * 
     * @example
     * const { access_token, refresh_token } = await api.auth.login({
     *   email: 'user@example.com',
     *   password: 'password'
     * });
     */
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
    
    /**
     * Refresh access token using a valid refresh token.
     * Issues new tokens and invalidates the old refresh token.
     * 
     * @param {string} refreshToken - Valid refresh token
     * @returns {Promise<Object>} New access_token and refresh_token
     * 
     * @example
     * const newTokens = await api.auth.refresh(oldRefreshToken);
     */
    refresh: (refreshToken) => fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).then(r => r.json()),
    
    /**
     * Logout user and revoke their access token.
     * 
     * @param {string} token - Current access token
     * @returns {Promise<Object>} Success message
     * 
     * @example
     * await api.auth.logout(accessToken);
     */
    logout: (token) => fetch(`${API_URL}/api/v1/auth/logout`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
    }).then(r => r.json()),
  },
  
  /**
   * User management endpoints.
   * Handles getting and updating the current user's profile.
   */
  users: {
    /**
     * Get current authenticated user's profile.
     * 
     * @param {string} token - Valid access token
     * @returns {Promise<Object>} User object with id, email, is_active, created_at
     * 
     * @example
     * const user = await api.users.me(token);
     */
    me: (token) => fetch(`${API_URL}/api/v1/users/me`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    /**
     * Update current user's profile.
     * 
     * @param {string} token - Valid access token
     * @param {Object} data - Fields to update
     * @param {string} [data.email] - New email address
     * @param {string} [data.password] - New password
     * @returns {Promise<Object>} Updated user object
     * 
     * @example
     * const updated = await api.users.me(token, { email: 'new@example.com' });
     */
    update: (token, data) => fetch(`${API_URL}/api/v1/users/me`, {
      method: 'PUT',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    }).then(r => r.json()),
  },
  
  /**
   * Team management endpoints.
   * Handles listing, creating, and managing team members.
   */
  teams: {
    /**
     * Get all teams for the current user.
     * 
     * @param {string} token - Valid access token
     * @returns {Promise<Array>} Array of team objects
     * 
     * @example
     * const teams = await api.teams.list(token);
     */
    list: (token) => fetch(`${API_URL}/api/v1/teams/`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    /**
     * Get a specific team by ID or slug.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @returns {Promise<Object>} Team object
     * 
     * @example
     * const team = await api.teams.get(token, 'my-team');
     */
    get: (token, teamId) => fetch(`${API_URL}/api/v1/teams/${teamId}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    /**
     * Get all members of a team.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @returns {Promise<Array>} Array of member objects with user details
     * 
     * @example
     * const members = await api.teams.listMembers(token, 1);
     */
    listMembers: (token, teamId) => fetch(`${API_URL}/api/v1/teams/${teamId}/members`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    /**
     * Create a new team.
     * 
     * @param {string} token - Valid access token
     * @param {Object} data - Team data
     * @param {string} data.name - Team name
     * @param {string} data.slug - URL-friendly team identifier
     * @param {string} [data.description] - Team description
     * @returns {Promise<Object>} Newly created team
     * 
     * @example
     * const team = await api.teams.create(token, {
     *   name: 'My Team',
     *   slug: 'my-team',
     *   description: 'Team for Project X'
     * });
     */
    create: (token, data) => fetch(`${API_URL}/api/v1/teams/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    }).then(r => r.json()),
    
    /**
     * Add a member to a team.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {string} email - Email of user to add
     * @param {string} role - Role to assign ('admin' or 'member')
     * @returns {Promise<Object>} Created member object
     * 
     * @example
     * await api.teams.addMember(token, 1, 'user@example.com', 'member');
     */
    addMember: (token, teamId, email, role) => fetch(`${API_URL}/api/v1/teams/${teamId}/members`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify({ email, role }),
    }).then(r => r.json()),
    
    /**
     * Remove a member from a team.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {number} userId - ID of user to remove
     * @returns {Promise<void>}
     * 
     * @example
     * await api.teams.removeMember(token, 1, 5);
     */
    removeMember: (token, teamId, userId) => fetch(`${API_URL}/api/v1/teams/${teamId}/members/${userId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    /**
     * Update a member's role.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {number} userId - ID of user to update
     * @param {string} role - New role ('admin' or 'member')
     * @returns {Promise<Object>} Updated member object
     * 
     * @example
     * await api.teams.updateMemberRole(token, 1, 5, 'admin');
     */
    updateMemberRole: (token, teamId, userId, role) => fetch(`${API_URL}/api/v1/teams/${teamId}/members/${userId}`, {
      method: 'PATCH',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify({ role }),
    }).then(r => r.json()),
  },
  
  /**
   * Project management endpoints.
   * Handles listing, creating, updating, and archiving projects.
   */
  projects: {
    /**
     * Get all active projects in a team.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @returns {Promise<Array>} Array of project objects
     * 
     * @example
     * const projects = await api.projects.list(token, 1);
     */
    list: (token, teamId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    /**
     * Get a specific project.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {string|number} projectId - Project ID or name
     * @returns {Promise<Object>} Project object
     * 
     * @example
     * const project = await api.projects.get(token, 1, 'my-project');
     */
    get: (token, teamId, projectId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    /**
     * Create a new project.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {Object} data - Project data
     * @param {string} data.name - Project name
     * @param {string} [data.description] - Project description
     * @returns {Promise<Object>} Newly created project
     * 
     * @example
     * const project = await api.projects.create(token, 1, {
     *   name: 'Website Redesign',
     *   description: 'Redesign company website'
     * });
     */
    create: (token, teamId, data) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    }).then(r => r.json()),
    
    /**
     * Update a project.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {string|number} projectId - Project ID or name
     * @param {Object} data - Fields to update
     * @returns {Promise<Object>} Updated project
     * 
     * @example
     * await api.projects.update(token, 1, 1, { name: 'New Name' });
     */
    update: (token, teamId, projectId, data) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}`, {
      method: 'PATCH',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    }).then(r => r.json()),
    
    /**
     * Delete a project (admin only).
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {string|number} projectId - Project ID or name
     * @returns {Promise<void>}
     * 
     * @example
     * await api.projects.delete(token, 1, 1);
     */
    delete: (token, teamId, projectId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    /**
     * Archive a project (admin only).
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {string|number} projectId - Project ID or name
     * @returns {Promise<Object>} Archived project
     * 
     * @example
     * await api.projects.archive(token, 1, 1);
     */
    archive: (token, teamId, projectId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/archive`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
  },
  
  /**
   * Task management endpoints.
   * Handles listing, creating, updating, deleting, and assigning tasks.
   */
  tasks: {
    /**
     * Get tasks with optional filters and pagination.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {string|number} projectId - Project ID or name
     * @param {Object} [params={}] - Query parameters
     * @param {string} [params.status] - Filter by status (todo, in_progress, done)
     * @param {string} [params.priority] - Filter by priority (low, medium, high)
     * @param {string|number} [params.assigned_to] - Filter by assignee user ID
     * @param {string} [params.due_before] - Filter by due date (before)
     * @param {string} [params.due_after] - Filter by due date (after)
     * @param {string} [params.sort_by] - Sort field (created_at, title, priority, due_date)
     * @param {string} [params.order] - Sort order (asc, desc)
     * @param {number} [params.page] - Page number
     * @param {number} [params.page_size] - Items per page
     * @returns {Promise<Object>} Paginated task response with items, total, page info
     * 
     * @example
     * const result = await api.tasks.list(token, 1, 1, { status: 'todo', priority: 'high' });
     */
    list: (token, teamId, projectId, params = {}) => {
      const filteredParams = Object.fromEntries(
        Object.entries(params).filter(([_, v]) => v !== '' && v !== null && v !== undefined)
      );
      const query = new URLSearchParams(filteredParams).toString();
      return fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/?${query}`, {
        headers: { 'Authorization': `Bearer ${token}` },
      }).then(r => r.json());
    },
    
    /**
     * Get a specific task.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {string|number} projectId - Project ID or name
     * @param {string|number} taskId - Task ID or title
     * @returns {Promise<Object>} Task object with details
     * 
     * @example
     * const task = await api.tasks.get(token, 1, 1, 1);
     */
    get: (token, teamId, projectId, taskId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    /**
     * Create a new task.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {string|number} projectId - Project ID or name
     * @param {Object} data - Task data
     * @param {string} data.title - Task title (required)
     * @param {string} [data.description] - Task description
     * @param {string} [data.priority] - Priority (low, medium, high)
     * @param {string} [data.due_date] - Due date (ISO string)
     * @param {number} [data.assigned_to] - User ID to assign
     * @returns {Promise<Object>} Newly created task
     * @throws {Error} If task creation fails
     * 
     * @example
     * const task = await api.tasks.create(token, 1, 1, {
     *   title: 'Fix login bug',
     *   priority: 'high',
     *   assigned_to: 5
     * });
     */
    create: (token, teamId, projectId, data) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    }).then(async (r) => {
      if (!r.ok) {
        const error = await r.json()
        throw new Error(error.detail || 'Failed to create task')
      }
      return r.json()
    }),
    
    /**
     * Update a task.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {string|number} projectId - Project ID or name
     * @param {string|number} taskId - Task ID or title
     * @param {Object} data - Fields to update
     * @returns {Promise<Object>} Updated task
     * 
     * @example
     * const updated = await api.tasks.update(token, 1, 1, 1, {
     *   status: 'in_progress',
     *   priority: 'low'
     * });
     */
    update: (token, teamId, projectId, taskId, data) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}`, {
      method: 'PATCH',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    }).then(r => r.json()),
    
    /**
     * Delete a task (creator or admin only).
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {string|number} projectId - Project ID or name
     * @param {string|number} taskId - Task ID or title
     * @returns {Promise<void>}
     * 
     * @example
     * await api.tasks.delete(token, 1, 1, 1);
     */
    delete: (token, teamId, projectId, taskId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    /**
     * Assign or unassign a task (admin only).
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {string|number} projectId - Project ID or name
     * @param {string|number} taskId - Task ID or title
     * @param {number|null} userId - User ID to assign, or null to unassign
     * @returns {Promise<Object>} Updated task
     * 
     * @example
     * // Assign to user
     * await api.tasks.assign(token, 1, 1, 1, 5);
     * 
     * // Unassign
     * await api.tasks.assign(token, 1, 1, 1, null);
     */
    assign: (token, teamId, projectId, taskId, userId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/assign`, {
      method: 'PATCH',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify({ assigned_to: userId }),
    }).then(r => r.json()),
  },
  
  /**
   * Comment management endpoints.
   * Handles listing, creating, and deleting comments on tasks.
   */
  comments: {
    /**
     * Get all comments for a task.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {string|number} projectId - Project ID or name
     * @param {string|number} taskId - Task ID or title
     * @returns {Promise<Array>} Array of comment objects
     * 
     * @example
     * const comments = await api.comments.list(token, 1, 1, 1);
     */
    list: (token, teamId, projectId, taskId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/comments/`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    /**
     * Create a comment on a task.
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {string|number} projectId - Project ID or name
     * @param {string|number} taskId - Task ID or title
     * @param {Object} data - Comment data
     * @param {string} data.content - Comment text
     * @returns {Promise<Object>} Created comment
     * 
     * @example
     * const comment = await api.comments.create(token, 1, 1, 1, {
     *   content: 'This looks great!'
     * });
     */
    create: (token, teamId, projectId, taskId, data) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/comments/`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify(data),
    }).then(r => r.json()),
    
    /**
     * Delete a comment (author or admin only).
     * 
     * @param {string} token - Valid access token
     * @param {string|number} teamId - Team ID or slug
     * @param {string|number} projectId - Project ID or name
     * @param {string|number} taskId - Task ID or title
     * @param {number} commentId - Comment ID to delete
     * @returns {Promise<void>}
     * 
     * @example
     * await api.comments.delete(token, 1, 1, 1, 3);
     */
    delete: (token, teamId, projectId, taskId, commentId) => fetch(`${API_URL}/api/v1/teams/${teamId}/projects/${projectId}/tasks/${taskId}/comments/${commentId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
  },
  
  /**
   * Notification endpoints.
   * Handles listing and managing user notifications.
   */
  notifications: {
    /**
     * Get all notifications for the current user.
     * 
     * @param {string} token - Valid access token
     * @returns {Promise<Array>} Array of notification objects
     * 
     * @example
     * const notifications = await api.notifications.list(token);
     */
    list: (token) => fetch(`${API_URL}/api/v1/notifications/`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    /**
     * Mark a notification as read.
     * 
     * @param {string} token - Valid access token
     * @param {number} id - Notification ID
     * @returns {Promise<Object>} Updated notification
     * 
     * @example
     * await api.notifications.markRead(token, 1);
     */
    markRead: (token, id) => fetch(`${API_URL}/api/v1/notifications/${id}/read`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
    
    /**
     * Mark all notifications as read.
     * 
     * @param {string} token - Valid access token
     * @returns {Promise<void>}
     * 
     * @example
     * await api.notifications.markAllRead(token);
     */
    markAllRead: (token) => fetch(`${API_URL}/api/v1/notifications/read-all`, {
      method: 'PATCH',
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(r => r.json()),
  },
};
