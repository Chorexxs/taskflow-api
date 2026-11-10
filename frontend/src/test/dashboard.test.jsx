import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import Dashboard from '../pages/Dashboard'

const mockApi = vi.hoisted(() => ({
  teams: {
    list: vi.fn(),
    create: vi.fn(),
  },
}))

vi.mock('../api', () => ({ api: mockApi }))

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/teams/:teamId" element={<div>team page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('lists the teams of the current user', async () => {
    mockApi.teams.list.mockResolvedValue([
      { id: 1, name: 'Alpha', slug: 'alpha', description: 'First team' },
    ])

    renderDashboard()

    expect(await screen.findByText('Alpha')).toBeInTheDocument()
    expect(screen.getByText('First team')).toBeInTheDocument()
    expect(mockApi.teams.list).toHaveBeenCalled()
  })

  it('shows an empty state without teams', async () => {
    mockApi.teams.list.mockResolvedValue([])

    renderDashboard()

    expect(await screen.findByText('No teams yet')).toBeInTheDocument()
  })

  it('creates a team from the modal', async () => {
    mockApi.teams.list.mockResolvedValue([])
    mockApi.teams.create.mockResolvedValue({ id: 2, name: 'Beta', slug: 'beta' })

    renderDashboard()
    await screen.findByText('No teams yet')

    await userEvent.click(screen.getByRole('button', { name: /new team/i }))
    await userEvent.type(screen.getByPlaceholderText('My Team'), 'Beta')
    await userEvent.type(screen.getByPlaceholderText('my-team'), 'beta')
    await userEvent.click(screen.getByRole('button', { name: /^create$/i }))

    await waitFor(() =>
      expect(mockApi.teams.create).toHaveBeenCalledWith(null, {
        name: 'Beta',
        slug: 'beta',
        description: '',
      }),
    )
  })
})
