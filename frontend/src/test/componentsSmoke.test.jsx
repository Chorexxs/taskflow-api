import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import QueryError from '../components/QueryError'
import {
  ColumnSkeleton,
  CommentSkeleton,
  EmptyState,
  MemberSkeleton,
  ProjectSkeleton,
  TaskCardSkeleton,
  TeamSkeleton,
} from '../components/Skeleton'
import NotFound from '../pages/NotFound'

describe('shared UI states', () => {
  it('renders a retryable error', async () => {
    const onRetry = vi.fn()
    render(<QueryError title="Load failed" message="Try again later" onRetry={onRetry} />)

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(screen.getByText('Load failed')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('renders loading skeletons and an empty state', () => {
    render(
      <div>
        <TeamSkeleton />
        <ProjectSkeleton />
        <TaskCardSkeleton />
        <ColumnSkeleton />
        <MemberSkeleton />
        <CommentSkeleton />
        <EmptyState icon={null} title="Nothing here" description="Create something" />
      </div>,
    )

    expect(screen.getByText('Nothing here')).toBeInTheDocument()
    expect(screen.getByText('Create something')).toBeInTheDocument()
  })

  it('renders the 404 page with a way back', () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>,
    )

    expect(screen.getByText('404')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /go to dashboard/i })).toHaveAttribute('href', '/')
  })
})
