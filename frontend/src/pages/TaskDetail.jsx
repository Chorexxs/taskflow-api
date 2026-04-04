import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import { api } from '../api'
import toast from 'react-hot-toast'
import { ArrowLeft, Send, Clock, MessageSquare, Paperclip, User } from 'lucide-react'

export default function TaskDetail() {
  const { teamId, projectId, taskId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const token = localStorage.getItem('access_token')
  const [newComment, setNewComment] = useState('')

  const { data: task, isLoading } = useQuery({
    queryKey: ['task', teamId, projectId, taskId],
    queryFn: () => api.tasks.get(token, teamId, projectId, taskId),
  })

  const { data: comments } = useQuery({
    queryKey: ['comments', teamId, projectId, taskId],
    queryFn: () => api.comments.list(token, teamId, projectId, taskId),
  })

  const addCommentMutation = useMutation({
    mutationFn: (content) => api.comments.create(token, teamId, projectId, taskId, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries(['comments', teamId, projectId, taskId])
      setNewComment('')
      toast.success('Comment added!')
    },
    onError: () => toast.error('Failed to add comment'),
  })

  const handleAddComment = (e) => {
    e.preventDefault()
    if (!newComment.trim()) return
    addCommentMutation.mutate(newComment)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const priorityColors = {
    high: 'text-red-600 bg-red-100 dark:bg-red-900',
    medium: 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900',
    low: 'text-gray-600 bg-gray-100 dark:bg-gray-700',
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16 gap-4">
            <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-700">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Task Details</h1>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">{task?.title}</h2>
              <div className="flex items-center gap-3">
                <span className={`px-3 py-1 text-sm rounded ${priorityColors[task?.priority]}`}>
                  {task?.priority}
                </span>
                <span className="px-3 py-1 text-sm rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                  {task?.status}
                </span>
              </div>
            </div>
          </div>

          {task?.description && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Description</h3>
              <p className="text-gray-900 dark:text-white">{task.description}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4 mb-6">
            <div>
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Assigned to</h3>
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-gray-400" />
                <span className="text-gray-900 dark:text-white">
                  {task?.assignee?.email || 'Unassigned'}
                </span>
              </div>
            </div>
            {task?.due_date && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Due date</h3>
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <span className="text-gray-900 dark:text-white">
                    {new Date(task.due_date).toLocaleDateString()}
                  </span>
                </div>
              </div>
            )}
          </div>

          <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <MessageSquare className="w-5 h-5" />
              Comments ({comments?.length || 0})
            </h3>

            <div className="space-y-4 mb-6">
              {comments?.map(comment => (
                <div key={comment.id} className="flex gap-3">
                  <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center text-sm font-medium text-blue-600 dark:text-blue-300 flex-shrink-0">
                    {comment.author_id?.[0]?.toUpperCase()}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        User {comment.author_id}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(comment.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-gray-700 dark:text-gray-300 mt-1">{comment.content}</p>
                  </div>
                </div>
              ))}
              {(!comments || comments.length === 0) && (
                <p className="text-gray-500 dark:text-gray-400">No comments yet</p>
              )}
            </div>

            <form onSubmit={handleAddComment} className="flex gap-3">
              <input
                type="text"
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                placeholder="Add a comment..."
                className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white"
              />
              <button
                type="submit"
                disabled={addCommentMutation.isPending || !newComment.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
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
