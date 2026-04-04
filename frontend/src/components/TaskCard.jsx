import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Calendar, User, AlertCircle } from 'lucide-react'

export default function TaskCard({ task, onClick }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: task.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const priorityColors = {
    high: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    low: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
  }

  const isOverdue = task.due_date && new Date(task.due_date) < new Date()
  const isDueToday = task.due_date && new Date(task.due_date).toDateString() === new Date().toDateString()

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between mb-2">
        <h4 className="text-sm font-medium text-gray-900 dark:text-white">{task.title}</h4>
        <span className={`px-2 py-0.5 text-xs rounded ${priorityColors[task.priority]}`}>
          {task.priority}
        </span>
      </div>
      
      {task.description && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 line-clamp-2">
          {task.description}
        </p>
      )}
      
      <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
        {task.due_date && (
          <div className={`flex items-center gap-1 ${isOverdue ? 'text-red-500' : isDueToday ? 'text-yellow-500' : ''}`}>
            <Calendar className="w-3 h-3" />
            {new Date(task.due_date).toLocaleDateString()}
          </div>
        )}
        {task.assignee && (
          <div className="flex items-center gap-1">
            <User className="w-3 h-3" />
            {task.assignee.email?.[0]?.toUpperCase()}
          </div>
        )}
      </div>
    </div>
  )
}
