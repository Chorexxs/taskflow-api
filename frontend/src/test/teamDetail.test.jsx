import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { AuthProvider } from '../context/AuthContext'
import TeamDetail from '../pages/TeamDetail'

const mockApi = vi.hoisted(() => ({
  users: { me: vi.fn() },
  teams: {
    get: vi.fn(),
    listMembers: vi.fn(),
    addMember: vi.fn(),
    update: vi.fn(),
    updateMemberRole: vi.fn(),
    removeMember: vi.fn(),
  },
  projects: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    restore: vi.fn(),
  },
}))

vi.mock('../api', () => ({ api: mockApi }))

function renderTeamDetail() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/teams/team-one']}>
        <AuthProvider>
          <Routes>
            <Route path="/teams/:teamId" element={<TeamDetail />} />
            <Route path="/teams/:teamId/projects/:projectId" element={<div>board</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('TeamDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem('access_token', 'access-token')
    localStorage.setItem('refresh_token', 'refresh-token')

    mockApi.users.me.mockResolvedValue({ id: 1, email: 'admin@test.com' })
    mockApi.teams.get.mockResolvedValue({
      id: 1,
      name: 'Team One',
      slug: 'team-one',
      description: 'The team',
    })
    mockApi.projects.list.mockResolvedValue([
      { id: 10, name: 'Project One', description: 'First project', status: 'active' },
    ])
    mockApi.teams.listMembers.mockResolvedValue([
      { user_id: 1, role: 'admin', user: { email: 'admin@test.com' } },
      { user_id: 2, role: 'member', user: { email: 'member@test.com' } },
    ])
  })

  it('shows the team, its projects and its members', async () => {
    renderTeamDetail()

    expect(await screen.findByText('Team One')).toBeInTheDocument()
    expect(await screen.findByText('Project One')).toBeInTheDocument()
    expect(await screen.findByText('member@test.com')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /new project/i })).toBeInTheDocument()
  })

  it('creates a project as an admin', async () => {
    mockApi.projects.create.mockResolvedValue({ id: 11, name: 'Project Two' })
    renderTeamDetail()

    await screen.findByText('Project One')
    await userEvent.click(await screen.findByRole('button', { name: /new project/i }))

    const dialog = screen.getByRole('dialog', { name: /create project/i })
    await userEvent.type(within(dialog).getByPlaceholderText('My Project'), 'Project Two')
    await userEvent.click(within(dialog).getByRole('button', { name: /^create project$/i }))

    await waitFor(() =>
      expect(mockApi.projects.create).toHaveBeenCalledWith('access-token', 'team-one', {
        name: 'Project Two',
        description: '',
      }),
    )
  })
})
