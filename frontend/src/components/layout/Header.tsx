import React from 'react';
import { Search, Plus, LogOut } from 'lucide-react';

interface HeaderProps {
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  onOpenUploadModal: () => void;
  userEmail: string;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  searchQuery,
  setSearchQuery,
  onOpenUploadModal,
  userEmail,
  onLogout,
}) => {
  return (
    <header className="header">
      <div style={{ position: 'relative' }}>
        <Search
          size={16}
          style={{
            position: 'absolute',
            left: '0.75rem',
            top: '50%',
            transform: 'translateY(-50%)',
            color: 'var(--text-muted)',
          }}
        />
        <input
          type="text"
          className="input-search"
          placeholder="Search meeting titles & transcripts..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {/* Authenticated user badge */}
        <div
          id="header-user-email"
          style={{
            fontSize: '0.8125rem',
            color: 'var(--text-muted)',
            padding: '0.375rem 0.75rem',
            background: 'var(--bg-input)',
            border: '1px solid var(--border-color)',
            borderRadius: '6px',
            maxWidth: '200px',
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
