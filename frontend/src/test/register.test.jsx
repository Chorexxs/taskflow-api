import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { AuthProvider } from '../context/AuthContext'
import Register from '../pages/Register'

const mockApi = vi.hoisted(() => ({
  auth: {
    register: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
  },
  users: { me: vi.fn() },
}))

vi.mock('../api', () => ({ api: mockApi }))

function renderRegister() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/register']}>
        <AuthProvider>
          <Routes>
            <Route path="/register" element={<Register />} />
            <Route path="/" element={<div>dashboard</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function passwordInputs() {
  return document.querySelectorAll('input[type="password"]')
}

describe('Register', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('creates the account and redirects to the dashboard', async () => {
    mockApi.auth.register.mockResolvedValue({ id: 7, email: 'new@example.com' })
    mockApi.auth.login.mockResolvedValue({ access_token: 'access', refresh_token: 'refresh' })
    mockApi.users.me.mockResolvedValue({ id: 7, email: 'new@example.com' })

    renderRegister()

    await userEvent.type(screen.getByPlaceholderText('you@example.com'), 'new@example.com')
    const [password, confirmation] = passwordInputs()
    await userEvent.type(password, 'password123')
    await userEvent.type(confirmation, 'password123')
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByText('dashboard')).toBeInTheDocument()
    expect(mockApi.auth.register).toHaveBeenCalledWith({
      email: 'new@example.com',
      password: 'password123',
    })
  })

  it('rejects mismatched passwords without calling the API', async () => {
    renderRegister()

    await userEvent.type(screen.getByPlaceholderText('you@example.com'), 'new@example.com')
    const [password, confirmation] = passwordInputs()
    await userEvent.type(password, 'password123')
    await userEvent.type(confirmation, 'password124')
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    expect(mockApi.auth.register).not.toHaveBeenCalled()
    expect(mockApi.auth.login).not.toHaveBeenCalled()
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument()
  })

  it('shows the verification message instead of logging in', async () => {
    mockApi.auth.register.mockResolvedValue({
      message: 'If the email is available, we sent a verification link.',
    })

    renderRegister()

    await userEvent.type(screen.getByPlaceholderText('you@example.com'), 'new@example.com')
    const [password, confirmation] = passwordInputs()
    await userEvent.type(password, 'password123')
    await userEvent.type(confirmation, 'password123')
    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    expect(
      await screen.findByText(/we sent a verification link/i),
    ).toBeInTheDocument()
    expect(mockApi.auth.login).not.toHaveBeenCalled()
  })
})
