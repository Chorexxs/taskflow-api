import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api'
import toast from 'react-hot-toast'
import { Plus, Users, FolderKanban, ChevronRight } from 'lucide-react'

export default function Dashboard() {
  const queryClient = useQueryClient()
  const [showCreateTeam, setShowCreateTeam] = useState(false)
  const [newTeam, setNewTeam] = useState({ name: '', slug: '', description: '' })

  const { data: teams, isLoading } = useQuery({
    queryKey: ['teams'],
    queryFn: () => api.teams.list(localStorage.getItem('access_token')),
  })

  const createTeamMutation = useMutation({
    mutationFn: (data) => api.teams.create(localStorage.getItem('access_token'), data),
    onSuccess: () => {
      queryClient.invalidateQueries(['teams'])
      setShowCreateTeam(false)
      setNewTeam({ name: '', slug: '', description: '' })
      toast.success('Team created!')
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to create team')
    },
  })

  const handleCreateTeam = (e) => {
    e.preventDefault()
    createTeamMutation.mutate(newTeam)
  }

  return (
    <>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h2 className="text-2xl font-medium text-[var(--color-text-primary)] mb-1">My Teams</h2>
          <p className="text-sm text-[var(--color-text-muted)]">Manage your projects and collaborators</p>
        </div>
        <button
          onClick={() => setShowCreateTeam(true)}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <Plus className="w-4 h-4" />
          New Team
        </button>
        </div>

        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-32 rounded-xl bg-[var(--color-bg-secondary)] skeleton"></div>
            ))}
          </div>
        ) : teams?.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-16 h-16 rounded-2xl bg-[var(--color-bg-tertiary)] flex items-center justify-center mb-4">
              <Users className="w-8 h-8 text-[var(--color-text-muted)]" />
            </div>
            <h3 className="text-lg font-medium text-[var(--color-text-primary)] mb-2">No teams yet</h3>
            <p className="text-sm text-[var(--color-text-muted)] mb-6 max-w-sm">
              Create your first team to start organizing projects and collaborating with your team.
            </p>
            <button
              onClick={() => setShowCreateTeam(true)}
              className="btn-primary text-sm"
            >
              Create Your First Team
            </button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {teams?.map((team, index) => (
              <Link
                key={team.id}
                to={`/teams/${team.slug}`}
                className={`card p-5 group fade-in stagger-${index + 1}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-xl bg-[var(--color-accent-muted)] flex items-center justify-center">
                    <span className="text-sm font-semibold text-[var(--color-accent)]">
                      {team.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <ChevronRight className="w-5 h-5 text-[var(--color-text-muted)] group-hover:text-[var(--color-accent)] group-hover:translate-x-1 transition-all" />
                </div>
                <h3 className="text-base font-medium text-[var(--color-text-primary)] mb-2">
                  {team.name}
                </h3>
                <p className="text-sm text-[var(--color-text-muted)] line-clamp-2 mb-4">
                  {team.description || 'No description'}
                </p>
                <div className="flex items-center text-xs text-[var(--color-text-secondary)]">
                  <FolderKanban className="w-4 h-4 mr-1.5" />
                  View projects
                </div>
              </Link>
            ))}
          </div>
        )}

      {showCreateTeam && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[var(--color-bg-secondary)] border border-subtle rounded-2xl p-6 w-full max-w-md shadow-elevated fade-in">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-medium text-[var(--color-text-primary)]">Create Team</h3>
              <button 
                onClick={() => setShowCreateTeam(false)}
                className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                <Plus className="w-5 h-5 rotate-45" />
              </button>
            </div>
            <form onSubmit={handleCreateTeam} className="space-y-4">
              <div className="space-y-2">
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Name</label>
                <input
                  type="text"
                  value={newTeam.name}
                  onChange={(e) => setNewTeam({ ...newTeam, name: e.target.value, slug: e.target.value.toLowerCase().replace(/\s+/g, '-') })}
                  required
                  className="input-field"
                  placeholder="My Awesome Team"
                />
              </div>
              <div className="space-y-2">
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Slug</label>
                <input
                  type="text"
                  value={newTeam.slug}
                  onChange={(e) => setNewTeam({ ...newTeam, slug: e.target.value })}
                  required
                  className="input-field"
                  placeholder="my-team"
                />
              </div>
              <div className="space-y-2">
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Description</label>
                <textarea
                  value={newTeam.description}
                  onChange={(e) => setNewTeam({ ...newTeam, description: e.target.value })}
                  className="input-field min-h-[80px] resize-none"
                  placeholder="Optional description..."
                />
              </div>
              <div className="flex gap-3 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateTeam(false)}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createTeamMutation.isPending}
                  className="btn-primary text-sm"
                >
                  {createTeamMutation.isPending ? 'Creating...' : 'Create Team'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}