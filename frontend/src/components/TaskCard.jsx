import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Calendar, User } from 'lucide-react'

export default function TaskCard({ task, onClick, isOverlay }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id })

  const style = {
    transform: CSS.Translate.toString(transform),
    transition: transition || 'transform 200ms ease',
    opacity: isDragging ? 0.3 : 1,
  }

  const priorityClasses = {
    high: 'badge badge-high',
    medium: 'badge badge-medium',
    low: 'badge badge-low',
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
      className={`card p-4 cursor-pointer ${isOverlay ? 'shadow-glow border-[var(--color-accent)]' : ''}`}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <h4 className="text-sm font-medium text-[var(--color-text-primary)] leading-snug">
          {task.title}
        </h4>
        <span className={priorityClasses[task.priority]}>
          {task.priority}
        </span>
      </div>
      
      {task.description && (
        <p className="text-xs text-[var(--color-text-muted)] mb-3 line-clamp-2 leading-relaxed">
          {task.description}
        </p>
      )}
      
      <div className="flex items-center gap-4 text-[10px] text-[var(--color-text-muted)]">
        {task.due_date && (
          <div className={`flex items-center gap-1.5 ${isOverdue ? 'text-[var(--color-priority-high)]' : isDueToday ? 'text-[var(--color-priority-medium)]' : ''}`}>
            <Calendar className="w-3.5 h-3.5" />
            <span className="font-medium">
              {new Date(task.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </span>
          </div>
        )}
        {task.assignee && (
          <div className="flex items-center gap-1.5">
            <div className="w-5 h-5 rounded-full bg-[var(--color-accent-muted)] flex items-center justify-center">
              <User className="w-3 h-3 text-[var(--color-accent)]" />
            </div>
            <span className="truncate max-w-[100px]">
              {task.assignee.email?.[0]?.toUpperCase()}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}