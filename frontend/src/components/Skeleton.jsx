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

export function ProjectSkeleton() {
  return (
    <div className="p-6 bg-white dark:bg-gray-800 rounded-lg shadow">
      <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/2 animate-pulse mb-2"></div>
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 animate-pulse mb-4"></div>
      <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-16 animate-pulse"></div>
    </div>
  )
}

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

export function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="text-center py-12">
      {Icon && <Icon className="w-12 h-12 mx-auto text-gray-400 mb-4" />}
      <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">{title}</h3>
      <p className="text-gray-500 dark:text-gray-400">{description}</p>
    </div>
  )
}
