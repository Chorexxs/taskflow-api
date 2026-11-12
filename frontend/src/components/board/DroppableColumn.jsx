import { useDroppable } from '@dnd-kit/core'

/**
 * A single Kanban column that accepts dropped tasks (T-127).
 */
export default function DroppableColumn({ column, children, taskCount }) {
  const { setNodeRef } = useDroppable({ id: column.id })

  return (
    <div ref={setNodeRef} className="column-bg rounded-xl p-4 h-full min-h-[500px] border border-subtle">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-widest">
          {column.title}
        </h3>
        <span className="badge badge-accent text-[10px]">{taskCount}</span>
      </div>
      {children}
    </div>
  )
}
