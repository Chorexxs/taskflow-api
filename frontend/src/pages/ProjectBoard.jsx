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
import { useParams, useSearchParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { DndContext, closestCorners, DragOverlay, useDroppable, useSensor, useSensors, PointerSensor } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { useAuth } from '../context/AuthContext'
import { api } from '../api'
import toast from 'react-hot-toast'
import { ArrowLeft, Plus, Search, Filter, X, Activity, ChevronDown, Settings, Archive } from 'lucide-react'
import TaskCard from '../components/TaskCard'

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
 * DroppableColumn Component - A single column in the Kanban board
 * 
 * Wraps task cards in a droppable area that accepts dragged tasks.
 * Displays column title and task count.
 * 
 * @param {Object} props - Component props
 * @param {Object} props.column - Column configuration with id and title
 * @param {JSX.Element} props.children - Task cards to render in column
 * @param {number} props.taskCount - Number of tasks in column
 * @returns {JSX.Element} Rendered droppable column
 * 
 * @example
 * <DroppableColumn column={{ id: 'todo', title: 'To Do' }} taskCount={5}>
 *   {taskCards}
 * </DroppableColumn>
 */

function DroppableColumn({ column, children, taskCount }) {
  const { setNodeRef } = useDroppable({
    id: column.id,
  })
  
  return (
    <div ref={setNodeRef} className="column-bg rounded-xl p-4 h-full min-h-[500px] border border-subtle">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-widest">
          {column.title}
        </h3>
        <span className="badge badge-accent text-[10px]">
          {taskCount}
        </span>
      </div>
      {children}
    </div>
  )
}

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
  const token = localStorage.getItem('access_token')
  const currentUserId = parseInt(localStorage.getItem('user_id') || '0')
  const [showCreateTask, setShowCreateTask] = useState(false)
  const [newTask, setNewTask] = useState({ title: '', description: '', priority: 'medium', assigned_to: null, due_date: null })
  const [showFilters, setShowFilters] = useState(false)
  const [search, setSearch] = useState('')
  const [activeTask, setActiveTask] = useState(null)
  const [showActivityPanel, setShowActivityPanel] = useState(false)
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

  const { data: tasks, isLoading, error: tasksError } = useQuery({
    queryKey: ['tasks', teamId, projectId, filters],
    queryFn: () => api.tasks.list(token, teamId, projectId, filters),
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
    queryFn: () => api.teams.get(token, teamId).then(t => t.members || []),
    retry: false,
  })

  const { data: projectActivity } = useQuery({
    queryKey: ['project-activity', teamId, projectId],
    queryFn: () => api.projects.getActivity(token, teamId, projectId),
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
      queryClient.invalidateQueries(['project', teamId, projectId])
      setShowEditProject(false)
      toast.success('Project updated!')
    },
    onError: (error) => {
      toast.error(error.detail || 'Failed to update project')
    },
  })

  const archiveProjectMutation = useMutation({
    mutationFn: () => api.projects.archive(token, teamId, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries(['projects', teamId])
      toast.success('Project archived!')
      navigate(`/teams/${teamId}`)
    },
    onError: (error) => {
      toast.error(error.detail || 'Failed to archive project')
    },
  })

  const createTaskMutation = useMutation({
    mutationFn: async (data) => {
      const response = await api.tasks.create(token, teamId, projectId, data)
      if (response.detail) {
        throw new Error(response.detail)
      }
      return response
    },
    onSuccess: (newTask) => {
      setTaskColumns(prev => ({
        ...prev,
        todo: [...prev.todo, newTask]
      }))
      queryClient.invalidateQueries(['tasks', teamId, projectId])
      setShowCreateTask(false)
      setNewTask({ title: '', description: '', priority: 'medium', assigned_to: null, due_date: null })
      toast.success('Task created!')
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to create task')
    },
  })

  const updateTaskMutation = useMutation({
    mutationFn: ({ taskId, data }) => api.tasks.update(token, teamId, projectId, taskId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      toast.success('Task updated!')
    },
    onError: (error) => {
      toast.error('Failed to update task')
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
    
    if (!over) return

    const taskId = active.id
    let newStatus

    if (COLUMNS.some(col => col.id === over.id)) {
      newStatus = over.id
    } else {
      const taskList = [...taskColumns.todo, ...taskColumns.in_progress, ...taskColumns.done]
      const overTask = taskList.find(t => String(t.id) === String(over.id))
      
      if (overTask) {
        newStatus = overTask.status
      } else {
        newStatus = over?.dataset?.colId || null
      }
    }

    if (!newStatus) return

    const task = taskColumns.todo.find(t => String(t.id) === String(taskId))
      || taskColumns.in_progress.find(t => String(t.id) === String(taskId))
      || taskColumns.done.find(t => String(t.id) === String(taskId))
    
    if (!task) return
    
    if (task.status !== newStatus) {
      setTaskColumns(prev => {
        const newColumns = { ...prev }
        const oldStatus = task.status
        
        const taskIndex = newColumns[oldStatus].findIndex(t => String(t.id) === String(taskId))
        if (taskIndex > -1) {
          const [movedTask] = newColumns[oldStatus].splice(taskIndex, 1)
          movedTask.status = newStatus
          
          const priorityOrder = { high: 0, medium: 1, low: 2 }
          const targetTasks = newColumns[newStatus]
          const insertIndex = targetTasks.findIndex(t => 
            priorityOrder[movedTask.priority] < priorityOrder[t.priority]
          )
          
          if (insertIndex === -1) {
            newColumns[newStatus] = [...targetTasks, movedTask]
          } else {
            newColumns[newStatus] = [
              ...targetTasks.slice(0, insertIndex),
              movedTask,
              ...targetTasks.slice(insertIndex)
            ]
          }
        }
        
        return newColumns
      })
      
      updateTaskMutation.mutate({ taskId: task.id, data: { status: newStatus } })
    }
    
    setActiveTask(null)
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
  }

  /**
   * Clears all active filters by resetting URL search parameters
   * Removes status, priority, and assignee filters
   * 
   * @returns {void}
   */

  const clearFilters = () => {
    setSearchParams(new URLSearchParams())
  }

  /**
   * Gets tasks for a specific column with search filtering and priority sorting
   * Searches task title and description, sorts by priority (high > medium > low)
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
    return filtered.sort((a, b) => (priorityOrder[a.priority] ?? 1) - (priorityOrder[b.priority] ?? 1))
  }

  const getColumnTaskCount = (status) => getTasksByStatus(status).length

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      <header className="border-b border-subtle bg-[var(--color-bg-secondary)]/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16 gap-4">
            <button 
              onClick={() => navigate(`/teams/${teamId}`)} 
              className="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-all"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-medium text-[var(--color-text-primary)]">Project Board</h1>
              <span className="text-[var(--color-text-muted)]">/</span>
              <span className="text-[var(--color-text-secondary)]">{projectId}</span>
            </div>
            
            {tasksError && (
              <span className="text-[var(--color-priority-high)] text-sm">Error loading tasks</span>
            )}
            
            <div className="flex-1 max-w-md mx-4">
              <input
                type="text"
                placeholder="Search tasks..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="input-field w-full"
              />
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`p-2 rounded-lg transition-all ${showFilters ? 'bg-[var(--color-accent-muted)] text-[var(--color-accent)]' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'}`}
              >
                <Filter className="w-5 h-5" />
              </button>
              
              <button
                onClick={() => setShowCreateTask(true)}
                className="btn-primary flex items-center gap-2 text-sm"
              >
                <Plus className="w-4 h-4" />
                New Task
              </button>

              <button
                onClick={() => setShowActivityPanel(!showActivityPanel)}
                className={`p-2 rounded-lg transition-all ${showActivityPanel ? 'bg-[var(--color-accent-muted)] text-[var(--color-accent)]' : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'}`}
                title="Project Activity"
              >
                <Activity className="w-5 h-5" />
              </button>
              
              <button
                onClick={() => { setProjectForm({ name: project?.name || '', description: project?.description || '' }); setShowEditProject(true); }}
                className="p-2 rounded-lg text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] transition-all"
                title="Project Settings"
              >
                <Settings className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {showFilters && (
        <div className="border-b border-subtle bg-[var(--color-bg-secondary)]/30 px-4 py-3">
          <div className="max-w-7xl mx-auto flex flex-wrap gap-3 items-center">
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="input-field w-auto py-1.5 text-sm"
            >
              <option value="">All Status</option>
              <option value="todo">To Do</option>
              <option value="in_progress">In Progress</option>
              <option value="done">Done</option>
            </select>

            <select
              value={filters.priority}
              onChange={(e) => handleFilterChange('priority', e.target.value)}
              className="input-field w-auto py-1.5 text-sm"
            >
              <option value="">All Priorities</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            <select
              value={filters.assigned_to}
              onChange={(e) => handleFilterChange('assigned_to', e.target.value)}
              className="input-field w-auto py-1.5 text-sm"
            >
              <option value="">All Assignees</option>
              {teamMembers?.map(m => (
                <option key={m.user_id} value={m.user_id}>{m.user?.email}</option>
              ))}
            </select>

            <button
              onClick={clearFilters}
              className="text-sm text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] flex items-center gap-1 transition-colors"
            >
              <X className="w-4 h-4" />
              Clear
            </button>
          </div>
        </div>
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
      </main>

      {showCreateTask && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[var(--color-bg-secondary)] border border-subtle rounded-2xl p-6 w-full max-w-md shadow-elevated fade-in">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-medium text-[var(--color-text-primary)]">Create Task</h3>
              <button 
                onClick={() => setShowCreateTask(false)}
                className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateTask} className="space-y-4">
              <div className="space-y-2">
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Title</label>
                <input
                  type="text"
                  value={newTask.title}
                  onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                  required
                  className="input-field"
                  placeholder="Task title"
                />
              </div>
              <div className="space-y-2">
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Description</label>
                <textarea
                  value={newTask.description}
                  onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                  className="input-field min-h-[80px] resize-none"
                  placeholder="Optional description..."
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Priority</label>
                  <select
                    value={newTask.priority}
                    onChange={(e) => setNewTask({ ...newTask, priority: e.target.value })}
                    className="input-field"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Due Date</label>
                  <input
                    type="date"
                    value={newTask.due_date || ''}
                    onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value || null })}
                    className="input-field"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Assign to</label>
                <select
                  value={newTask.assigned_to || ''}
                  onChange={(e) => setNewTask({ ...newTask, assigned_to: e.target.value ? parseInt(e.target.value) : null })}
                  className="input-field"
                >
                  <option value="">Unassigned</option>
                  {teamMembers?.map(m => (
                    <option key={m.user_id} value={m.user_id}>{m.user?.email}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateTask(false)}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createTaskMutation.isPending}
                  className="btn-primary text-sm"
                >
                  {createTaskMutation.isPending ? 'Creating...' : 'Create Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
)}

      {showEditProject && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[var(--color-bg-secondary)] border border-subtle rounded-2xl p-6 w-full max-w-md shadow-elevated fade-in">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-medium text-[var(--color-text-primary)]">Project Settings</h3>
              <button 
                onClick={() => setShowEditProject(false)}
                className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form 
              onSubmit={(e) => { e.preventDefault(); updateProjectMutation.mutate(projectForm); }}
              className="space-y-4"
            >
              <div className="space-y-2">
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Project Name</label>
                <input
                  type="text"
                  value={projectForm.name}
                  onChange={(e) => setProjectForm({ ...projectForm, name: e.target.value })}
                  required
                  className="input-field"
                  placeholder="Project name"
                />
              </div>
              <div className="space-y-2">
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Description</label>
                <textarea
                  value={projectForm.description}
                  onChange={(e) => setProjectForm({ ...projectForm, description: e.target.value })}
                  className="input-field min-h-[80px] resize-none"
                  placeholder="Optional description..."
                />
              </div>
              <div className="flex gap-3 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setShowEditProject(false)}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateProjectMutation.isPending}
                  className="btn-primary text-sm"
                >
                  {updateProjectMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
            
            <div className="mt-6 pt-4 border-t border-subtle">
              <button
                onClick={() => { if (confirm('Are you sure you want to archive this project?')) { archiveProjectMutation.mutate(); }}}
                disabled={archiveProjectMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-[var(--color-priority-high)]/10 text-[var(--color-priority-high)] rounded-lg hover:bg-[var(--color-priority-high)]/20 transition-colors text-sm w-full justify-center"
              >
                <Archive className="w-4 h-4" />
                {archiveProjectMutation.isPending ? 'Archiving...' : 'Archive Project'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showActivityPanel && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-[var(--color-bg-secondary)] rounded-xl shadow-xl max-w-lg w-full max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-subtle">
              <h2 className="text-lg font-medium text-[var(--color-text-primary)]">Project Activity</h2>
              <button
                onClick={() => setShowActivityPanel(false)}
                className="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              {projectActivity && projectActivity.length > 0 ? (
                <div className="space-y-3">
                  {projectActivity.map(log => {
                    const actionLabel = log.action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
                    return (
                      <div key={log.id} className="p-3 bg-[var(--color-bg-tertiary)] rounded-lg text-sm">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-[var(--color-accent)]">{actionLabel}</span>
                          <span className="text-xs text-[var(--color-text-muted)]">
                            {new Date(log.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        {log.old_value && log.new_value && (
                          <div className="text-[var(--color-text-secondary)]">
                            <span className="line-through text-[var(--color-text-muted)] mr-1">{log.old_value}</span>
                            <span className="text-[var(--color-text-primary)]">→ {log.new_value}</span>
                          </div>
                        )}
                        {!log.old_value && log.new_value && log.action !== 'created' && (
                          <div className="text-[var(--color-text-secondary)]">
                            Set to: <span className="text-[var(--color-text-primary)]">{log.new_value}</span>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-[var(--color-text-muted)]">
                  <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No activity yet</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}