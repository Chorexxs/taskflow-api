import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '../context/AuthContext'

const mockNavigate = vi.fn()
const mockApi = vi.hoisted(() => ({
  users: {
    me: vi.fn(() => Promise.resolve({ id: 1, email: 'admin@test.com' })),
  },
  tasks: {
    get: vi.fn(() => Promise.resolve({
      id: 1,
      title: 'Test Task',
      description: 'Test description',
      status: 'todo',
      priority: 'medium',
      created_by: 1,
      assignee: null,
    })),
    getActivity: vi.fn(() => Promise.resolve({ items: [], total: 0, page: 1, pages: 0, has_next: false })),
  },
  comments: {
    list: vi.fn(() => Promise.resolve({
      items: [
        { id: 1, content: 'First comment', author_id: 1, author: { email: 'user1@test.com' }, created_at: '2024-01-01T00:00:00Z' },
        { id: 2, content: 'Second comment', author_id: 2, author: { email: 'user2@test.com' }, created_at: '2024-01-01T00:00:00Z' },
      ],
      total: 2,
      page: 1,
      pages: 1,
      has_next: false,
    })),
    create: vi.fn(() => Promise.resolve({ id: 3, content: 'New comment' })),
    update: vi.fn(() => Promise.resolve({ id: 1, content: 'Updated content' })),
    delete: vi.fn(() => Promise.resolve()),
  },
  attachments: {
    list: vi.fn(() => Promise.resolve([
      { id: 1, filename: 'note.txt', file_size: 1024 },
    ])),
    upload: vi.fn(() => Promise.resolve({ id: 2, filename: 'note.txt' })),
    delete: vi.fn(() => Promise.resolve()),
    download: vi.fn(() => Promise.resolve(new Blob(['hello']))),
  },
  teams: {
    listMembers: vi.fn(() => Promise.resolve([
      { user_id: 1, role: 'admin', user: { email: 'admin@test.com' } },
      { user_id: 2, role: 'member', user: { email: 'member@test.com' } },
    ])),
  },
}))

vi.mock('../api', () => ({ api: mockApi }))

vi.mock('react-hot-toast', () => ({
  default: { success: vi.fn(), error: vi.fn() },
  success: vi.fn(),
  error: vi.fn(),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ teamId: '1', projectId: '1', taskId: '1' }),
  }
})

localStorage.setItem('access_token', 'test-token')

function renderWithProviders(ui) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>{ui}</AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('TaskDetail - Comment Editing and Deletion', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('access_token', 'test-token')
  })

  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('should render comments section', async () => {
    const TaskDetail = (await import('../pages/TaskDetail')).default
    renderWithProviders(<TaskDetail />)

    await waitFor(() => {
      expect(screen.getByText('Comments (2)')).toBeInTheDocument()
    })
  })

  it('should display comment authors and content', async () => {
    const TaskDetail = (await import('../pages/TaskDetail')).default
    renderWithProviders(<TaskDetail />)

    await waitFor(() => {
      expect(screen.getByText('user1@test.com')).toBeInTheDocument()
      expect(screen.getByText('First comment')).toBeInTheDocument()
    })
  })

  it('should show edit and delete buttons for author', async () => {
    const TaskDetail = (await import('../pages/TaskDetail')).default
    renderWithProviders(<TaskDetail />)

    await waitFor(() => {
      expect(screen.getByText('First comment')).toBeInTheDocument()
    }, { timeout: 3000 })

    const editButtons = await waitFor(() => 
      document.querySelectorAll('[title="Edit comment"]')
    )
    const deleteButtons = document.querySelectorAll('[title="Delete comment"]')

    expect(editButtons.length).toBeGreaterThan(0)
    expect(deleteButtons.length).toBeGreaterThan(0)
  })

  it('should handle edit button click', async () => {
    const user = userEvent.setup()
    const TaskDetail = (await import('../pages/TaskDetail')).default
    
    renderWithProviders(<TaskDetail />)

    await waitFor(() => {
      expect(screen.getByText('First comment')).toBeInTheDocument()
    }, { timeout: 3000 })

    const editButtons = document.querySelectorAll('[title="Edit comment"]')
    if (editButtons.length > 0) {
      await user.click(editButtons[0])
      
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Edit your comment...')).toBeInTheDocument()
      })
    }
  })

  it('should call update API when saving comment', async () => {
    const user = userEvent.setup()
    const TaskDetail = (await import('../pages/TaskDetail')).default
    
    renderWithProviders(<TaskDetail />)

    await waitFor(() => {
      expect(screen.getByText('First comment')).toBeInTheDocument()
    }, { timeout: 3000 })

    const editButtons = document.querySelectorAll('[title="Edit comment"]')
    if (editButtons.length > 0) {
      await user.click(editButtons[0])
      
      const textarea = await waitFor(() => 
        screen.getByPlaceholderText('Edit your comment...')
      )
      await user.clear(textarea)
      await user.type(textarea, 'Updated content')

      const saveButton = screen.getByText('Save')
      await user.click(saveButton)

      await waitFor(() => {
        expect(mockApi.comments.update).toHaveBeenCalled()
      })
    }
  })

  it('should call delete API when confirmed', async () => {
    const user = userEvent.setup()
    window.confirm = vi.fn(() => true)
    
    const TaskDetail = (await import('../pages/TaskDetail')).default
    
    renderWithProviders(<TaskDetail />)

    await waitFor(() => {
      expect(screen.getByText('First comment')).toBeInTheDocument()
    }, { timeout: 3000 })

    const deleteButtons = document.querySelectorAll('[title="Delete comment"]')
    if (deleteButtons.length > 0) {
      await user.click(deleteButtons[0])
      
      await waitFor(() => {
        expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to delete this comment?')
      })
    }
  })

  it('edits and saves the task', async () => {
    const user = userEvent.setup()
    mockApi.tasks.update = vi.fn(() => Promise.resolve({ id: 1, title: 'Updated task' }))
    const TaskDetail = (await import('../pages/TaskDetail')).default
    renderWithProviders(<TaskDetail />)

    await screen.findByText('Test Task')
    await user.click(screen.getByRole('button', { name: 'Edit task' }))
    const title = screen.getByLabelText('Title')
    await user.clear(title)
    await user.type(title, 'Updated task')
    await user.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() =>
      expect(mockApi.tasks.update).toHaveBeenCalledWith(
        'test-token',
        '1',
        '1',
        '1',
        expect.objectContaining({ title: 'Updated task' }),
      ),
    )
  })

  it('uploads an attachment', async () => {
    const user = userEvent.setup()
    const TaskDetail = (await import('../pages/TaskDetail')).default
    renderWithProviders(<TaskDetail />)

    await screen.findByText('Test Task')
    const file = new File(['hello'], 'note.txt', { type: 'text/plain' })
    await user.upload(screen.getByLabelText('Upload attachment'), file)

    await waitFor(() => expect(mockApi.attachments.upload).toHaveBeenCalled())
  })

  it('downloads and deletes an attachment', async () => {
    const user = userEvent.setup()
    window.URL.createObjectURL = vi.fn(() => 'blob:mock')
    window.URL.revokeObjectURL = vi.fn()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const TaskDetail = (await import('../pages/TaskDetail')).default
    renderWithProviders(<TaskDetail />)

    await screen.findByText('note.txt')

    await user.click(screen.getByRole('button', { name: 'Download note.txt' }))
    await waitFor(() =>
      expect(mockApi.attachments.download).toHaveBeenCalledWith(
        'test-token',
        '1',
        '1',
        '1',
        1,
      ),
    )

    await user.click(screen.getByRole('button', { name: 'Delete note.txt' }))
    await waitFor(() =>
      expect(mockApi.attachments.delete).toHaveBeenCalledWith(
        'test-token',
        '1',
        '1',
        '1',
        1,
      ),
    )
  })

  it('shows an error state when the task cannot be loaded', async () => {
    mockApi.tasks.get.mockRejectedValueOnce(new Error('not found'))
    const TaskDetail = (await import('../pages/TaskDetail')).default
    renderWithProviders(<TaskDetail />)

    expect(await screen.findByText('Could not load this task')).toBeInTheDocument()
  })
})