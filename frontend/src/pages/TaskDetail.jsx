/**
 * TaskDetail.jsx - Task Detail Page Component
 * 
 * Displays detailed information about a single task including title, description,
 * priority, status, assignee, due date, and comments.
 * Provides functionality for adding comments to tasks.
 * 
 * Features:
 * - View full task details (title, description, priority, status)
 * - Display assignee information with avatar
 * - Show due date with overdue highlighting
 * - View and add comments on the task
 * - Navigate back to previous page
 * 
 * @requires react-router-dom - For navigation and URL params
 * @requires @tanstack/react-query - For data fetching and mutations
 * @requires react-hot-toast - For notification toasts
 * @requires lucide-react - For icons
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import toast from 'react-hot-toast'
import { ArrowLeft, Send, MessageSquare, User, Calendar, Edit2, X, Check, Paperclip, Download, Trash2, File } from 'lucide-react'

/**
 * TaskDetail Component - Page for viewing and interacting with a single task
 * 
 * Fetches task details and comments from API.
 * Displays task information in a card layout with comment section.
 * 
 * @returns {JSX.Element} Rendered task detail page with comments
 * 
 * @state {string} teamId - Team ID from URL params
 * @state {string} projectId - Project ID from URL params  
 * @state {string} taskId - Task ID from URL params
 * @state {string} newComment - Comment text input
 * 
 * @queries
 * - task: Fetches full task details by IDs
 * - comments: Fetches all comments for the task
 * 
 * @mutations
 * - addCommentMutation: Creates a new comment on the task
 */

export default function TaskDetail() {
  const { teamId, projectId, taskId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const token = localStorage.getItem('access_token')
  const currentUserId = parseInt(localStorage.getItem('user_id') || '0')
  const [newComment, setNewComment] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState({
    title: '',
    description: '',
    priority: 'medium',
    status: 'todo',
    due_date: '',
  })

  const { data: task, isLoading } = useQuery({
    queryKey: ['task', teamId, projectId, taskId],
    queryFn: () => api.tasks.get(token, teamId, projectId, taskId),
  })

  const { data: comments } = useQuery({
    queryKey: ['comments', teamId, projectId, taskId],
    queryFn: () => api.comments.list(token, teamId, projectId, taskId),
  })

  const { data: attachments } = useQuery({
    queryKey: ['attachments', teamId, projectId, taskId],
    queryFn: () => api.attachments.list(token, teamId, projectId, taskId),
  })

  const uploadMutation = useMutation({
    mutationFn: (formData) => api.attachments.upload(token, teamId, projectId, taskId, formData),
    onSuccess: () => {
      queryClient.invalidateQueries(['attachments', teamId, projectId, taskId])
      toast.success('File uploaded!')
    },
    onError: () => toast.error('Failed to upload file'),
  })

  const deleteAttachmentMutation = useMutation({
    mutationFn: (attachmentId) => api.attachments.delete(token, teamId, projectId, taskId, attachmentId),
    onSuccess: () => {
      queryClient.invalidateQueries(['attachments', teamId, projectId, taskId])
      toast.success('File deleted!')
    },
    onError: () => toast.error('Failed to delete file'),
  })

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedFile(file)
      const formData = new FormData()
      formData.append('file', file)
      uploadMutation.mutate(formData)
      e.target.value = ''
    }
  }

  const handleDownload = async (attachment) => {
    try {
      const blob = await api.attachments.download(token, teamId, projectId, taskId, attachment.id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = attachment.filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      a.remove()
    } catch {
      toast.error('Failed to download file')
    }
  }

  const addCommentMutation = useMutation({
    mutationFn: (content) => api.comments.create(token, teamId, projectId, taskId, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries(['comments', teamId, projectId, taskId])
      setNewComment('')
      toast.success('Comment added!')
    },
    onError: () => toast.error('Failed to add comment'),
  })

  const updateTaskMutation = useMutation({
    mutationFn: (data) => api.tasks.update(token, teamId, projectId, taskId, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['task', teamId, projectId, taskId])
      setIsEditing(false)
      toast.success('Task updated!')
    },
    onError: (err) => toast.error(err.response?.data?.detail || 'Failed to update task'),
  })

  const canEdit = task?.created_by === currentUserId

  const handleStartEdit = () => {
    setEditForm({
      title: task?.title || '',
      description: task?.description || '',
      priority: task?.priority || 'medium',
      status: task?.status || 'todo',
      due_date: task?.due_date ? new Date(task.due_date).toISOString().slice(0, 16) : '',
    })
    setIsEditing(true)
  }

  const handleSaveEdit = () => {
    const data = {
      title: editForm.title,
      description: editForm.description || null,
      priority: editForm.priority,
      status: editForm.status,
      due_date: editForm.due_date ? new Date(editForm.due_date).toISOString() : null,
    }
    updateTaskMutation.mutate(data)
  }

  const handleCancelEdit = () => {
    setIsEditing(false)
  }

  const handleAddComment = (e) => {
    e.preventDefault()
    if (!newComment.trim()) return
    addCommentMutation.mutate(newComment)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  const priorityClasses = {
    high: 'badge badge-high',
    medium: 'badge badge-medium',
    low: 'badge badge-low',
  }

  const isOverdue = task?.due_date && new Date(task.due_date) < new Date()

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      <header className="border-b border-subtle bg-[var(--color-bg-secondary)]/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16 gap-4">
            <button 
              onClick={() => navigate(-1)} 
              className="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-all"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-lg font-medium text-[var(--color-text-primary)]">Task Details</h1>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="card p-6 md:p-8">
          {isEditing ? (
            <div className="space-y-4 mb-6">
              <div>
                <label className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider block mb-2">Title</label>
                <input
                  type="text"
                  value={editForm.title}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  className="input-field w-full"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider block mb-2">Description</label>
                <textarea
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  className="input-field w-full h-24 resize-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider block mb-2">Priority</label>
                  <select
                    value={editForm.priority}
                    onChange={(e) => setEditForm({ ...editForm, priority: e.target.value })}
                    className="input-field w-full"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider block mb-2">Status</label>
                  <select
                    value={editForm.status}
                    onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                    className="input-field w-full"
                  >
                    <option value="todo">To Do</option>
                    <option value="in_progress">In Progress</option>
                    <option value="done">Done</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider block mb-2">Due Date</label>
                <input
                  type="datetime-local"
                  value={editForm.due_date}
                  onChange={(e) => setEditForm({ ...editForm, due_date: e.target.value })}
                  className="input-field w-full"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleSaveEdit}
                  disabled={updateTaskMutation.isPending || !editForm.title.trim()}
                  className="btn-primary flex items-center gap-2"
                >
                  <Check className="w-4 h-4" />
                  Save
                </button>
                <button
                  onClick={handleCancelEdit}
                  className="btn-secondary flex items-center gap-2"
                >
                  <X className="w-4 h-4" />
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-start justify-between mb-6">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h2 className="text-2xl font-medium text-[var(--color-text-primary)]">{task?.title}</h2>
                  {canEdit && (
                    <button
                      onClick={handleStartEdit}
                      className="p-1.5 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-all"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  <span className={priorityClasses[task?.priority]}>
                    {task?.priority}
                  </span>
                  <span className="badge badge-accent">
                    {task?.status}
                  </span>
                </div>
              </div>
            </div>
          )}

          {!isEditing && task?.description && (
            <div className="mb-8">
              <h3 className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider mb-3">Description</h3>
              <p className="text-[var(--color-text-primary)] leading-relaxed whitespace-pre-wrap">{task.description}</p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 p-4 bg-[var(--color-bg-tertiary)] rounded-xl">
            <div>
              <h3 className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Assigned to</h3>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-[var(--color-accent-muted)] flex items-center justify-center">
                  <User className="w-4 h-4 text-[var(--color-accent)]" />
                </div>
                <span className="text-[var(--color-text-primary)]">
                  {task?.assignee?.email || 'Unassigned'}
                </span>
</div>
           </div>

          {task?.due_date && (
            <div>
              <h3 className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-2">Due date</h3>
              <div className="flex items-center gap-3">
                <Calendar className={`w-4 h-4 ${isOverdue ? 'text-[var(--color-priority-high)]' : 'text-[var(--color-text-muted)]'}`} />
                <span className={`${isOverdue ? 'text-[var(--color-priority-high)]' : 'text-[var(--color-text-primary)]'}`}>
                  {new Date(task.due_date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="">
          <h3 className="text-sm font-medium text-[var(--color-text-secondary)] uppercase tracking-wider mb-5 flex items-center gap-2">
            <Paperclip className="w-4 h-4" />
            Attachments ({attachments?.length || 0})
          </h3>

          <div className="mb-4">
            <label className="btn-secondary cursor-pointer inline-flex items-center gap-2">
              <Paperclip className="w-4 h-4" />
              Upload File
              <input
                type="file"
                className="hidden"
                onChange={handleFileSelect}
                disabled={uploadMutation.isPending}
              />
            </label>
            {uploadMutation.isPending && <span className="ml-3 text-sm text-[var(--color-text-muted)]">Uploading...</span>}
          </div>

          <div className="space-y-2">
            {attachments?.map(attachment => (
              <div key={attachment.id} className="flex items-center justify-between p-3 bg-[var(--color-bg-tertiary)] rounded-xl">
                <div className="flex items-center gap-3">
                  <File className="w-5 h-5 text-[var(--color-text-muted)]" />
                  <div>
                    <p className="text-sm text-[var(--color-text-primary)]">{attachment.filename}</p>
                    <p className="text-xs text-[var(--color-text-muted)]">
                      {(attachment.file_size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleDownload(attachment)}
                    className="p-2 rounded-lg hover:bg-[var(--color-bg-secondary)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-all"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => deleteAttachmentMutation.mutate(attachment.id)}
                    className="p-2 rounded-lg hover:bg-[var(--color-bg-secondary)] text-[var(--color-text-muted)] hover:text-[var(--color-priority-high)] transition-all"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
            {(!attachments || attachments.length === 0) && (
              <p className="text-sm text-[var(--color-text-muted)]">No attachments</p>
            )}
          </div>
        </div>

        <div className="">
          <h3 className="text-sm font-medium text-[var(--color-text-secondary)] uppercase tracking-wider mb-5 flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            Comments ({comments?.length || 0})
            </h3>

            <div className="space-y-4 mb-6">
              {comments?.map(comment => (
                <div key={comment.id} className="flex gap-4 p-4 bg-[var(--color-bg-tertiary)] rounded-xl">
                  <div className="w-9 h-9 rounded-full bg-[var(--color-accent-muted)] flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-semibold text-[var(--color-accent)]">
                      {comment.author?.email?.[0]?.toUpperCase() || '?'}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-[var(--color-text-primary)]">
                        {comment.author?.email || `User ${comment.author_id}`}
                      </span>
                      <span className="text-xs text-[var(--color-text-muted)]">
                        {new Date(comment.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-[var(--color-text-secondary)] leading-relaxed">{comment.content}</p>
                  </div>
                </div>
              ))}
              {(!comments || comments.length === 0) && (
                <div className="text-center py-8">
                  <MessageSquare className="w-8 h-8 text-[var(--color-text-muted)] mx-auto mb-2" />
                  <p className="text-sm text-[var(--color-text-muted)]">No comments yet</p>
                </div>
              )}
            </div>

            <form onSubmit={handleAddComment} className="flex gap-3">
              <input
                type="text"
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Add a comment..."
                className="input-field flex-1"
              />
              <button
                type="submit"
                disabled={addCommentMutation.isPending || !newComment.trim()}
                className="btn-primary px-4"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  )
}