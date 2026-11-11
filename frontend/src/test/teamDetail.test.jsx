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
    search: vi.fn(),
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

  it('invites a member', async () => {
    mockApi.teams.addMember.mockResolvedValue({ user_id: 3, role: 'member' })
    renderTeamDetail()

    await screen.findByText('member@test.com')
    await userEvent.click(screen.getByRole('button', { name: /\+ invite/i }))

    const dialog = screen.getByRole('dialog', { name: /add team member/i })
    await userEvent.type(within(dialog).getByLabelText('Email'), 'new@test.com')
    await userEvent.selectOptions(within(dialog).getByLabelText('Role'), 'member')
    await userEvent.click(within(dialog).getByRole('button', { name: /send invite/i }))

    await waitFor(() =>
      expect(mockApi.teams.addMember).toHaveBeenCalledWith(
        'access-token',
        'team-one',
        'new@test.com',
        'member',
      ),
    )
  })

  it('updates a member role', async () => {
    mockApi.teams.updateMemberRole.mockResolvedValue({ user_id: 2, role: 'admin' })
    renderTeamDetail()

    const roleSelect = await screen.findByLabelText('Role for member@test.com')
    await userEvent.selectOptions(roleSelect, 'admin')

    await waitFor(() =>
      expect(mockApi.teams.updateMemberRole).toHaveBeenCalledWith(
        'access-token',
        'team-one',
        2,
        'admin',
      ),
    )
  })

  it('removes a member after confirmation', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    mockApi.teams.removeMember.mockResolvedValue(null)
    renderTeamDetail()

    await screen.findByText('member@test.com')
    await userEvent.click(screen.getByTitle('Remove member'))

    await waitFor(() =>
      expect(mockApi.teams.removeMember).toHaveBeenCalledWith(
        'access-token',
        'team-one',
        2,
      ),
    )
  })

  it('edits the team', async () => {
    mockApi.teams.update.mockResolvedValue({ id: 1, name: 'Renamed Team' })
    renderTeamDetail()

    await screen.findByText('Team One')
    await userEvent.click(screen.getByRole('button', { name: /edit team/i }))
    const nameInput = screen.getByLabelText('Team Name')
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, 'Renamed Team')
    await userEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() =>
      expect(mockApi.teams.update).toHaveBeenCalledWith(
        'access-token',
        'team-one',
        expect.objectContaining({ name: 'Renamed Team' }),
      ),
    )
  })

  it('edits and restores projects', async () => {
    mockApi.projects.update.mockResolvedValue({ id: 10, name: 'Renamed Project' })
    mockApi.projects.restore.mockResolvedValue({ id: 12, status: 'active' })
    mockApi.projects.list.mockResolvedValue([
      { id: 10, name: 'Project One', description: 'First', status: 'active' },
      { id: 12, name: 'Archived One', description: 'Old', status: 'archived' },
    ])
    renderTeamDetail()

    await screen.findByText('Project One')
    await userEvent.click(screen.getByTitle('Edit project'))
    const dialog = screen.getByRole('dialog', { name: /edit project/i })
    const nameInput = within(dialog).getByLabelText('Name')
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, 'Renamed Project')
    await userEvent.click(within(dialog).getByRole('button', { name: /save changes/i }))

    await waitFor(() =>
      expect(mockApi.projects.update).toHaveBeenCalledWith(
        'access-token',
        'team-one',
        10,
        expect.objectContaining({ name: 'Renamed Project' }),
      ),
    )

    await userEvent.click(screen.getByTitle('Restore project'))
    await waitFor(() =>
      expect(mockApi.projects.restore).toHaveBeenCalledWith('access-token', 'team-one', 12),
    )
  })

  it('searches projects and tasks', async () => {
    mockApi.teams.search.mockResolvedValue({
      projects: { items: [{ id: 10, name: 'Search Project' }] },
      tasks: { items: [{ id: 5, project_id: 10, title: 'Search Task' }] },
    })
    renderTeamDetail()

    await screen.findByText('Team One')
    await userEvent.type(screen.getByLabelText('Search team'), 'search')

    expect(await screen.findByText('Search Project')).toBeInTheDocument()
    expect(await screen.findByText('Search Task')).toBeInTheDocument()
  })

  it('toggles archived projects', async () => {
    renderTeamDetail()

    await screen.findByText('Project One')
    await userEvent.click(screen.getByRole('checkbox', { name: /show archived/i }))

    await waitFor(() =>
      expect(mockApi.projects.list).toHaveBeenLastCalledWith('access-token', 'team-one', {
        include_archived: true,
      }),
    )
  })
})
