import { useState, useEffect } from 'react'
import { useParams, useSearchParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { DndContext, closestCorners, DragOverlay } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { useAuth } from '../context/AuthContext'
import { api } from '../api'
import toast from 'react-hot-toast'
import { ArrowLeft, Plus, Calendar, User, AlertCircle, Clock, Search, Filter, Bell, X } from 'lucide-react'
import TaskCard from '../components/TaskCard'

const COLUMNS = [
  { id: 'todo', title: 'To Do', color: 'bg-gray-100 dark:bg-gray-700' },
  { id: 'in_progress', title: 'In Progress', color: 'bg-blue-100 dark:bg-blue-900' },
  { id: 'done', title: 'Done', color: 'bg-green-100 dark:bg-green-900' },
]

export default function ProjectBoard() {
  const { teamId, projectId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const token = localStorage.getItem('access_token')
  const [showCreateTask, setShowCreateTask] = useState(false)
  const [newTask, setNewTask] = useState({ title: '', description: '', priority: 'medium', assigned_to: null, due_date: null })
  const [showFilters, setShowFilters] = useState(false)
  const [search, setSearch] = useState('')

  const filters = {
    status: searchParams.get('status') || '',
    priority: searchParams.get('priority') || '',
    assigned_to: searchParams.get('assigned_to') || '',
  }

  const { data: tasks, isLoading } = useQuery({
    queryKey: ['tasks', teamId, projectId, filters],
    queryFn: () => api.tasks.list(token, teamId, projectId, filters),
  })

  const { data: teamMembers } = useQuery({
    queryKey: ['team-members', teamId],
    queryFn: () => api.teams.get(token, teamId).then(t => t.members || []),
  })

  const createTaskMutation = useMutation({
    mutationFn: (data) => api.tasks.create(token, teamId, projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['tasks', teamId, projectId])
      setShowCreateTask(false)
      setNewTask({ title: '', description: '', priority: 'medium', assigned_to: null, due_date: null })
      toast.success('Task created!')
    },
    onError: () => toast.error('Failed to create task'),
  })

  const updateTaskMutation = useMutation({
    mutationFn: ({ taskId, data }) => api.tasks.update(token, teamId, projectId, taskId, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['tasks', teamId, projectId])
      toast.success('Task updated!')
    },
    onError: () => toast.error('Failed to update task'),
  })

  const handleDragEnd = (event) => {
    const { active, over } = event
    if (!over) return

    const taskId = active.id
    const newStatus = over.id

    const task = tasks?.find(t => t.id === taskId || t.title === taskId)
    if (task && task.status !== newStatus) {
      updateTaskMutation.mutate({ taskId: task.id, data: { status: newStatus } })
    }
  }

  const handleCreateTask = (e) => {
    e.preventDefault()
    createTaskMutation.mutate(newTask)
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

  const clearFilters = () => {
    setSearchParams(new URLSearchParams())
  }

  const getTasksByStatus = (status) => {
    let filtered = tasks?.filter(t => t.status === status) || []
    if (search) {
      const s = search.toLowerCase()
      filtered = filtered.filter(t => 
        t.title.toLowerCase().includes(s) || 
        t.description?.toLowerCase().includes(s)
      )
    }
    return filtered
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16 gap-4">
            <button onClick={() => navigate(`/teams/${teamId}`)} className="text-gray-500 hover:text-gray-700">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Project Board</h1>
            
            <div className="flex-1 max-w-md mx-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search tasks..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white text-sm"
                />
              </div>
            </div>

            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`p-2 rounded-md ${showFilters ? 'bg-blue-100 text-blue-600' : 'text-gray-500 hover:bg-gray-100'}`}
            >
              <Filter className="w-5 h-5" />
            </button>
            
            <button
              onClick={() => setShowCreateTask(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              New Task
            </button>
          </div>
        </div>
      </header>

      {showFilters && (
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
          <div className="max-w-7xl mx-auto flex flex-wrap gap-4 items-center">
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white text-sm"
            >
              <option value="">All Status</option>
              <option value="todo">To Do</option>
              <option value="in_progress">In Progress</option>
              <option value="done">Done</option>
            </select>

            <select
              value={filters.priority}
              onChange={(e) => handleFilterChange('priority', e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white text-sm"
            >
              <option value="">All Priorities</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            <select
              value={filters.assigned_to}
              onChange={(e) => handleFilterChange('assigned_to', e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white text-sm"
            >
              <option value="">All Assignees</option>
              {teamMembers?.map(m => (
                <option key={m.user_id} value={m.user_id}>{m.user?.email}</option>
              ))}
            </select>

            <button
              onClick={clearFilters}
              className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
            >
              <X className="w-4 h-4" />
              Clear filters
            </button>
          </div>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {COLUMNS.map(col => (
              <div key={col.id} className="h-96 bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse"></div>
            ))}
          </div>
        ) : (
          <DndContext collisionDetectionAlgorithm={closestCorners} onDragEnd={handleDragEnd}>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {COLUMNS.map(column => (
                <div key={column.id} className={`rounded-lg p-4 ${column.color}`}>
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                    {column.title}
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      ({getTasksByStatus(column.id).length})
                    </span>
                  </h3>
                  <SortableContext 
                    items={getTasksByStatus(column.id).map(t => t.id)} 
                    strategy={verticalListSortingStrategy}
                  >
                    <div className="space-y-3">
                      {getTasksByStatus(column.id).map(task => (
                        <TaskCard key={task.id} task={task} />
                      ))}
                      {getTasksByStatus(column.id).length === 0 && (
                        <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                          No tasks
                        </p>
                      )}
                    </div>
                  </SortableContext>
                </div>
              ))}
            </div>
          </DndContext>
        )}
      </main>

      {showCreateTask && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">Create Task</h3>
            <form onSubmit={handleCreateTask} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Title</label>
                <input
                  type="text"
                  value={newTask.title}
                  onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                  required
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Description</label>
                <textarea
                  value={newTask.description}
                  onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Priority</label>
                  <select
                    value={newTask.priority}
                    onChange={(e) => setNewTask({ ...newTask, priority: e.target.value })}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Due Date</label>
                  <input
                    type="date"
                    value={newTask.due_date || ''}
                    onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value || null })}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Assign to</label>
                <select
                  value={newTask.assigned_to || ''}
                  onChange={(e) => setNewTask({ ...newTask, assigned_to: e.target.value ? parseInt(e.target.value) : null })}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
                >
                  <option value="">Unassigned</option>
                  {teamMembers?.map(m => (
                    <option key={m.user_id} value={m.user_id}>{m.user?.email}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3 justify-end">
                <button
                  type="button"
                  onClick={() => setShowCreateTask(false)}
                  className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createTaskMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {createTaskMutation.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
