/**
 * TaskFlow Frontend - Notifications Bell Component
 * 
 * This component displays a notification bell icon with unread count
 * and a dropdown panel showing recent notifications.
 * 
 * Features:
 * - Bell icon with unread notification badge
 * - Dropdown panel with notification list
 * - Mark individual notifications as read
 * - Mark all as read functionality
 * - Auto-refresh every 30 seconds
 * - Relative time display (e.g., "5m ago")
 * - Click outside to close
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import toast from 'react-hot-toast';
import { Bell, CheckCheck, X } from 'lucide-react';

/**
 * Notifications bell component with dropdown panel.
 * Shows unread count and allows viewing/marking notifications.
 * 
 * @returns {JSX.Element} Notifications bell with dropdown
 * 
 * @example
 * <NotificationsBell />
 */
export default function NotificationsBell() {
  const [showPanel, setShowPanel] = useState(false);
  const token = localStorage.getItem('access_token');
  const queryClient = useQueryClient();

  /**
   * Fetch notifications from API.
   * Auto-refreshes every 30 seconds.
   */
  const { data: notifications, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => api.notifications.list(token),
    refetchInterval: 30000, // 30 seconds
  });

  /**
   * Mark a single notification as read.
   */
  const markReadMutation = useMutation({
    mutationFn: (id) => api.notifications.markRead(token, id),
    onSuccess: () => {
      queryClient.invalidateQueries(['notifications']);
    },
  });

  /**
   * Mark all notifications as read.
   */
  const markAllReadMutation = useMutation({
    mutationFn: () => api.notifications.markAllRead(token),
    onSuccess: () => {
      queryClient.invalidateQueries(['notifications']);
      toast.success('All notifications marked as read');
    },
  });

  // Count unread notifications
  const unreadCount = notifications?.filter(n => !n.is_read)?.length || 0;

  /**
   * Format timestamp as relative time.
   * 
   * @param {string} date - ISO date string
   * @returns {string} Relative time string
   */
  const getRelativeTime = (date) => {
    const now = new Date();
    const then = new Date(date);
    const diffMs = now - then;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return then.toLocaleDateString();
  };

  return (
    <div className="relative">
      {/* Bell button with unread badge */}
      <button
        onClick={() => setShowPanel(!showPanel)}
        className="relative p-2 rounded-lg text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-[var(--color-text-primary)] transition-all"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-[var(--color-accent)] text-[var(--color-bg-primary)] text-[10px] font-bold rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Notifications dropdown panel */}
      {showPanel && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-[var(--color-bg-secondary)] border border-subtle rounded-xl shadow-elevated z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-subtle">
            <h3 className="text-sm font-medium text-[var(--color-text-primary)]">Notifications</h3>
            <button
              onClick={() => setShowPanel(false)}
              className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Notification list */}
          <div className="max-h-80 overflow-y-auto">
            {isLoading ? (
              <div className="p-4 text-center text-[var(--color-text-muted)]">Loading...</div>
            ) : notifications?.length === 0 ? (
              <div className="p-6 text-center">
                <Bell className="w-8 h-8 text-[var(--color-text-muted)] mx-auto mb-2 opacity-50" />
                <p className="text-sm text-[var(--color-text-muted)]">No notifications</p>
              </div>
            ) : (
              notifications?.map(notification => (
                <div
                  key={notification.id}
                  className={`p-4 border-b border-subtle hover:bg-[var(--color-bg-tertiary)] cursor-pointer transition-colors ${
                    !notification.is_read ? 'bg-[var(--color-accent-muted)]/30' : ''
                  }`}
                  onClick={() => markReadMutation.mutate(notification.id)}
                >
                  <p className="text-sm text-[var(--color-text-primary)] leading-snug">{notification.message}</p>
                  <p className="text-xs text-[var(--color-text-muted)] mt-2">{getRelativeTime(notification.created_at)}</p>
                </div>
              ))
            )}
          </div>

          {/* Mark all as read button */}
          {unreadCount > 0 && (
            <div className="p-3 border-t border-subtle bg-[var(--color-bg-tertiary)]/50">
              <button
                onClick={() => markAllReadMutation.mutate()}
                className="text-xs text-[var(--color-accent)] hover:text-[var(--color-accent-hover)] font-medium flex items-center gap-1.5 transition-colors"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                Mark all as read
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
