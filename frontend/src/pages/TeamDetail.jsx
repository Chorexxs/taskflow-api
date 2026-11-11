/**
 * TeamDetail.jsx - Team Detail Page Component
 * 
 * Displays detailed information about a team including its projects and members.
 * Provides functionality for managing team members (inviting) and creating new projects.
 * 
 * Features:
 * - View team name and details
 * - List all projects within the team with navigation to project boards
 * - List team members with their roles (admin/member)
 * - Invite new members via email with role assignment
 * - Create new projects with name and description
 * 
 * @requires react-router-dom - For navigation and URL params
 * @requires @tanstack/react-query - For data fetching and mutations
 * @requires react-hot-toast - For notification toasts
 * @requires lucide-react - For icons
 */

import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../context/auth-context'
import QueryError from '../components/QueryError'
import { api } from '../api'
import toast from 'react-hot-toast'
import { ArrowLeft, Plus, Crown, X, FolderOpen, ChevronRight, Edit2, Save, Trash2 } from 'lucide-react'

/**
 * TeamDetail Component - Main page for viewing and managing a single team
 * 
 * Fetches and displays team information, projects, and members.
 * Provides modals for inviting members and creating new projects.
 * 
 * @returns {JSX.Element} Rendered team detail page with projects list, members list, and action modals
 * 
 * @state {string} teamId - Team ID from URL params for fetching team data
 * @state {boolean} showInvite - Controls visibility of invite member modal
 * @state {string} inviteEmail - Email input for inviting new member
 * @state {string} inviteRole - Role selection for invited member (member/admin)
 * @state {boolean} showCreateProject - Controls visibility of create project modal
 * @state {Object} newProject - Form state for new project name and description
 * @state {string} token - Authentication token from localStorage
 * 
 * @queries
 * - team: Fetches team details by teamId
 * - projects: Fetches all projects belonging to the team
 * - members: Fetches all team members with their user info and roles
 * 
 * @mutations
 * - inviteMutation: Invites a new member to the team via email
 * - createProjectMutation: Creates a new project in the team
 */

export default function TeamDetail() {
  const { teamId } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showInvite, setShowInvite] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')
  const [showCreateProject, setShowCreateProject] = useState(false)
  const [newProject, setNewProject] = useState({ name: '', description: '' })
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  const [showEditProject, setShowEditProject] = useState(false)
  const [editingProject, setEditingProject] = useState(null)
  const [editProjectForm, setEditProjectForm] = useState({ name: '', description: '' })
  const [showEditTeam, setShowEditTeam] = useState(false)
  const [teamForm, setTeamForm] = useState({ name: '', description: '' })
  const [showArchived, setShowArchived] = useState(false)

  const token = localStorage.getItem('access_token')
  const { user } = useAuth()
  const currentUserId = user?.id ?? 0

  const { data: team, isLoading: teamLoading, isError: teamError, refetch: refetchTeam } = useQuery({
    queryKey: ['team', teamId],
    queryFn: () => api.teams.get(token, teamId),
  })

  const { data: projects, isLoading: projectsLoading } = useQuery({
    queryKey: ['projects', teamId, showArchived],
    queryFn: () => api.projects.list(token, teamId, { include_archived: showArchived }),
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
      queryClient.invalidateQueries({ queryKey: ['team', teamId] })
      queryClient.invalidateQueries({ queryKey: ['team-members', teamId] })
      setShowInvite(false)
      setInviteEmail('')
      toast.success('Invitation sent!')
    },
    onError: () => toast.error('Failed to invite member'),
  })

  const createProjectMutation = useMutation({
    mutationFn: (data) => api.projects.create(token, teamId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects', teamId] })
      setShowCreateProject(false)
      setNewProject({ name: '', description: '' })
      toast.success('Project created!')
    },
    onError: () => toast.error('Failed to create project'),
  })

  const updateProjectMutation = useMutation({
    mutationFn: ({ projectId, data }) => api.projects.update(token, teamId, projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects', teamId] })
      setShowEditProject(false)
      setEditingProject(null)
      setEditProjectForm({ name: '', description: '' })
      toast.success('Project updated!')
    },
    onError: () => toast.error('Failed to update project'),
  })

  const updateTeamMutation = useMutation({
    mutationFn: (data) => api.teams.update(token, teamId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team', teamId] })
      queryClient.invalidateQueries({ queryKey: ['teams'] })
      setShowEditTeam(false)
      toast.success('Team updated!')
    },
    onError: (error) => toast.error(error.message || 'Failed to update team'),
  })

  const handleStartEditTeam = () => {
    setTeamForm({ name: team?.name || '', description: team?.description || '' })
    setShowEditTeam(true)
  }

  const handleSaveTeam = (e) => {
    e.preventDefault()
    updateTeamMutation.mutate(teamForm)
  }

  const restoreProjectMutation = useMutation({
    mutationFn: (projectId) => api.projects.restore(token, teamId, projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects', teamId] })
      toast.success('Project restored!')
    },
    onError: (error) => toast.error(error.message || 'Failed to restore project'),
  })

  const myMember = members?.find(m => m.user_id === currentUserId)
  const isAdmin = myMember?.role === 'admin'

  const handleStartEditProject = (project) => {
    setEditingProject(project)
    setEditProjectForm({ name: project.name, description: project.description || '' })
    setShowEditProject(true)
  }

  const handleSaveEditProject = () => {
    updateProjectMutation.mutate({ projectId: editingProject.id, data: editProjectForm })
  }

  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, role }) => api.teams.updateMemberRole(token, teamId, userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-members', teamId] })
      toast.success('Role updated!')
    },
    onError: () => toast.error('Failed to update role'),
  })

  const removeMemberMutation = useMutation({
    mutationFn: (userId) => api.teams.removeMember(token, teamId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team-members', teamId] })
      toast.success('Member removed!')
    },
    onError: () => toast.error('Failed to remove member'),
    retry: 0,
  })

  useEffect(() => {
    const query = searchQuery.trim()
    if (query.length < 2) {
      setSearchResults(null)
      return undefined
    }

    const timer = setTimeout(async () => {
      try {
        setSearchResults(await api.teams.search(token, teamId, query))
      } catch {
        toast.error('Search failed')
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [searchQuery, teamId, token])

  /**
   * Handles the invite member form submission
   * Prevents default form behavior and triggers the invite mutation
   * 
   * @param {Event} e - Form submit event
   * @returns {void}
   */

  const handleInvite = (e) => {
    e.preventDefault()
    inviteMutation.mutate({ email: inviteEmail, role: inviteRole })
  }

  /**
   * Handles the create project form submission
   * Prevents default form behavior and triggers the create project mutation
   * 
   * @param {Event} e - Form submit event
   * @returns {void}
   */

  const handleCreateProject = (e) => {
    e.preventDefault()
    createProjectMutation.mutate(newProject)
  }

  // Loading state - shown while team data is being fetched
  if (teamLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  if (teamError) {
    return (
      <div className="min-h-screen bg-[var(--color-bg-primary)]">
        <QueryError
          title="Could not load this team"
          message="It may have been removed or you may not have access."
          onRetry={() => refetchTeam()}
        />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-primary)]">
      <header className="border-b border-subtle bg-[var(--color-bg-secondary)]/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center min-h-16 gap-3 py-2">
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
              {isAdmin && (
                <button
                  onClick={handleStartEditTeam}
                  className="p-1.5 rounded-lg text-[var(--color-text-muted)] hover:text-[var(--color-accent)] hover:bg-[var(--color-bg-tertiary)] transition-all"
                  title="Edit team"
                  aria-label="Edit team"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
              )}
            </div>
            <div className="relative order-last w-full sm:order-none sm:flex-1 sm:max-w-md sm:ml-auto">
              <div className="relative">
                <input
                  type="text"
                  id="team-search"
                  name="team-search"
                  placeholder="Search..."
                  aria-label="Search team"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="input-field w-full py-1.5 text-sm"
                />
              </div>
              {searchResults && (
                <div className="absolute top-full mt-2 w-full max-w-md bg-[var(--color-bg-secondary)] border border-subtle rounded-xl shadow-elevated overflow-hidden z-50">
                  {searchResults.projects?.items?.length > 0 && (
                    <div className="p-2">
                      <p className="text-xs font-medium text-[var(--color-text-muted)] uppercase px-2 py-1">Projects</p>
                      {searchResults.projects.items.slice(0, 3).map(p => (
                        <button
                          key={p.id}
                          onClick={() => { navigate(`/teams/${teamId}/projects/${p.id}`); setSearchResults(null); setSearchQuery(''); }}
                          className="w-full text-left px-3 py-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-sm text-[var(--color-text-primary)]"
                        >
                          {p.name}
                        </button>
                      ))}
                    </div>
                  )}
                  {searchResults.tasks?.items?.length > 0 && (
                    <div className="p-2 border-t border-subtle">
                      <p className="text-xs font-medium text-[var(--color-text-muted)] uppercase px-2 py-1">Tasks</p>
                      {searchResults.tasks.items.slice(0, 3).map(t => (
                        <button
                          key={t.id}
                          onClick={() => { navigate(`/teams/${teamId}/projects/${t.project_id}/tasks/${t.id}`); setSearchResults(null); setSearchQuery(''); }}
                          className="w-full text-left px-3 py-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-sm text-[var(--color-text-primary)]"
                        >
                          {t.title}
                        </button>
                      ))}
                    </div>
                  )}
                  {searchResults.projects?.items?.length === 0 && searchResults.tasks?.items?.length === 0 && (
                    <p className="p-4 text-sm text-[var(--color-text-muted)] text-center">No results found</p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {showEditTeam && (
          <div className="mb-6 card p-4">
            <form onSubmit={handleSaveTeam} className="space-y-3">
              <div>
                <label htmlFor="edit-team-name" className="block text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-1">Team Name</label>
                <input
                  className="input-field"
                  id="edit-team-name"
                  name="name"
                  value={teamForm.name}
                  onChange={(e) => setTeamForm({ ...teamForm, name: e.target.value })}
                  required
                />
              </div>
              <div>
                <label htmlFor="edit-team-description" className="block text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-1">Description</label>
                <textarea
                  className="input-field"
                  id="edit-team-description"
                  name="description"
                  rows={2}
                  value={teamForm.description}
                  onChange={(e) => setTeamForm({ ...teamForm, description: e.target.value })}
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button type="button" onClick={() => setShowEditTeam(false)} className="btn-secondary text-sm">Cancel</button>
                <button type="submit" disabled={updateTeamMutation.isPending} className="btn-primary text-sm flex items-center gap-1.5">
                  <Save className="w-4 h-4" />
                  {updateTeamMutation.isPending ? 'Saving...' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-xl font-medium text-[var(--color-text-primary)] mb-1">Projects</h2>
                <p className="text-sm text-[var(--color-text-muted)]">{projects?.length || 0} projects</p>
                <label className="mt-2 inline-flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
                  <input
                    type="checkbox"
                    name="show-archived"
                    checked={showArchived}
                    onChange={(e) => setShowArchived(e.target.checked)}
                  />
                  Show archived
                </label>
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
                      <div className="flex items-center gap-1">
                        {isAdmin && project.status === 'archived' && (
                          <button
                            onClick={(e) => { e.preventDefault(); restoreProjectMutation.mutate(project.id); }}
                            className="p-1.5 text-[var(--color-text-muted)] hover:text-[var(--color-accent)] hover:bg-[var(--color-bg-secondary)] rounded transition-all"
                            title="Restore project"
                          >
                            <FolderOpen className="w-4 h-4" />
                          </button>
                        )}
                        {isAdmin && project.status !== 'archived' && (
                          <button
                            onClick={(e) => { e.preventDefault(); handleStartEditProject(project); }}
                            className="p-1.5 text-[var(--color-text-muted)] hover:text-[var(--color-accent)] hover:bg-[var(--color-bg-secondary)] rounded transition-all"
                            title="Edit project"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                        )}
                        <ChevronRight className="w-5 h-5 text-[var(--color-text-muted)] group-hover:text-[var(--color-accent)] group-hover:translate-x-1 transition-all" />
                      </div>
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
                {isAdmin && (
                  <button
                    onClick={() => setShowInvite(true)}
                    className="text-xs text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] font-medium transition-colors"
                  >
                    + Invite
                  </button>
                )}
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
                    <div className="flex items-center gap-2">
                      {member.role === 'admin' ? (
                        <Crown className="w-4 h-4 text-[var(--color-priority-medium)]" />
                      ) : (
                        isAdmin && member.user_id !== currentUserId && (
                          <select
                            id={`member-role-${member.user_id}`}
                            name={`member-role-${member.user_id}`}
                            aria-label={`Role for ${member.user?.email}`}
                            value={member.role}
                            onChange={(e) => updateRoleMutation.mutate({ userId: member.user_id, role: e.target.value })}
                            className="input-field py-1 px-1 text-xs w-full min-w-[94px]"
                          >
                            <option value="member">Member</option>
                            <option value="admin">Admin</option>
                          </select>
                        )
                      )}
                      {isAdmin && member.user_id !== currentUserId && (
                        <button
                          onClick={() => {
                            if (window.confirm(`Remove ${member.user?.email} from this team?`)) {
                              removeMemberMutation.mutate(member.user_id)
                            }
                          }}
                          className="p-1.5 text-[var(--color-text-muted)] hover:text-red-500 hover:bg-[var(--color-bg-secondary)] rounded transition-all"
                          title="Remove member"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
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
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-label="Add team member">
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
                <label htmlFor="invite-email" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Email</label>
                <input
                  type="email"
                  id="invite-email"
                  name="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  required
                  className="input-field"
                  placeholder="colleague@example.com"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="invite-role" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Role</label>
                <select
                  id="invite-role"
                  name="role"
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
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-label="Create project">
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
                <label htmlFor="create-project-name" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Name</label>
                <input
                  type="text"
                  id="create-project-name"
                  name="name"
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  required
                  className="input-field"
                  placeholder="My Project"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="create-project-description" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Description</label>
                <textarea
                  id="create-project-description"
                  name="description"
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

      {showEditProject && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" role="dialog" aria-modal="true" aria-label="Edit project">
          <div className="bg-[var(--color-bg-secondary)] rounded-xl shadow-xl max-w-md w-full">
            <div className="flex items-center justify-between p-4 border-b border-subtle">
              <h2 className="text-lg font-medium text-[var(--color-text-primary)]">Edit Project</h2>
              <button
                onClick={() => { setShowEditProject(false); setEditingProject(null); }}
                className="p-2 rounded-lg hover:bg-[var(--color-bg-tertiary)] text-[var(--color-text-muted)]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); handleSaveEditProject(); }} className="p-4 space-y-4">
              <div className="space-y-2">
                <label htmlFor="team-edit-project-name" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Name</label>
                <input
                  type="text"
                  id="team-edit-project-name"
                  name="name"
                  value={editProjectForm.name}
                  onChange={(e) => setEditProjectForm({ ...editProjectForm, name: e.target.value })}
                  required
                  className="input-field"
                  placeholder="My Project"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="team-edit-project-description" className="block text-xs font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Description</label>
                <textarea
                  id="team-edit-project-description"
                  name="description"
                  value={editProjectForm.description}
                  onChange={(e) => setEditProjectForm({ ...editProjectForm, description: e.target.value })}
                  className="input-field min-h-[80px] resize-none"
                  placeholder="Optional description..."
                />
              </div>
              <div className="flex gap-3 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => { setShowEditProject(false); setEditingProject(null); }}
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateProjectMutation.isPending || !editProjectForm.name.trim()}
                  className="btn-primary text-sm"
                >
                  {updateProjectMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}