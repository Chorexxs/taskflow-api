import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import { api } from '../api'
import toast from 'react-hot-toast'
import { ArrowLeft, Plus, Users, Crown, X, FolderOpen, ChevronRight } from 'lucide-react'

export default function TeamDetail() {
  const { teamId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showInvite, setShowInvite] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')
  const [showCreateProject, setShowCreateProject] = useState(false)
  const [newProject, setNewProject] = useState({ name: '', description: '' })

  const token = localStorage.getItem('access_token')

  const { data: team, isLoading: teamLoading } = useQuery({
    queryKey: ['team', teamId],
    queryFn: () => api.teams.get(token, teamId),
  })

  const { data: projects, isLoading: projectsLoading } = useQuery({
    queryKey: ['projects', teamId],
    queryFn: () => api.projects.list(token, teamId),
  })

  const { data: members } = useQuery({
    queryKey: ['team-members', teamId],
    queryFn: () => api.teams.listMembers(token, teamId),
    refetchOnMount: true,
    staleTime: 0,
  })

  const inviteMutation = useMutation({
    mutationFn: ({ email, role }) => api.teams.addMember(token, teamId, email, role),
    onSuccess: () => {
      queryClient.invalidateQueries(['team', teamId])
      queryClient.invalidateQueries(['team-members', teamId])
      setShowInvite(false)
      setInviteEmail('')
      toast.success('Invitation sent!')
    },
    onError: () => toast.error('Failed to invite member'),
  })

  const createProjectMutation = useMutation({
    mutationFn: (data) => api.projects.create(token, teamId, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['projects', teamId])
      setShowCreateProject(false)
      setNewProject({ name: '', description: '' })
      toast.success('Project created!')
    },
    onError: () => toast.error('Failed to create project'),
  })

  const handleInvite = (e) => {
    e.preventDefault()
    inviteMutation.mutate({ email: inviteEmail, role: inviteRole })
  }

  const handleCreateProject = (e) => {
    e.preventDefault()
    createProjectMutation.mutate(newProject)
  }

  if (teamLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      <header className="border-b border-subtle bg-[var(--color-bg-secondary)]/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16 gap-4">
            <button 
              onClick={() => navigate('/')} 
              className="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-all"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-[var(--color-accent)] flex items-center justify-center">
                <span className="text-sm font-bold text-[var(--color-bg-primary)]">
                  {team?.name?.charAt(0).toUpperCase()}
                </span>
              </div>
              <h1 className="text-xl font-medium text-[var(--color-text-primary)]">{team?.name}</h1>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-xl font-medium text-[var(--color-text-primary)] mb-1">Projects</h2>
                <p className="text-sm text-[var(--color-text-muted)]">{projects?.length || 0} projects</p>
              </div>
              <button
                onClick={() => setShowCreateProject(true)}
                className="btn-primary flex items-center gap-2 text-sm"
              >
                <Plus className="w-4 h-4" />
                New Project
              </button>
            </div>

            {projectsLoading ? (
              <div className="grid gap-4 md:grid-cols-2">
                {[1, 2].map(i => (
                  <div key={i} className="h-32 rounded-xl bg-[var(--color-bg-secondary)] skeleton"></div>
                ))}
              </div>
            ) : projects?.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center card p-8">
                <div className="w-14 h-14 rounded-2xl bg-[var(--color-bg-tertiary)] flex items-center justify-center mb-4">
                  <FolderOpen className="w-7 h-7 text-[var(--color-text-muted)]" />
                </div>
                <h3 className="text-base font-medium text-[var(--color-text-primary)] mb-2">No projects yet</h3>
                <p className="text-sm text-[var(--color-text-muted)] mb-6">Create your first project to start organizing tasks.</p>
                <button
                  onClick={() => setShowCreateProject(true)}
                  className="btn-primary text-sm"
                >
                  Create Project
                </button>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {projects?.map((project, index) => (
                  <Link
                    key={project.id}
                    to={`/teams/${teamId}/projects/${project.id}`}
                    className={`card p-5 group fade-in stagger-${index + 1}`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--color-accent)] to-emerald-400 flex items-center justify-center">
                        <FolderOpen className="w-5 h-5 text-[var(--color-bg-primary)]" />
                      </div>
                      <ChevronRight className="w-5 h-5 text-[var(--color-text-muted)] group-hover:text-[var(--color-accent)] group-hover:translate-x-1 transition-all" />
                    </div>
                    <h3 className="text-base font-medium text-[var(--color-text-primary)] mb-2">
                      {project.name}
                    </h3>
                    <p className="text-sm text-[var(--color-text-muted)] line-clamp-2 mb-4">
                      {project.description || 'No description'}
                    </p>
                    <span className={`badge ${project.status === 'active' ? 'badge-accent' : 'badge-low'}`}>
                      {project.status}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div>
            <div className="card p-5">
              <div className="flex justify-between items-center mb-5">
                <h3 className="text-sm font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Members</h3>
                <button
                  onClick={() => setShowInvite(true)}
                  className="text-xs text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] font-medium transition-colors"
                >
                  + Invite
                </button>
              </div>
              <div className="space-y-3">
                {members?.map(member => (
                  <div key={member.user_id} className="flex items-center justify-between p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] transition-colors">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-[var(--color-accent-muted)] flex items-center justify-center">
                        <span className="text-xs font-semibold text-[var(--color-accent)]">
                          {member.user?.email?.[0]?.toUpperCase()}
                        </span>
                      </div>
                      <span className="text-sm text-[var(--color-text-primary)]">{member.user?.email}</span>
                    </div>
                    {member.role === 'admin' && (
                      <Crown className="w-4 h-4 text-[var(--color-priority-medium)]" />
                    )}
                  </div>
                ))}
                {(!members || members.length === 0) && (
                  <p className="text-sm text-[var(--color-text-muted)] text-center py-4">No members yet</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      {showInvite && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[var(--color-bg-secondary)] border border-subtle rounded-2xl p-6 w-full max-w-md shadow-elevated fade-in">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-medium text-[var(--color-text-primary)]">Invite Member</h3>
              <button 
                onClick={() => setShowInvite(false)}
                className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleInvite} className="space-y-4">
              <div className="space-y-2">
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Email</label>
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  required
                  className="input-field"
                  placeholder="colleague@example.com"
                />
              </div>
              <div className="space-y-2">
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Role</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                  className="input-field"
                >
                  <option value="member">Member</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex gap-3 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setShowInvite(false)}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={inviteMutation.isPending}
                  className="btn-primary text-sm"
                >
                  {inviteMutation.isPending ? 'Sending...' : 'Send Invite'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showCreateProject && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[var(--color-bg-secondary)] border border-subtle rounded-2xl p-6 w-full max-w-md shadow-elevated fade-in">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-medium text-[var(--color-text-primary)]">Create Project</h3>
              <button 
                onClick={() => setShowCreateProject(false)}
                className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div className="space-y-2">
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Name</label>
                <input
                  type="text"
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  required
                  className="input-field"
                  placeholder="My Project"
                />
              </div>
              <div className="space-y-2">
                <label className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Description</label>
                <textarea
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  className="input-field min-h-[80px] resize-none"
                  placeholder="Optional description..."
                />
              </div>
              <div className="flex gap-3 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateProject(false)}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createProjectMutation.isPending}
                  className="btn-primary text-sm"
                >
                  {createProjectMutation.isPending ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}