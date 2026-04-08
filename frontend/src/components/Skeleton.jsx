/**
 * Skeleton.jsx - Loading Skeleton Components
 *
 * Provides placeholder loading states for various UI elements.
 * Used during data fetching to show loading animations.
 * Each skeleton mimics the shape and layout of the actual content.
 *
 * Features:
 * - TeamSkeleton for team cards
 * - ProjectSkeleton for project cards
 * - TaskCardSkeleton for task cards
 * - ColumnSkeleton for Kanban columns
 * - MemberSkeleton for team member lists
 * - CommentSkeleton for comment sections
 * - EmptyState for zero-data displays
 *
 * @requires lucide-react - For icons in EmptyState
 */

/**
 * TeamSkeleton - Loading placeholder for team cards
 *
 * Displays a pulsing skeleton that mimics the team card layout.
 * Shows placeholder for team name, description, and member count.
 *
 * @returns {JSX.Element} Rendered team skeleton placeholder
 */
export function TeamSkeleton() {
  return (
    <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 animate-pulse mb-2"></div>
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3 animate-pulse mb-4"></div>
      <div className="flex items-center text-sm text-gray-500">
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20 animate-pulse"></div>
      </div>
    </div>
  )
}

/**
 * ProjectSkeleton - Loading placeholder for project cards
 *
 * Displays a pulsing skeleton that mimics the project card layout.
 * Shows placeholder for project name, description, and status.
 *
 * @returns {JSX.Element} Rendered project skeleton placeholder
 */
export function ProjectSkeleton() {
  return (
    <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/2 animate-pulse mb-2"></div>
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 animate-pulse mb-4"></div>
      <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-16 animate-pulse"></div>
    </div>
  )
}

/**
 * TaskCardSkeleton - Loading placeholder for task cards
 *
 * Displays a pulsing skeleton that mimics the task card layout.
 * Shows placeholder for title, description, and metadata.
 *
 * @returns {JSX.Element} Rendered task card skeleton placeholder
 */
export function TaskCardSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-start justify-between mb-2">
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3 animate-pulse"></div>
        <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-12 animate-pulse"></div>
      </div>
      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full animate-pulse mb-3"></div>
      <div className="flex items-center gap-3">
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-20 animate-pulse"></div>
      </div>
    </div>
  )
}

/**
 * ColumnSkeleton - Loading placeholder for Kanban columns
 *
 * Displays a pulsing skeleton that mimics a column layout.
 * Shows placeholder for column header and sample task cards.
 *
 * @returns {JSX.Element} Rendered column skeleton placeholder
 */
export function ColumnSkeleton() {
  return (
    <div className="rounded-lg p-4 bg-gray-100 dark:bg-gray-700">
      <div className="h-6 bg-gray-200 dark:bg-gray-600 rounded w-24 animate-pulse mb-4"></div>
      <div className="space-y-3">
        <TaskCardSkeleton />
        <TaskCardSkeleton />
      </div>
    </div>
  )
}

/**
 * MemberSkeleton - Loading placeholder for team member items
 *
 * Displays a pulsing skeleton that mimics the member item layout.
 * Shows placeholder for avatar and name.
 *
 * @returns {JSX.Element} Rendered member skeleton placeholder
 */
export function MemberSkeleton() {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse"></div>
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-32 animate-pulse"></div>
      </div>
    </div>
  )
}

/**
 * CommentSkeleton - Loading placeholder for comment items
 *
 * Displays a pulsing skeleton that mimics the comment layout.
 * Shows placeholder for avatar, author, timestamp, and content.
 *
 * @returns {JSX.Element} Rendered comment skeleton placeholder
 */
export function CommentSkeleton() {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse flex-shrink-0"></div>
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-24 animate-pulse"></div>
          <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-16 animate-pulse"></div>
        </div>
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full animate-pulse"></div>
      </div>
    </div>
  )
}

/**
 * EmptyState - Component for displaying empty/zero-data states
 * 
 * Displayed when lists have no data to show.
 * Accepts icon, title, and description for custom messaging.
 * 
 * @param {Object} props - Component props
 * @param {React.ComponentType} props.icon - Optional icon component to display
 * @param {string} props.title - Title text for empty state
 * @param {string} props.description - Description text for empty state
 * @returns {JSX.Element} Rendered empty state component
 * 
 * @example
 * <EmptyState 
 *   icon={FolderOpen} 
 *   title="No projects yet" 
 *   description="Create your first project to get started" 
 * />
 */

export function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="text-center py-12">
      {Icon && <Icon className="w-12 h-12 mx-auto text-gray-400 mb-4" />}
      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">{title}</h3>
      <p className="text-gray-500 dark:text-gray-400">{description}</p>
    </div>
  )
}
