import React, { useState, useRef, useEffect } from 'react';
import { useWorkspace } from '../../context/WorkspaceContext';
import { Building2, ChevronDown, Plus, Users, Check } from 'lucide-react';

interface WorkspaceSelectorProps {
  onOpenCreateWorkspace: () => void;
  onOpenManageMembers: () => void;
}

export const WorkspaceSelector: React.FC<WorkspaceSelectorProps> = ({
  onOpenCreateWorkspace,
  onOpenManageMembers,
}) => {
  const { workspaces, activeWorkspace, activeWorkspaceRole, switchWorkspace, loading } = useWorkspace();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (loading && !activeWorkspace) {
    return (
      <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', padding: '0.375rem 0.75rem' }}>
        Loading workspaces...
      </div>
    );
  }

  const isOwnerOrAdmin = activeWorkspaceRole === 'OWNER' || activeWorkspaceRole === 'ADMIN';

  return (
    <div ref={dropdownRef} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        id="workspace-selector-btn"
        className="btn btn-secondary"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.4rem 0.75rem',
          fontSize: '0.8125rem',
          borderColor: 'var(--border-color)',
          background: 'var(--bg-input)',
        }}
        title="Active Workspace"
      >
        <Building2 size={16} style={{ color: 'var(--primary)' }} />
        <span
          style={{
            maxWidth: '140px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            fontWeight: 600,
          }}
        >
          {activeWorkspace ? activeWorkspace.name : 'Select Workspace'}
        </span>
        {activeWorkspaceRole && (
          <span
            style={{
              fontSize: '0.6875rem',
              padding: '0.125rem 0.375rem',
              borderRadius: '4px',
              backgroundColor: 'rgba(99, 102, 241, 0.15)',
              color: 'var(--primary)',
              fontWeight: 700,
              textTransform: 'uppercase',
            }}
          >
            {activeWorkspaceRole}
          </span>
        )}
        <ChevronDown size={14} style={{ color: 'var(--text-muted)' }} />
      </button>

      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 0.5rem)',
            left: 0,
            width: '240px',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
            zIndex: 1000,
            overflow: 'hidden',
            padding: '0.5rem 0',
          }}
        >
          <div
            style={{
              padding: '0.375rem 0.75rem',
              fontSize: '0.6875rem',
              fontWeight: 700,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}
          >
            Workspaces
          </div>

          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            {workspaces.map((ws) => {
              const isSelected = activeWorkspace?.id === ws.id;
              return (
                <button
                  key={ws.id}
                  onClick={() => {
                    switchWorkspace(ws.id);
                    setIsOpen(false);
                  }}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.5rem 0.75rem',
                    fontSize: '0.8125rem',
                    color: isSelected ? '#fff' : 'var(--text-main)',
                    backgroundColor: isSelected ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                    border: 'none',
                    textAlign: 'left',
                    cursor: 'pointer',
                    transition: 'background 0.15s ease',
                  }}
                >
                  <span style={{ fontWeight: isSelected ? 600 : 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {ws.name}
                  </span>
                  {isSelected && <Check size={14} style={{ color: 'var(--primary)' }} />}
                </button>
              );
            })}
          </div>

          <div style={{ borderTop: '1px solid var(--border-color)', marginTop: '0.375rem', paddingTop: '0.375rem' }}>
            {isOwnerOrAdmin && (
              <button
                onClick={() => {
                  onOpenManageMembers();
                  setIsOpen(false);
                }}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.5rem 0.75rem',
                  fontSize: '0.8125rem',
                  color: 'var(--text-main)',
                  backgroundColor: 'transparent',
                  border: 'none',
                  textAlign: 'left',
                  cursor: 'pointer',
                }}
              >
                <Users size={14} style={{ color: 'var(--primary)' }} />
                <span>Workspace Members</span>
              </button>
            )}

            <button
              onClick={() => {
                onOpenCreateWorkspace();
                setIsOpen(false);
              }}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 0.75rem',
                fontSize: '0.8125rem',
                color: 'var(--primary)',
                backgroundColor: 'transparent',
                border: 'none',
                textAlign: 'left',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              <Plus size={14} />
              <span>Create New Workspace</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
