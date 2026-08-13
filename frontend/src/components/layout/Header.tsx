import React, { useState } from 'react';
import { Search, Plus, LogOut, X, Sun, Moon } from 'lucide-react';
import { WorkspaceSelector } from './WorkspaceSelector';
import { SearchDropdown } from '../search/SearchDropdown';
import { NotificationDropdown } from '../notifications/NotificationDropdown';
import { useWorkspace } from '../../context/WorkspaceContext';
import { useTheme } from '../../context/ThemeContext';

interface HeaderProps {
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  onOpenUploadModal: () => void;
  onOpenCreateWorkspace: () => void;
  onOpenManageMembers: () => void;
  onSelectMeeting: (meetingId: number) => void;
  userEmail: string;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  searchQuery,
  setSearchQuery,
  onOpenUploadModal,
  onOpenCreateWorkspace,
  onOpenManageMembers,
  onSelectMeeting,
  userEmail,
  onLogout,
}) => {
  const { activeWorkspace } = useWorkspace();
  const { theme, toggleTheme } = useTheme();
  const [isDropdownOpen, setIsDropdownOpen] = useState(true);

  return (
    <header className="header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flex: 1 }}>
        <WorkspaceSelector
          onOpenCreateWorkspace={onOpenCreateWorkspace}
          onOpenManageMembers={onOpenManageMembers}
        />

        <div style={{ position: 'relative', flex: 1, maxWidth: '440px' }}>
          <Search
            size={16}
            style={{
              position: 'absolute',
              left: '0.75rem',
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--text-muted)',
              pointerEvents: 'none',
            }}
          />
          <input
            type="text"
            className="input-search"
            placeholder="Search meeting titles, transcripts, action items..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setIsDropdownOpen(true);
            }}
            onFocus={() => setIsDropdownOpen(true)}
            style={{ paddingRight: searchQuery ? '2rem' : '0.75rem' }}
          />

          {searchQuery && (
            <button
              onClick={() => {
                setSearchQuery('');
                setIsDropdownOpen(false);
              }}
              style={{
                position: 'absolute',
                right: '0.75rem',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: 0,
                display: 'flex',
                alignItems: 'center',
              }}
              title="Clear search"
            >
              <X size={14} />
            </button>
          )}

          {isDropdownOpen && searchQuery.trim() && (
            <SearchDropdown
              query={searchQuery}
              onSelectMeeting={(meetingId) => {
                onSelectMeeting(meetingId);
                setIsDropdownOpen(false);
              }}
              onClose={() => setIsDropdownOpen(false)}
            />
          )}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {/* Theme Switch Toggle Button */}
        <button
          id="theme-toggle-btn"
          className="theme-toggle-btn"
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          aria-label={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        {/* Notification Bell Dropdown */}
        <NotificationDropdown
          workspaceId={activeWorkspace?.id}
          onSelectMeeting={onSelectMeeting}
        />

        <div
          id="header-user-email"
          style={{
            fontSize: '0.8125rem',
            color: 'var(--text-muted)',
            padding: '0.375rem 0.75rem',
            background: 'var(--bg-input)',
            border: '1px solid var(--border-color)',
            borderRadius: '6px',
            maxWidth: '180px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
          title={userEmail}
        >
          {userEmail}
        </div>

        <button className="btn btn-primary" onClick={onOpenUploadModal}>
          <Plus size={18} />
          <span>New Meeting</span>
        </button>

        <button
          id="header-logout-btn"
          className="btn btn-secondary"
          onClick={onLogout}
          title="Sign out"
          style={{ padding: '0.5rem 0.875rem' }}
        >
          <LogOut size={16} />
          <span>Sign out</span>
        </button>
      </div>
    </header>
  );
};
