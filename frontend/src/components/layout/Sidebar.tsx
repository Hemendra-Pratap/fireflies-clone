import React from 'react';
import { LayoutDashboard, Mic, Settings, Sparkles, FolderKanban, LogOut } from 'lucide-react';
import { User } from '../../api/auth';

interface SidebarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  user: User;
  onLogout: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, setCurrentTab, user, onLogout }) => {
  const avatarLetter = (user.full_name || user.email).charAt(0).toUpperCase();
  const displayName = user.full_name || user.email;

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Sparkles size={20} />
        </div>
        <span>FireFlies AI</span>
      </div>

      <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <button
          id="nav-dashboard"
          className={`nav-item ${currentTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setCurrentTab('dashboard')}
        >
          <LayoutDashboard size={18} />
          <span>Dashboard</span>
        </button>

        <button
          id="nav-meetings"
          className={`nav-item ${currentTab === 'all-meetings' ? 'active' : ''}`}
          onClick={() => setCurrentTab('all-meetings')}
        >
          <Mic size={18} />
          <span>All Meetings</span>
        </button>

        <button
          id="nav-workspaces"
          className={`nav-item ${currentTab === 'workspaces' ? 'active' : ''}`}
          onClick={() => setCurrentTab('workspaces')}
        >
          <FolderKanban size={18} />
          <span>Workspaces</span>
        </button>

        <button
          id="nav-settings"
          className={`nav-item ${currentTab === 'settings' ? 'active' : ''}`}
          onClick={() => setCurrentTab('settings')}
        >
          <Settings size={18} />
          <span>Settings</span>
        </button>
      </nav>

      <div style={{ marginTop: 'auto', paddingTop: '1.5rem', borderTop: '1px solid var(--border-color)' }}>
        {/* User info row */}
        <div
          id="sidebar-user-info"
          style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.875rem' }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #4f46e5, #9333ea)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              color: '#fff',
              flexShrink: 0,
              fontSize: '0.9375rem',
            }}
          >
            {avatarLetter}
          </div>
          <div style={{ minWidth: 0 }}>
            <div
              style={{
                fontWeight: 600,
                fontSize: '0.875rem',
                color: 'var(--text-heading)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
              title={displayName}
            >
              {displayName}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Authenticated</div>
          </div>
        </div>

        {/* Logout button */}
        <button
          id="sidebar-logout-btn"
          className="nav-item"
          onClick={onLogout}
          style={{ width: '100%', color: '#f87171' }}
        >
          <LogOut size={16} />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
};
