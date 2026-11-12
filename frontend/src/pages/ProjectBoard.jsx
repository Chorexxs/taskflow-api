/**
 * ProjectBoard.jsx - Project Board / Kanban Page Component
 * 
 * Displays a Kanban-style task board for a project with drag-and-drop functionality.
 * Supports filtering tasks by status, priority, and assignee.
 * Real-time task updates through optimistic UI updates.
 * 
 * Features:
 * - Kanban board with three columns: To Do, In Progress, Done
 * - Drag and drop tasks between columns (@dnd-kit)
 * - Filter tasks by status, priority, and assignee
 * - Search tasks by title or description
 * - Create new tasks with title, description, priority, due date, and assignee
 * - Real-time task status updates via drag and drop
 * - Optimistic UI updates for smooth user experience
 * 
 * @requires @dnd-kit/core - For drag and drop functionality
 * @requires @dnd-kit/sortable - For sortable list items
 * @requires react-hot-toast - For notification toasts
 * @requires lucide-react - For icons
 */

import { useState, useEffect } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { DndContext, closestCorners, DragOverlay, useSensor, useSensors, PointerSensor } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { useAuth } from '../context/auth-context'
import { api } from '../api'
import toast from 'react-hot-toast'
import { ArrowLeft, Plus, Filter, Activity, Settings } from 'lucide-react'
import { positionBetween, toPosition } from '../utils/kanban'
import TaskCard from '../components/TaskCard'
import DroppableColumn from '../components/board/DroppableColumn'
import FiltersPanel from '../components/board/FiltersPanel'
import CreateTaskDialog from '../components/board/CreateTaskDialog'
import ProjectSettingsDialog from '../components/board/ProjectSettingsDialog'
import ProjectActivityDialog from '../components/board/ProjectActivityDialog'

/**
 * Kanban board column definitions
 * Each column represents a task status with its display title
 * 
 * @constant {Array<Object>} COLUMNS
 * @property {string} id - Unique column identifier (used as status value)
 * @property {string} title - Display title shown in column header
 */

const COLUMNS = [
  { id: 'todo', title: 'To Do', color: '' },
  { id: 'in_progress', title: 'In Progress', color: '' },
  { id: 'done', title: 'Done', color: '' },
]

/**
 * ProjectBoard Component - Main Kanban board page for project task management
 * 
 * Displays a drag-and-drop Kanban board organized into three columns (To Do, In Progress, Done).
 * Fetches tasks from API and organizes them by status.
 * Provides filtering, searching, and task creation functionality.
 * 
 * Features:
 * - Three-column Kanban board layout
 * - Drag and drop task movement between columns
 * - Filter panel for status, priority, and assignee
 * - Search input for filtering tasks by title/description
 * - Create task modal with full form
 * - Optimistic UI updates for smooth drag operations
 * - Real-time task count badges per column
 * 
 * @returns {JSX.Element} Rendered Kanban board with tasks and modals
 * 
 * @state {string} teamId - Team ID from URL params
 * @state {string} projectId - Project ID from URL params
 * @state {Object} searchParams - URL search parameters for filters
 * @state {boolean} showCreateTask - Controls visibility of create task modal
 * @state {Object} newTask - Form state for new task creation
 * @state {boolean} showFilters - Controls visibility of filter panel
 * @state {string} search - Search query for filtering tasks
 * @state {Object|null} activeTask - Currently dragged task for overlay
 * @state {Object} taskColumns - Tasks organized by status columns
 * 
 * @queries
 * - tasks: Fetches all tasks for the project with filters
 * - teamMembers: Fetches team members for assignee dropdown
 * 
 * @mutations
 * - createTaskMutation: Creates a new task in the project
 * - updateTaskMutation: Updates task status/fields after drag
 * 
 * @example
 * // URL structure
 * /teams/:teamId/projects/:projectId
 */

export default function ProjectBoard() {
  const { teamId, projectId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user, accessToken } = useAuth()
  const token = accessToken
  const currentUserId = user?.id ?? 0
  const [showCreateTask, setShowCreateTask] = useState(false)
  const [newTask, setNewTask] = useState({ title: '', description: '', priority: 'medium', assigned_to: null, due_date: null })
  const [showFilters, setShowFilters] = useState(false)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [activeTask, setActiveTask] = useState(null)
  const [showActivityPanel, setShowActivityPanel] = useState(false)
  const [activityPageNumber, setActivityPageNumber] = useState(1)
  const [showEditProject, setShowEditProject] = useState(false)
  const [projectForm, setProjectForm] = useState({ name: '', description: '' })
  const [taskColumns, setTaskColumns] = useState({
    todo: [],
    in_progress: [],
    done: []
  })

  const filters = {
    status: searchParams.get('status') || '',
    priority: searchParams.get('priority') || '',
    assigned_to: searchParams.get('assigned_to') || '',
  }

  // Debounce the search so typing never triggers a request per keystroke.
  useEffect(() => {
    const timeout = setTimeout(() => {
      setSearch(searchInput.trim().toLowerCase())
      setPage(1)
    }, 300)
    return () => clearTimeout(timeout)
  }, [searchInput])

  const { data: tasks, isLoading, error: tasksError, refetch: refetchTasks } = useQuery({
    queryKey: ['tasks', teamId, projectId, filters, page],
    queryFn: () =>
      api.tasks.list(token, teamId, projectId, {
        ...filters,
        page,
        page_size: 50,
        sort_by: 'position',
        order: 'asc',
      }),
    retry: false,
  })

  useEffect(() => {
    if (tasks?.items) {
      setTaskColumns({
        todo: tasks.items.filter(t => t.status === 'todo'),
        in_progress: tasks.items.filter(t => t.status === 'in_progress'),
        done: tasks.items.filter(t => t.status === 'done')
      })
    }
  }, [tasks])

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  )

  const { data: teamMembers } = useQuery({
    queryKey: ['team-members', teamId],
    queryFn: () => api.teams.listMembers(token, teamId),
    retry: false,
  })
  const currentMember = teamMembers?.find(m => m.user_id === currentUserId)
  const isAdmin = currentMember?.role === 'admin'

  const { data: projectActivity } = useQuery({
    queryKey: ['project-activity', teamId, projectId, activityPageNumber],
    queryFn: () =>
      api.projects.getActivity(token, teamId, projectId, {
        page: activityPageNumber,
        page_size: 10,
      }),
    enabled: showActivityPanel,
  })

  const { data: project } = useQuery({
    queryKey: ['project', teamId, projectId],
    queryFn: () => api.projects.get(token, teamId, projectId),
    retry: false,
  })

  const updateProjectMutation = useMutation({
    mutationFn: (data) => api.projects.update(token, teamId, projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', teamId, projectId] })
      setShowEditProject(false)
      toast.success('Project updated!')
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to update project')
    },
  })

  const archiveProjectMutation = useMutation({
    mutationFn: () => api.projects.archive(token, teamId, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects', teamId] })
      toast.success('Project archived!')
      navigate(`/teams/${teamId}`)
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to archive project')
    },
  })

  const createTaskMutation = useMutation({
    mutationFn: (data) => api.tasks.create(token, teamId, projectId, data),
    onSuccess: (newTask) => {
      setTaskColumns(prev => ({
        ...prev,
        todo: [...prev.todo, newTask]
      }))
      queryClient.invalidateQueries({ queryKey: ['tasks', teamId, projectId] })
      setShowCreateTask(false)
      setNewTask({ title: '', description: '', priority: 'medium', assigned_to: null, due_date: null })
      toast.success('Task created!')
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to create task')
    },
  })

  const updateTaskMutation = useMutation({
    mutationFn: ({ taskId, status, position }) =>
      api.tasks.updateStatus(token, teamId, projectId, taskId, status, position),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      toast.success('Task updated!')
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to update task')
    },
  })

  const handleDragStart = (event) => {
    const { active } = event
    const taskList = [...taskColumns.todo, ...taskColumns.in_progress, ...taskColumns.done]
    const task = taskList.find(t => String(t.id) === String(active.id))
    if (task) {
      setActiveTask(task)
    }
  }

  const handleDragEnd = (event) => {
    const { active, over } = event
    setActiveTask(null)

    if (!over || String(over.id) === String(active.id)) return

    const taskId = active.id
    const taskList = [...taskColumns.todo, ...taskColumns.in_progress, ...taskColumns.done]
    const task = taskList.find(t => String(t.id) === String(taskId))
    if (!task) return

    const overTask = taskList.find(t => String(t.id) === String(over.id))
    const newStatus = COLUMNS.some(col => col.id === over.id)
      ? over.id
      : overTask?.status || over?.data?.current?.status || null

    if (!newStatus) return

    const sourceStatus = task.status
    // Remove the dragged card from its current column before computing the
    // drop slot, so same-column moves do not count it twice.
    const sourceRemaining = taskColumns[sourceStatus].filter(
      t => String(t.id) !== String(taskId)
    )
    const targetRemaining = sourceStatus === newStatus
      ? sourceRemaining
      : taskColumns[newStatus].filter(t => String(t.id) !== String(taskId))

    let insertIndex = targetRemaining.length
    if (overTask) {
      const overIndex = targetRemaining.findIndex(t => String(t.id) === String(over.id))
      if (overIndex > -1) insertIndex = overIndex
    }

    const previous = insertIndex > 0 ? targetRemaining[insertIndex - 1].position : null
    const next = insertIndex < targetRemaining.length
      ? targetRemaining[insertIndex].position
      : null
    const position = positionBetween(previous, next)

    const movedTask = { ...task, status: newStatus, position }
    const newColumns = {
      ...taskColumns,
      [newStatus]: [
        ...targetRemaining.slice(0, insertIndex),
        movedTask,
        ...targetRemaining.slice(insertIndex),
      ],
    }
    if (sourceStatus !== newStatus) {
      newColumns[sourceStatus] = sourceRemaining
    }
    setTaskColumns(newColumns)

    const statusChanged = sourceStatus !== newStatus
    const positionChanged = Math.abs(toPosition(task.position) - position) > 1e-9
    if (statusChanged || positionChanged) {
      updateTaskMutation.mutate({ taskId: task.id, status: newStatus, position })
    }
  }

  const handleCreateTask = (e) => {
    e.preventDefault()
    createTaskMutation.mutate(newTask)
  }

  const handleEditTask = (task) => {
    navigate(`/teams/${teamId}/projects/${projectId}/tasks/${task.id}`)
  }

  const handleFilterChange = (key, value) => {
    const newParams = new URLSearchParams(searchParams)
    if (value) {
      newParams.set(key, value)
    } else {
      newParams.delete(key)
    }
    setSearchParams(newParams)
    setPage(1)
  }

  /**
   * Clears all active filters by resetting URL search parameters
   * Removes status, priority, and assignee filters
   * 
   * @returns {void}
   */

  const clearFilters = () => {
    setSearchParams(new URLSearchParams())
    setPage(1)
  }

  /**
   * Gets tasks for a specific column with search filtering and stable ordering.
   * The API returns tasks sorted by `position`; priority is only a tiebreaker
   * for legacy rows that still share position 0.
   *
   * @param {string} status - Column status to get tasks for (todo/in_progress/done)
   * @returns {Array<Object>} Filtered and sorted tasks for the column
   */

  const getTasksByStatus = (status) => {
    const taskList = taskColumns[status] || []
    if (!Array.isArray(taskList)) return []
    let filtered = taskList
    if (search) {
      const s = search.toLowerCase()
      filtered = filtered.filter(t => 
        t.title.toLowerCase().includes(s) || 
        t.description?.toLowerCase().includes(s)
      )
    }
    const priorityOrder = { high: 0, medium: 1, low: 2 }
    return [...filtered].sort((a, b) => {
      const byPosition = toPosition(a.position) - toPosition(b.position)
      if (byPosition !== 0) return byPosition
      return (priorityOrder[a.priority] ?? 1) - (priorityOrder[b.priority] ?? 1)
    })
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      <header className="border-b border-subtle bg-[var(--color-bg-secondary)]/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center min-h-16 gap-3 py-2">
            <button 
              onClick={() => navigate(`/teams/${teamId}`)} 
              className="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-all"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2 min-w-0">
              <h1 className="text-lg font-medium text-[var(--color-text-primary)]">Project Board</h1>
              <span className="text-[var(--color-text-muted)]">/</span>
              <span className="text-[var(--color-text-secondary)] truncate max-w-[12rem]">{projectId}</span>
            </div>
            
            {tasksError && (
              <span className="flex items-center gap-2 text-[var(--color-priority-high)] text-sm">
                Error loading tasks
                <button
                  type="button"
                  onClick={() => refetchTasks()}
                  className="underline hover:no-underline"
                >
                  Retry
                </button>
              </span>
            )}
            
            <div className="order-last w-full sm:order-none sm:flex-1 sm:max-w-md sm:mx-4">
              <input
                type="text"
                id="task-search"
                name="task-search"
                placeholder="Search tasks..."
                aria-label="Search tasks"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="input-field w-full"
              />
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`p-2 rounded-lg transition-all ${showFilters ? 'bg-[var(--color-accent-muted)] text-[var(--color-accent)]' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'}`}
                aria-label="Toggle filters"
                aria-expanded={showFilters}
              >
                <Filter className="w-5 h-5" />
              </button>
              
              <button
                onClick={() => setShowCreateTask(true)}
                className="btn-primary flex items-center gap-2 text-sm"
              >
                <Plus className="w-4 h-4" />
                <span className="hidden sm:inline">New Task</span>
              </button>

              <button
                onClick={() => setShowActivityPanel(!showActivityPanel)}
                className={`p-2 rounded-lg transition-all ${showActivityPanel ? 'bg-[var(--color-accent-muted)] text-[var(--color-accent)]' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'}`}
                title="Project Activity"
                aria-label="Project activity"
                aria-expanded={showActivityPanel}
              >
                <Activity className="w-5 h-5" />
              </button>
              
              {isAdmin && (
                <button
                  onClick={() => { setProjectForm({ name: project?.name || '', description: project?.description || '' }); setShowEditProject(true); }}
                  className="p-2 rounded-lg text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-all"
                  title="Project Settings"
                  aria-label="Project settings"
                >
                  <Settings className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {showFilters && (
        <FiltersPanel
          filters={filters}
          teamMembers={teamMembers}
          onChange={handleFilterChange}
          onClear={clearFilters}
        />
      )}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {COLUMNS.map(col => (
              <div key={col.id} className="h-[500px] rounded-xl bg-[var(--color-bg-secondary)] skeleton"></div>
            ))}
          </div>
        ) : (
          <DndContext 
            sensors={sensors}
            collisionDetectionAlgorithm={closestCorners} 
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {COLUMNS.map(column => (
                <DroppableColumn 
                  key={column.id} 
                  column={column}
                  taskCount={getTasksByStatus(column.id).length}
                >
                  <SortableContext 
                    items={getTasksByStatus(column.id).map(t => t.id)} 
                    strategy={verticalListSortingStrategy}
                  >
                    <div className="space-y-3">
                      {getTasksByStatus(column.id).map(task => (
                        <div key={task.id} className="task-card-transition">
                          <TaskCard task={task} onEdit={handleEditTask} currentUserId={currentUserId} />
                        </div>
                      ))}
                      {getTasksByStatus(column.id).length === 0 && (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                          <div className="w-12 h-12 rounded-full bg-[var(--color-bg-tertiary)] flex items-center justify-center mb-3">
                            <Plus className="w-5 h-5 text-[var(--color-text-muted)]" />
                          </div>
                          <p className="text-sm text-[var(--color-text-muted)]">
                            No tasks
                          </p>
                        </div>
                      )}
                    </div>
                  </SortableContext>
                </DroppableColumn>
              ))}
            </div>
            <DragOverlay>
              {activeTask ? <TaskCard task={activeTask} isOverlay /> : null}
            </DragOverlay>
          </DndContext>
        )}
        {tasks?.pages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-subtle">
            <button
              onClick={() => setPage(current => Math.max(1, current - 1))}
              disabled={page <= 1}
              className="text-sm text-[var(--color-accent)] disabled:text-[var(--color-text-muted)] disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-xs text-[var(--color-text-muted)]">
              Page {tasks.page} of {tasks.pages} · {tasks.total} tasks
            </span>
            <button
              onClick={() => setPage(current => Math.min(tasks.pages, current + 1))}
              disabled={!tasks.has_next}
              className="text-sm text-[var(--color-accent)] disabled:text-[var(--color-text-muted)] disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}
      </main>

      {showCreateTask && (
        <CreateTaskDialog
          form={newTask}
          onChange={setNewTask}
          onSubmit={handleCreateTask}
          teamMembers={teamMembers}
          isPending={createTaskMutation.isPending}
          onClose={() => setShowCreateTask(false)}
        />
      )}

      {showEditProject && (
        <ProjectSettingsDialog
          form={projectForm}
          onChange={setProjectForm}
          onSubmit={(event) => {
            event.preventDefault()
            updateProjectMutation.mutate(projectForm)
          }}
          onArchive={() => {
            if (confirm('Are you sure you want to archive this project?')) {
              archiveProjectMutation.mutate()
            }
          }}
          isSaving={updateProjectMutation.isPending}
          isArchiving={archiveProjectMutation.isPending}
          onClose={() => setShowEditProject(false)}
        />
      )}

      {showActivityPanel && (
        <ProjectActivityDialog
          activity={projectActivity}
          page={activityPageNumber}
          onPrevious={() => setActivityPageNumber((page) => Math.max(1, page - 1))}
          onNext={() => setActivityPageNumber((page) => Math.min(projectActivity.pages, page + 1))}
          onClose={() => setShowActivityPanel(false)}
        />
      )}
    </div>
  )
}