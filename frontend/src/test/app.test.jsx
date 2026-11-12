import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import App from '../App'
import { AuthProvider } from '../context/AuthContext'

const mockApi = vi.hoisted(() => ({
  users: { me: vi.fn() },
  teams: { list: vi.fn() },
}))

vi.mock('../api', () => ({ api: mockApi }))
vi.mock('../components/Layout', () => ({
  default: ({ children }) => <div data-testid="layout">{children}</div>,
}))

function renderApp(path) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('App routing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    mockApi.teams.list.mockResolvedValue([])
  })

  it('redirects unauthenticated users to login', async () => {
    renderApp('/')

    expect(await screen.findByText('Sign in to your workspace')).toBeInTheDocument()
  })

  it('renders the public login and register routes', async () => {
    renderApp('/register')

    expect(await screen.findByText('Create your account')).toBeInTheDocument()
  })

  it('renders the 404 page for unknown routes', async () => {
    renderApp('/missing-page')

    expect(await screen.findByText('Page not found')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /go to dashboard/i })).toBeInTheDocument()
  })

  it('renders a protected route for an authenticated user', async () => {
    localStorage.setItem('access_token', 'access-token')
    localStorage.setItem('refresh_token', 'refresh-token')
    mockApi.users.me.mockResolvedValue({ id: 1, email: 'admin@test.com' })

    renderApp('/')

    expect(await screen.findByTestId('layout')).toBeInTheDocument()
    expect(await screen.findByText('My Teams')).toBeInTheDocument()
  })

  it('does not refetch the user when the client refreshes the token', async () => {
    localStorage.setItem('access_token', 'access-token')
    localStorage.setItem('refresh_token', 'refresh-token')
    mockApi.users.me.mockResolvedValue({ id: 1, email: 'admin@test.com' })

    renderApp('/')
    await screen.findByTestId('layout')
    await waitFor(() => expect(mockApi.users.me).toHaveBeenCalledTimes(1))

    act(() => {
      window.dispatchEvent(
        new CustomEvent('taskflow:session', {
          detail: { access_token: 'refreshed-token', refresh_token: 'refresh-2' },
        }),
      )
    })
    await act(async () => {
      await Promise.resolve()
    })

    expect(mockApi.users.me).toHaveBeenCalledTimes(1)
  })
})
