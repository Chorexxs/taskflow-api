import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { http, HttpResponse } from 'msw'

import { server } from './mswServer'
import { AuthProvider } from '../context/AuthContext'
import Login from '../pages/Login'
import ProjectBoard from '../pages/ProjectBoard'
import TaskDetail from '../pages/TaskDetail'
import NotificationsBell from '../components/NotificationsBell'

const API = 'http://localhost:8000/api/v1'

function ok(body) {
  return HttpResponse.json(body)
}

function renderApp(ui, { route = '/' } = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

const userPayload = { id: 1, email: 'user@example.com', is_active: true }

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => {
  server.resetHandlers()
  localStorage.clear()
})
afterAll(() => server.close())

beforeEach(() => {
  server.use(http.get(`${API}/users/me`, () => ok(userPayload)))
})

describe('critical UI flows with MSW', () => {
  it('logs in and redirects to the dashboard', async () => {
    server.use(
      http.post(`${API}/auth/login`, () =>
        ok({ access_token: 'access', refresh_token: 'refresh', token_type: 'bearer' }),
      ),
    )
    const user = userEvent.setup()

    renderApp(
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<div>Dashboard home</div>} />
      </Routes>,
      { route: '/login' },
    )

    await user.type(screen.getByLabelText('Email'), 'user@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText('Dashboard home')).toBeInTheDocument()
    expect(localStorage.getItem('access_token')).toBe('access')
  })

  it('renders the Kanban board from the API', async () => {
    localStorage.setItem('access_token', 'access')
    server.use(
      http.get(`${API}/teams/1/members`, () =>
        ok({
          items: [{ user_id: 1, role: 'admin', user: userPayload }],
          total: 1,
          page: 1,
          pages: 1,
          has_next: false,
        }),
      ),
      http.get(`${API}/teams/1/projects/1`, () =>
        ok({ id: 1, name: 'Demo Project', slug: 'demo', status: 'active' }),
      ),
      http.get(`${API}/teams/1/projects/1/activity`, () =>
        ok({ items: [], total: 0, page: 1, pages: 0, has_next: false }),
      ),
      http.get(`${API}/teams/1/projects/1/tasks/`, () =>
        ok({
          items: [
            { id: 1, title: 'Task One', status: 'todo', priority: 'high', created_by: 1 },
            { id: 2, title: 'Task Two', status: 'done', priority: 'low', created_by: 1 },
          ],
          total: 2,
          page: 1,
          pages: 1,
          has_next: false,
        }),
      ),
    )

    renderApp(
      <Routes>
        <Route path="/teams/:teamId/projects/:projectId" element={<ProjectBoard />} />
      </Routes>,
      { route: '/teams/1/projects/1' },
    )

    expect(await screen.findByText('Task One')).toBeInTheDocument()
    expect(screen.getByText('Task Two')).toBeInTheDocument()
  })

  it('renders task details and comments', async () => {
    localStorage.setItem('access_token', 'access')
    server.use(
      http.get(`${API}/teams/1/members`, () => ok({ items: [], total: 0, page: 1, pages: 0, has_next: false })),
      http.get(`${API}/teams/1/projects/1/tasks/1`, () =>
        ok({
          id: 1,
          title: 'Detailed Task',
          description: 'A task body',
          status: 'todo',
          priority: 'medium',
          created_by: 1,
          assignee: null,
        }),
      ),
      http.get(`${API}/teams/1/projects/1/tasks/1/comments/`, () =>
        ok({
          items: [
            {
              id: 1,
              content: 'First comment',
              author_id: 1,
              author: { email: 'user@example.com' },
              created_at: '2026-01-01T00:00:00Z',
            },
          ],
          total: 1,
          page: 1,
          pages: 1,
          has_next: false,
        }),
      ),
      http.get(`${API}/teams/1/projects/1/tasks/1/attachments/`, () =>
        ok({ items: [], total: 0, page: 1, pages: 0, has_next: false }),
      ),
      http.get(`${API}/teams/1/projects/1/tasks/1/activity`, () =>
        ok({ items: [], total: 0, page: 1, pages: 0, has_next: false }),
      ),
    )

    renderApp(
      <Routes>
        <Route path="/teams/:teamId/projects/:projectId/tasks/:taskId" element={<TaskDetail />} />
      </Routes>,
      { route: '/teams/1/projects/1/tasks/1' },
    )

    expect(await screen.findByText('Detailed Task')).toBeInTheDocument()
    expect(screen.getByText('First comment')).toBeInTheDocument()
  })

  it('shows unread notifications and their messages', async () => {
    localStorage.setItem('access_token', 'access')
    server.use(
      http.get(`${API}/notifications/`, () =>
        ok({
          items: [
            {
              id: 1,
              user_id: 1,
              type: 'assigned',
              entity_type: 'task',
              entity_id: 1,
              message: 'You were assigned a task',
              is_read: false,
              created_at: '2026-01-01T00:00:00Z',
            },
          ],
          total: 1,
          page: 1,
          pages: 1,
          has_next: false,
        }),
      ),
      http.get(`${API}/notifications/unread-count`, () => ok({ count: 1 })),
      http.get(`${API}/notifications/stream`, () => HttpResponse.text('')),
    )

    const user = userEvent.setup()
    renderApp(<NotificationsBell />)

    const bell = await screen.findByRole('button', { name: /notifications/i })
    await user.click(bell)

    expect(await screen.findByText('You were assigned a task')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
  })
})
