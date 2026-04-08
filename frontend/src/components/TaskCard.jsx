/**
 * TaskFlow Frontend - Task Card Component
 * 
 * This component displays a task in a card format for the project board.
 * It supports drag-and-drop functionality and shows task details.
 * 
 * Features:
 * - Drag-and-drop with @dnd-kit
 * - Priority badge styling
 * - Due date display with overdue/today indicators
 * - Assignee display with avatar
 * - Click to view task details
 * - Visual states for dragging and overlay
 */

import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Calendar, User } from 'lucide-react';

/**
 * Task card component for displaying task summary in project board.
 * 
 * @param {Object} props - Component props
 * @param {Object} props.task - Task object with title, description, priority, due_date, assignee
 * @param {Function} props.onClick - Callback when card is clicked
 * @param {boolean} props.isOverlay - Whether this is a drag overlay (visual feedback during drag)
 * @returns {JSX.Element} Task card element
 * 
 * @example
 * <TaskCard 
 *   task={{
 *     id: 1,
 *     title: 'Fix bug',
 *     priority: 'high',
 *     due_date: '2024-01-15',
 *     assignee: { email: 'user@example.com' }
 *   }}
 *   onClick={() => navigate(`/tasks/${task.id}`)}
 * />
 */
export default function TaskCard({ task, onClick, isOverlay }) {
  // Setup sortable functionality
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id });

  // Calculate transform styles for drag positioning
  const style = {
    transform: CSS.Translate.toString(transform),
    transition: transition || 'transform 200ms ease',
    opacity: isDragging ? 0.3 : 1,
  };

  /**
   * Priority badge class mapping.
   * Maps priority values to CSS class names.
   */
  const priorityClasses = {
    high: 'badge badge-high',
    medium: 'badge badge-medium',
    low: 'badge badge-low',
  };

  // Check if task is overdue
  const isOverdue = task.due_date && new Date(task.due_date) < new Date();
  
  // Check if task is due today
  const isDueToday = task.due_date && new Date(task.due_date).toDateString() === new Date().toDateString();

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className={`card p-4 cursor-pointer ${isOverlay ? 'shadow-glow border-[var(--color-accent)]' : ''}`}
    >
      {/* Title and priority */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <h4 className="text-sm font-medium text-[var(--color-text-primary)] leading-snug">
          {task.title}
        </h4>
        <span className={priorityClasses[task.priority]}>
          {task.priority}
        </span>
      </div>
      
      {/* Description (truncated) */}
      {task.description && (
        <p className="text-xs text-[var(--color-text-muted)] mb-3 line-clamp-2 leading-relaxed">
          {task.description}
        </p>
      )}
      
      {/* Footer: due date and assignee */}
      <div className="flex items-center gap-4 text-[10px] text-[var(--color-text-muted)]">
        {/* Due date */}
        {task.due_date && (
          <div className={`flex items-center gap-1.5 ${isOverdue ? 'text-[var(--color-priority-high)]' : isDueToday ? 'text-[var(--color-priority-medium)]' : ''}`}>
            <Calendar className="w-3.5 h-3.5" />
            <span className="font-medium">
              {new Date(task.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </span>
          </div>
        )}
        
        {/* Assignee avatar */}
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
  );
}
