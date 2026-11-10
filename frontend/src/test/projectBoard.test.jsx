import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { AuthProvider } from '../context/AuthContext'
import ProjectBoard from '../pages/ProjectBoard'

const mockApi = vi.hoisted(() => ({
  users: { me: vi.fn() },
  tasks: { list: vi.fn(), create: vi.fn(), updateStatus: vi.fn() },
  teams: { listMembers: vi.fn() },
  projects: {
    get: vi.fn(),
    getActivity: vi.fn(),
    update: vi.fn(),
    archive: vi.fn(),
  },
}))

vi.mock('../api', () => ({ api: mockApi }))

function renderBoard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/teams/team-one/projects/10']}>
        <AuthProvider>
          <Routes>
            <Route path="/teams/:teamId/projects/:projectId" element={<ProjectBoard />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const task = {
  id: 1,
  title: 'Task One',
  description: 'Do the thing',
  status: 'todo',
  priority: 'high',
  created_by: 1,
  assignee: null,
  due_date: null,
}

describe('ProjectBoard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem('access_token', 'access-token')

    mockApi.users.me.mockResolvedValue({ id: 1, email: 'admin@test.com' })
    mockApi.tasks.list.mockResolvedValue({
      items: [task],
      total: 1,
      page: 1,
      pages: 1,
      has_next: false,
    })
    mockApi.teams.listMembers.mockResolvedValue([
      { user_id: 1, role: 'admin', user: { email: 'admin@test.com' } },
    ])
    mockApi.projects.getActivity.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      pages: 0,
      has_next: false,
    })
    mockApi.projects.get.mockResolvedValue({
      id: 10,
      name: 'Project One',
      description: 'First project',
      status: 'active',
    })
  })

  it('renders the project board with its tasks', async () => {
    renderBoard()

    expect(await screen.findByText('Task One')).toBeInTheDocument()
    expect(screen.getByText('To Do')).toBeInTheDocument()
    expect(screen.getByText('In Progress')).toBeInTheDocument()
    expect(screen.getByText('Done')).toBeInTheDocument()
    expect(mockApi.tasks.list).toHaveBeenCalledWith(
      'access-token',
      'team-one',
      '10',
      expect.objectContaining({ page: 1, page_size: 50 }),
    )
  })

  it('creates a task from the modal', async () => {
    mockApi.tasks.create.mockResolvedValue({ id: 2, title: 'Second task', status: 'todo' })
    renderBoard()

    await screen.findByText('Task One')
    await userEvent.click(screen.getByRole('button', { name: /new task/i }))

    const dialog = screen.getByRole('dialog', { name: /create task/i })
    await userEvent.type(within(dialog).getByPlaceholderText('Task title'), 'Second task')
    await userEvent.click(within(dialog).getByRole('button', { name: /^create task$/i }))

    await waitFor(() =>
      expect(mockApi.tasks.create).toHaveBeenCalledWith(
        'access-token',
        'team-one',
        '10',
        expect.objectContaining({ title: 'Second task' }),
      ),
    )
  })

  it('toggles filters and the activity panel', async () => {
    renderBoard()
    await screen.findByText('Task One')

    await userEvent.click(screen.getByRole('button', { name: /toggle filters/i }))
    expect(screen.getByText('All Status')).toBeInTheDocument()
    expect(screen.getByText('All Priorities')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /project activity/i }))
    const dialog = screen.getByRole('dialog', { name: /project activity/i })
    expect(within(dialog).getByText('Project Activity')).toBeInTheDocument()
    expect(within(dialog).getByText(/no activity/i)).toBeInTheDocument()
  })

  it('updates the project from the settings modal', async () => {
    mockApi.projects.update.mockResolvedValue({ id: 10, name: 'Renamed' })
    renderBoard()

    await screen.findByText('Task One')
    await userEvent.click(await screen.findByRole('button', { name: /project settings/i }))

    const dialog = screen.getByRole('dialog', { name: /project settings/i })
    const nameInput = within(dialog).getByPlaceholderText('Project name')
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, 'Renamed')
    await userEvent.click(within(dialog).getByRole('button', { name: /save changes/i }))

    await waitFor(() =>
      expect(mockApi.projects.update).toHaveBeenCalledWith(
        'access-token',
        'team-one',
        '10',
        expect.objectContaining({ name: 'Renamed' }),
      ),
    )
  })
})
