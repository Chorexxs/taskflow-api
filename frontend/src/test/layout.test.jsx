import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { AuthProvider } from '../context/AuthContext'
import Layout from '../components/Layout'

const mockApi = vi.hoisted(() => ({
  users: { me: vi.fn() },
  auth: { logout: vi.fn() },
  notifications: {
    list: vi.fn(),
    unreadCount: vi.fn(),
    stream: vi.fn(),
    markRead: vi.fn(),
    markAllRead: vi.fn(),
  },
}))

vi.mock('../api', () => ({ api: mockApi }))

function renderLayout() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/']}>
        <AuthProvider>
          <Routes>
            <Route
              path="/"
              element={
                <Layout>
                  <div>page content</div>
                </Layout>
              }
            />
            <Route path="/login" element={<div>login screen</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Layout', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    mockApi.notifications.list.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      pages: 0,
      has_next: false,
    })
    mockApi.notifications.unreadCount.mockResolvedValue({ count: 0 })
  })

  it('renders the shell and the page content', async () => {
    renderLayout()

    expect(screen.getByRole('link', { name: /skip to main content/i })).toBeInTheDocument()
    expect(screen.getByText('TaskFlow')).toBeInTheDocument()
    expect(screen.getByText('page content')).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /notifications/i })).toBeInTheDocument()
  })

  it('logs out and returns to the login screen', async () => {
    renderLayout()

    await userEvent.click(screen.getByRole('button', { name: /log out/i }))

    expect(await screen.findByText('login screen')).toBeInTheDocument()
  })
})
