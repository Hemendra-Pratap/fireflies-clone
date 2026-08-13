import React, { useState, useEffect, useRef } from 'react';
import { notificationsApi } from '../../api/notifications';
import { NotificationRead } from '../../types/notification';
import { Bell, CheckCheck, Loader2, AlertCircle, CheckCircle2, XCircle, Calendar, Sparkles } from 'lucide-react';

interface NotificationDropdownProps {
  workspaceId?: number;
  onSelectMeeting?: (meetingId: number) => void;
}

export const NotificationDropdown: React.FC<NotificationDropdownProps> = ({
  workspaceId,
  onSelectMeeting,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationRead[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  const fetchUnreadCount = async () => {
    try {
      const count = await notificationsApi.getUnreadCount(workspaceId);
      setUnreadCount(count);
    } catch {
      // Ignore background poll errors
    }
  };

  const fetchNotifications = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await notificationsApi.listNotifications(workspaceId);
      setNotifications(res.items);
      setUnreadCount(res.unread_count);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load notifications.');
    } finally {
      setLoading(false);
    }
  };

  // Poll unread count periodically
  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 15000);
    return () => clearInterval(interval);
  }, [workspaceId]);

  // Fetch full list when dropdown opens
  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen, workspaceId]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleMarkAsRead = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await notificationsApi.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // Ignore error
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await notificationsApi.markAllAsRead(workspaceId);
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, read_at: n.read_at || new Date().toISOString() }))
      );
      setUnreadCount(0);
    } catch {
      // Ignore error
    }
  };

  const handleNotificationClick = async (notif: NotificationRead) => {
    if (!notif.read_at) {
      try {
        await notificationsApi.markAsRead(notif.id);
        setUnreadCount((prev) => Math.max(0, prev - 1));
      } catch {
        // Ignore error
      }
    }
    setIsOpen(false);
    if (notif.meeting_id && onSelectMeeting) {
      onSelectMeeting(notif.meeting_id);
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'meeting_completed':
        return <CheckCircle2 size={16} style={{ color: '#4ade80' }} />;
      case 'meeting_failed':
        return <XCircle size={16} style={{ color: '#ef4444' }} />;
      case 'upcoming_meeting':
        return <Calendar size={16} style={{ color: 'var(--primary)' }} />;
      default:
        return <Sparkles size={16} style={{ color: '#818cf8' }} />;
    }
  };

  const formatTimeAgo = (isoStr: string) => {
    try {
      const date = new Date(isoStr);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffMins = Math.floor(diffMs / 60000);

      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
      return isoStr;
    }
  };

  return (
    <div style={{ position: 'relative' }} ref={dropdownRef}>
      {/* Bell Button with Unread Counter Badge */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '0.5rem',
          color: isOpen ? '#fff' : 'var(--text-muted)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          transition: 'all 0.2s ease',
        }}
        title="Notifications"
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span
            style={{
              position: 'absolute',
              top: '-4px',
              right: '-4px',
              backgroundColor: '#ef4444',
              color: '#fff',
              fontSize: '0.65rem',
              fontWeight: 800,
              padding: '0.1rem 0.35rem',
              borderRadius: '10px',
              minWidth: '16px',
              textAlign: 'center',
              lineHeight: 1.2,
              boxShadow: '0 0 6px rgba(239, 68, 68, 0.6)',
            }}
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Floating Notification Panel Overlay */}
      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 0.5rem)',
            right: 0,
            width: '360px',
            maxHeight: '480px',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: '12px',
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.5)',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          {/* Panel Header */}
          <div
            style={{
              padding: '0.875rem 1rem',
              borderBottom: '1px solid var(--border-color)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              backgroundColor: 'var(--bg-input)',
            }}
          >
            <div style={{ fontWeight: 700, fontSize: '0.9375rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <span>Notifications</span>
              {unreadCount > 0 && (
                <span
                  style={{
                    fontSize: '0.7rem',
                    backgroundColor: 'rgba(99, 102, 241, 0.2)',
                    color: 'var(--primary)',
                    padding: '0.125rem 0.5rem',
                    borderRadius: '10px',
                    fontWeight: 700,
                  }}
                >
                  {unreadCount} new
                </span>
              )}
            </div>

            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllAsRead}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--primary)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  padding: 0,
                }}
              >
                <CheckCheck size={14} /> Mark all read
              </button>
            )}
          </div>

          {/* Panel Content Body */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '0.5rem 0' }}>
            {loading ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                <Loader2 size={24} className="animate-spin" style={{ color: 'var(--primary)', marginBottom: '0.5rem' }} />
                <div style={{ fontSize: '0.8125rem' }}>Loading notifications...</div>
              </div>
            ) : error ? (
              <div style={{ padding: '1.5rem', textAlign: 'center', color: '#fca5a5', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.375rem' }}>
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            ) : notifications.length > 0 ? (
              notifications.map((notif) => {
                const isUnread = !notif.read_at;

                return (
                  <div
                    key={notif.id}
                    onClick={() => handleNotificationClick(notif)}
                    style={{
                      padding: '0.75rem 1rem',
                      display: 'flex',
                      gap: '0.75rem',
                      alignItems: 'flex-start',
                      backgroundColor: isUnread ? 'rgba(99, 102, 241, 0.08)' : 'transparent',
                      borderLeft: isUnread ? '3px solid var(--primary)' : '3px solid transparent',
                      cursor: 'pointer',
                      transition: 'background-color 0.15s ease',
                      borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
                    }}
                  >
                    <div style={{ marginTop: '0.125rem', flexShrink: 0 }}>
                      {getNotificationIcon(notif.type)}
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '0.375rem' }}>
                        <div
                          style={{
                            fontSize: '0.8125rem',
                            fontWeight: isUnread ? 700 : 600,
                            color: isUnread ? '#fff' : 'var(--text-main)',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {notif.title}
                        </div>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', flexShrink: 0 }}>
                          {formatTimeAgo(notif.created_at)}
                        </span>
                      </div>

                      <p
                        style={{
                          fontSize: '0.75rem',
                          color: 'var(--text-muted)',
                          lineHeight: 1.35,
                          marginTop: '0.125rem',
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                        }}
                      >
                        {notif.message}
                      </p>
                    </div>

                    {isUnread && (
                      <button
                        onClick={(e) => handleMarkAsRead(notif.id, e)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--text-dim)',
                          cursor: 'pointer',
                          padding: '0.125rem',
                          flexShrink: 0,
                        }}
                        title="Mark as read"
                      >
                        <div
                          style={{
                            width: '6px',
                            height: '6px',
                            borderRadius: '50%',
                            backgroundColor: 'var(--primary)',
                          }}
                        />
                      </button>
                    )}
                  </div>
                );
              })
            ) : (
              <div style={{ padding: '2.5rem 1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                <Bell size={28} style={{ color: 'var(--text-dim)', marginBottom: '0.5rem' }} />
                <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#fff' }}>No Notifications</div>
                <div style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>
                  You will receive notifications here when meetings complete or upcoming events arrive.
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
