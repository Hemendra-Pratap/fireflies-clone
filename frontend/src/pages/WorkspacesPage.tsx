import React, { useState } from 'react';
import { useWorkspace } from '../context/WorkspaceContext';
import { User } from '../api/auth';
import {
  Building2,
  Plus,
  Users,
  UserPlus,
  Trash2,
  Loader2,
  CheckCircle,
  AlertCircle,
  Check,
  Edit2,
} from 'lucide-react';

interface WorkspacesPageProps {
  user: User;
  onOpenCreateWorkspaceModal: () => void;
}

export const WorkspacesPage: React.FC<WorkspacesPageProps> = ({
  user,
  onOpenCreateWorkspaceModal,
}) => {
  const {
    workspaces,
    activeWorkspace,
    activeWorkspaceRole,
    switchWorkspace,
    updateWorkspaceName,
    addMember,
    updateMemberRole,
    removeMember,
  } = useWorkspace();

  // Rename Workspace state
  const [isEditingName, setIsEditingName] = useState(false);
  const [workspaceName, setWorkspaceName] = useState(activeWorkspace?.name || '');
  const [renameLoading, setRenameLoading] = useState(false);
  const [renameError, setRenameError] = useState<string | null>(null);

  // Invite Member state
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'ADMIN' | 'MEMBER'>('MEMBER');
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteSuccess, setInviteSuccess] = useState<string | null>(null);

  // Member Action state
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const isOwnerOrAdmin = activeWorkspaceRole === 'OWNER' || activeWorkspaceRole === 'ADMIN';

  const handleRenameWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !workspaceName.trim()) return;

    setRenameLoading(true);
    setRenameError(null);

    try {
      await updateWorkspaceName(activeWorkspace.id, workspaceName.trim());
      setIsEditingName(false);
    } catch (err: any) {
      setRenameError(err.response?.data?.detail || 'Failed to update workspace name.');
    } finally {
      setRenameLoading(false);
    }
  };

  const handleInviteMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !inviteEmail.trim()) return;

    setInviteLoading(true);
    setInviteError(null);
    setInviteSuccess(null);

    try {
      await addMember(activeWorkspace.id, inviteEmail.trim(), inviteRole);
      setInviteSuccess(`User ${inviteEmail.trim()} added successfully.`);
      setInviteEmail('');
    } catch (err: any) {
      setInviteError(err.response?.data?.detail || 'Failed to add workspace member.');
    } finally {
      setInviteLoading(false);
    }
  };

  const handleRoleChange = async (memberId: number, newRole: string) => {
    if (!activeWorkspace) return;
    setActionLoadingId(memberId);
    setActionError(null);

    try {
      await updateMemberRole(activeWorkspace.id, memberId, newRole);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to update member role.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleRemoveMember = async (memberId: number, memberEmail: string) => {
    if (!activeWorkspace) return;
    if (!window.confirm(`Are you sure you want to remove ${memberEmail} from this workspace?`)) {
      return;
    }

    setActionLoadingId(memberId);
    setActionError(null);

    try {
      await removeMember(activeWorkspace.id, memberId);
    } catch (err: any) {
      setActionError(err.response?.data?.detail || 'Failed to remove member.');
    } finally {
      setActionLoadingId(null);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1000px', margin: '0 auto' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '2rem',
        }}
      >
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fff' }}>Workspace Management</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Switch workspaces, invite team members, and manage workspace permissions.
          </p>
        </div>

        <button className="btn btn-primary" onClick={onOpenCreateWorkspaceModal}>
          <Plus size={18} />
          <span>New Workspace</span>
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '1.75rem' }}>
        {/* Left Column: Workspaces List */}
        <div className="card" style={{ padding: '1.25rem', height: 'fit-content' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.875rem' }}>
            Your Workspaces ({workspaces.length})
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {workspaces.map((ws) => {
              const isActive = activeWorkspace?.id === ws.id;
              const role = ws.owner_id === user.id ? 'OWNER' : ws.members.find((m) => m.user_id === user.id)?.role || 'MEMBER';

              return (
                <div
                  key={ws.id}
                  onClick={() => switchWorkspace(ws.id)}
                  style={{
                    padding: '0.875rem 1rem',
                    borderRadius: '8px',
                    backgroundColor: isActive ? 'rgba(99, 102, 241, 0.12)' : 'var(--bg-input)',
                    border: isActive ? '1px solid var(--primary)' : '1px solid var(--border-color)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.375rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.9375rem', color: isActive ? '#fff' : 'var(--text-main)' }}>
                      {ws.name}
                    </span>
                    {isActive && <Check size={16} style={{ color: 'var(--primary)' }} />}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span>{ws.members?.length || 1} member(s)</span>
                    <span
                      style={{
                        padding: '0.125rem 0.375rem',
                        borderRadius: '4px',
                        backgroundColor: 'rgba(255, 255, 255, 0.05)',
                        fontWeight: 600,
                        color: role === 'OWNER' ? '#fde047' : role === 'ADMIN' ? 'var(--primary)' : 'var(--text-dim)',
                      }}
                    >
                      {role}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Active Workspace Management Details */}
        {activeWorkspace ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Header & Rename Card */}
            <div className="card" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <Building2 size={24} style={{ color: 'var(--primary)' }} />
                  <div>
                    {!isEditingName ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff' }}>
                          {activeWorkspace.name}
                        </h2>
                        {isOwnerOrAdmin && (
                          <button
                            onClick={() => {
                              setWorkspaceName(activeWorkspace.name);
                              setIsEditingName(true);
                            }}
                            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '0.25rem' }}
                            title="Rename workspace"
                          >
                            <Edit2 size={16} />
                          </button>
                        )}
                      </div>
                    ) : (
                      <form onSubmit={handleRenameWorkspace} style={{ display: 'flex', gap: '0.5rem' }}>
                        <input
                          type="text"
                          className="input-search"
                          value={workspaceName}
                          onChange={(e) => setWorkspaceName(e.target.value)}
                          style={{ paddingLeft: '0.75rem' }}
                          autoFocus
                        />
                        <button type="submit" className="btn btn-primary" disabled={renameLoading || !workspaceName.trim()}>
                          {renameLoading ? <Loader2 size={14} className="animate-spin" /> : 'Save'}
                        </button>
                        <button type="button" className="btn btn-secondary" onClick={() => setIsEditingName(false)}>
                          Cancel
                        </button>
                      </form>
                    )}
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                      Workspace ID #{activeWorkspace.id} • Your Role: <strong style={{ color: '#fff' }}>{activeWorkspaceRole}</strong>
                    </span>
                  </div>
                </div>
              </div>

              {renameError && (
                <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#fca5a5', padding: '0.625rem', borderRadius: '6px', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.75rem' }}>
                  <AlertCircle size={14} />
                  <span>{renameError}</span>
                </div>
              )}
            </div>

            {/* Members Management Card */}
            <div className="card" style={{ padding: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', paddingBottom: '0.875rem', borderBottom: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                  <Users size={20} style={{ color: '#818cf8' }} />
                  <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#fff' }}>
                    Members & Permissions ({activeWorkspace.members.length})
                  </h3>
                </div>
              </div>

              {actionError && (
                <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#fca5a5', padding: '0.75rem', borderRadius: '6px', marginBottom: '1rem', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <AlertCircle size={16} />
                  <span>{actionError}</span>
                </div>
              )}

              {/* Add Member Form (Owner / Admin) */}
              {isOwnerOrAdmin && (
                <form onSubmit={handleInviteMember} style={{ marginBottom: '1.5rem', paddingBottom: '1.25rem', borderBottom: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#fff', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                    <UserPlus size={16} style={{ color: 'var(--primary)' }} />
                    Invite User to Workspace
                  </div>

                  {inviteError && (
                    <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#fca5a5', padding: '0.625rem', borderRadius: '6px', marginBottom: '0.75rem', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <AlertCircle size={14} />
                      <span>{inviteError}</span>
                    </div>
                  )}

                  {inviteSuccess && (
                    <div style={{ backgroundColor: 'rgba(34, 197, 94, 0.1)', border: '1px solid rgba(34, 197, 94, 0.3)', color: '#86efac', padding: '0.625rem', borderRadius: '6px', marginBottom: '0.75rem', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <CheckCircle size={14} />
                      <span>{inviteSuccess}</span>
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <input
                      type="email"
                      className="input-search"
                      placeholder="User email address..."
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      style={{ flex: 1, minWidth: '220px', paddingLeft: '0.75rem' }}
                      required
                    />

                    <select
                      value={inviteRole}
                      onChange={(e) => setInviteRole(e.target.value as 'ADMIN' | 'MEMBER')}
                      style={{
                        backgroundColor: 'var(--bg-input)',
                        color: 'var(--text-main)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '6px',
                        padding: '0.5rem 0.75rem',
                        fontSize: '0.8125rem',
                      }}
                    >
                      <option value="MEMBER">Member</option>
                      <option value="ADMIN">Admin</option>
                    </select>

                    <button type="submit" className="btn btn-primary" disabled={inviteLoading || !inviteEmail.trim()}>
                      {inviteLoading && <Loader2 size={16} className="animate-spin" />}
                      <span>Add Member</span>
                    </button>
                  </div>
                </form>
              )}

              {/* Members List Table */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {activeWorkspace.members.map((member) => {
                  const isSelf = member.user_id === user.id;
                  const canManageThisMember = isOwnerOrAdmin && (!isSelf || activeWorkspaceRole === 'OWNER');

                  return (
                    <div
                      key={member.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '0.75rem 1rem',
                        backgroundColor: 'var(--bg-input)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.875rem', color: '#fff' }}>
                          {member.user?.email || `User #${member.user_id}`} {isSelf && '(You)'}
                        </div>
                        {member.user?.full_name && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            {member.user.full_name}
                          </div>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        {isOwnerOrAdmin && !isSelf && activeWorkspaceRole === 'OWNER' ? (
                          <select
                            value={member.role}
                            disabled={actionLoadingId === member.id}
                            onChange={(e) => handleRoleChange(member.id, e.target.value)}
                            style={{
                              backgroundColor: 'var(--bg-primary)',
                              color: member.role === 'OWNER' ? '#fde047' : member.role === 'ADMIN' ? 'var(--primary)' : 'var(--text-main)',
                              border: '1px solid var(--border-color)',
                              borderRadius: '6px',
                              padding: '0.375rem 0.625rem',
                              fontSize: '0.8125rem',
                              fontWeight: 600,
                            }}
                          >
                            <option value="MEMBER">MEMBER</option>
                            <option value="ADMIN">ADMIN</option>
                            <option value="OWNER">OWNER</option>
                          </select>
                        ) : (
                          <span
                            style={{
                              fontSize: '0.75rem',
                              padding: '0.25rem 0.5rem',
                              borderRadius: '4px',
                              backgroundColor: 'rgba(255, 255, 255, 0.05)',
                              color: member.role === 'OWNER' ? '#fde047' : member.role === 'ADMIN' ? 'var(--primary)' : 'var(--text-dim)',
                              fontWeight: 700,
                            }}
                          >
                            {member.role}
                          </span>
                        )}

                        {/* Remove / Leave Button */}
                        {(canManageThisMember || isSelf) && (
                          <button
                            onClick={() => handleRemoveMember(member.id, member.user?.email || 'this user')}
                            disabled={actionLoadingId === member.id}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: isSelf ? 'var(--text-muted)' : '#f87171',
                              cursor: 'pointer',
                              padding: '0.375rem',
                              borderRadius: '4px',
                            }}
                            title={isSelf ? 'Leave workspace' : 'Remove member'}
                          >
                            {actionLoadingId === member.id ? (
                              <Loader2 size={16} className="animate-spin" />
                            ) : (
                              <Trash2 size={16} />
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className="card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No active workspace selected.
          </div>
        )}
      </div>
    </div>
  );
};
