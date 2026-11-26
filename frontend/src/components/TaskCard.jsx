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
 * - A single interactive control that opens the task detail (click or Enter)
 * - Separate edit affordance with an accessible name (T-133, T-134)
 * - Visual states for dragging and overlay
 */

import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Calendar, User, Edit2 } from 'lucide-react';

/**
 * Priority badge class mapping. Maps priority values to CSS class names.
 */
const priorityClasses = {
  high: 'badge badge-high',
  medium: 'badge badge-medium',
  low: 'badge badge-low',
};

/**
 * Visual content of a task card, without any interaction (T-134).
 *
 * Kept separate so the drag overlay renders the same markup without nesting
 * interactive elements.
 *
 * @param {Object} props - Component props
 * @param {Object} props.task - Task object with title, description, priority, due_date, assignee
 * @returns {JSX.Element} Card content
 */
function CardContent({ task }) {
  const isOverdue = task.due_date && new Date(task.due_date) < new Date();
  const isDueToday =
    task.due_date && new Date(task.due_date).toDateString() === new Date().toDateString();

  return (
    <>
      {/* Title and priority */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <h4 className="text-sm font-medium text-[var(--color-text-primary)] leading-snug flex-1">
          {task.title}
        </h4>
        <span className={priorityClasses[task.priority]}>{task.priority}</span>
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
          <div
            className={`flex items-center gap-1.5 ${
              isOverdue
                ? 'text-[var(--color-priority-high)]'
                : isDueToday
                  ? 'text-[var(--color-priority-medium)]'
                  : ''
            }`}
          >
            <Calendar className="w-3.5 h-3.5" />
            <span className="font-medium">
              {new Date(task.due_date).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
              })}
            </span>
          </div>
        )}

        {/* Assignee avatar */}
        {task.assignee && (
          <div className="flex items-center gap-1.5">
            <div className="w-5 h-5 rounded-full bg-[var(--color-accent-muted)] flex items-center justify-center">
              <User className="w-3 h-3 text-[var(--color-accent)]" />
            </div>
            <span className="truncate max-w-[100px]">{task.assignee.email?.[0]?.toUpperCase()}</span>
          </div>
        )}
      </div>
    </>
  );
}

/**
 * Task card component for displaying task summary in project board.
 *
 * The card is a single interactive control: clicking it (or pressing Enter
 * while focused) opens the task. The edit affordance lives next to that
 * control instead of inside it, so there are no nested interactive elements.
 *
 * @param {Object} props - Component props
 * @param {Object} props.task - Task object with title, description, priority, due_date, assignee, created_by
 * @param {Function} props.onOpen - Callback that opens the task detail
 * @param {Function} props.onEdit - Callback for the edit affordance
 * @param {boolean} props.isOverlay - Whether this is a drag overlay (non-interactive)
 * @param {number} props.currentUserId - Current logged in user ID
 * @returns {JSX.Element} Task card element
 */
export default function TaskCard({ task, onOpen, onEdit, isOverlay, currentUserId }) {
  const { listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: task.id });

  const style = {
    transform: CSS.Translate.toString(transform),
    transition: transition || 'transform 200ms ease',
    opacity: isDragging ? 0.3 : 1,
  };

  if (isOverlay) {
    return (
      <div className="card p-4 shadow-glow border-[var(--color-accent)]">
        <CardContent task={task} />
      </div>
    );
  }

  const canEdit = currentUserId === task.created_by && Boolean(onEdit);

  return (
    <div className="relative">
      <div
        ref={setNodeRef}
        style={style}
        {...listeners}
        className="card p-4 cursor-pointer"
      >
        <button
          type="button"
          onClick={() => onOpen?.(task)}
          className={`block w-full text-left rounded-lg focus-visible:outline-2 ${
            canEdit ? 'pr-6' : ''
          }`}
        >
          <CardContent task={task} />
        </button>
      </div>

      {canEdit && (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onEdit(task);
          }}
          aria-label={`Edit task: ${task.title}`}
          className="absolute bottom-2 right-2 p-1 rounded text-[var(--color-text-muted)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text-primary)] transition-all"
        >
          <Edit2 className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}
