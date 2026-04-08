/**
 * TaskFlow Frontend - Dashboard Page
 * 
 * This page displays the user's teams and allows creating new teams.
 * It's the main landing page after login.
 * 
 * Features:
 * - List of user's teams with project counts
 * - Create new team modal/form
 * - Loading and error states
 * - Navigation to team details
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import toast from 'react-hot-toast';
import { Plus, Users, FolderKanban, ChevronRight } from 'lucide-react';

/**
 * Dashboard page component.
 * Shows user's teams and allows creating new ones.
 * 
 * @returns {JSX.Element} Dashboard with teams list
 * 
 * @example
 * <Route path="/" element={<Dashboard />} />
 */
export default function Dashboard() {
  const queryClient = useQueryClient();
  const [showCreateTeam, setShowCreateTeam] = useState(false);
  const [newTeam, setNewTeam] = useState({ name: '', slug: '', description: '' });

  /**
   * Fetch user's teams from API.
   */
  const { data: teams, isLoading } = useQuery({
    queryKey: ['teams'],
    queryFn: () => api.teams.list(localStorage.getItem('access_token')),
  });

  /**
   * Create team mutation.
   */
  const createTeamMutation = useMutation({
    mutationFn: (data) => api.teams.create(localStorage.getItem('access_token'), data),
    onSuccess: () => {
      queryClient.invalidateQueries(['teams']);
      setShowCreateTeam(false);
      setNewTeam({ name: '', slug: '', description: '' });
      toast.success('Team created!');
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to create team');
    },
  });

  /**
   * Handle team creation form submit.
   */
  const handleCreateTeam = (e) => {
    e.preventDefault();
    createTeamMutation.mutate(newTeam);
  };

  return (
    <>
      {/* Page header */}
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

      {/* Loading state */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="card p-6 animate-pulse">
              <div className="h-6 bg-[var(--color-bg-tertiary)] rounded w-3/4 mb-3"></div>
              <div className="h-4 bg-[var(--color-bg-tertiary)] rounded w-1/2"></div>
            </div>
          ))}
        </div>
      ) : teams?.length === 0 ? (
        /* Empty state */
        <div className="text-center py-16">
          <div className="w-16 h-16 bg-[var(--color-bg-tertiary)] rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Users className="w-8 h-8 text-[var(--color-text-muted)]" />
          </div>
          <h3 className="text-lg font-medium text-[var(--color-text-primary)] mb-2">No teams yet</h3>
          <p className="text-sm text-[var(--color-text-muted)] mb-6">Create your first team to get started</p>
          <button
            onClick={() => setShowCreateTeam(true)}
            className="btn-primary"
          >
            Create Team
          </button>
        </div>
      ) : (
        /* Teams grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {teams?.map(team => (
            <Link
              key={team.id}
              to={`/teams/${team.slug}`}
              className="card p-6 hover:border-[var(--color-accent)] transition-all group"
            >
              <h3 className="text-lg font-medium text-[var(--color-text-primary)] mb-2 group-hover:text-[var(--color-accent)]">
                {team.name}
              </h3>
              {team.description && (
                <p className="text-sm text-[var(--color-text-muted)] mb-4 line-clamp-2">
                  {team.description}
                </p>
              )}
              <div className="flex items-center gap-1 text-xs text-[var(--color-text-muted)]">
                <ChevronRight className="w-4 h-4" />
                View team
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Create team modal */}
      {showCreateTeam && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[var(--color-bg-secondary)] border border-subtle rounded-2xl p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-medium text-[var(--color-text-primary)] mb-4">Create Team</h3>
            <form onSubmit={handleCreateTeam} className="space-y-4">
              <div>
                <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Team Name</label>
                <input
                  type="text"
                  value={newTeam.name}
                  onChange={(e) => setNewTeam({ ...newTeam, name: e.target.value })}
                  required
                  className="input-field"
                  placeholder="My Team"
                />
              </div>
              <div>
                <label className="block text-sm text-[var(--color-text-secondary)] mb-1">URL Slug</label>
                <input
                  type="text"
                  value={newTeam.slug}
                  onChange={(e) => setNewTeam({ ...newTeam, slug: e.target.value.toLowerCase().replace(/\s+/g, '-') })}
                  required
                  className="input-field"
                  placeholder="my-team"
                />
              </div>
              <div>
                <label className="block text-sm text-[var(--color-text-secondary)] mb-1">Description (optional)</label>
                <textarea
                  value={newTeam.description}
                  onChange={(e) => setNewTeam({ ...newTeam, description: e.target.value })}
                  className="input-field"
                  rows={3}
                  placeholder="Team description..."
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateTeam(false)}
                  className="btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createTeamMutation.isPending}
                  className="btn-primary flex-1"
                >
                  {createTeamMutation.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
