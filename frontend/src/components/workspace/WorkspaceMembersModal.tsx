import React, { useState } from 'react';
import { useWorkspace } from '../../context/WorkspaceContext';
import { X, Users, UserPlus, Loader2, AlertCircle, CheckCircle } from 'lucide-react';

interface WorkspaceMembersModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const WorkspaceMembersModal: React.FC<WorkspaceMembersModalProps> = ({ isOpen, onClose }) => {
  const { activeWorkspace, activeWorkspaceRole, addMember } = useWorkspace();
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<'ADMIN' | 'MEMBER'>('MEMBER');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  if (!isOpen || !activeWorkspace) return null;

  const isOwnerOrAdmin = activeWorkspaceRole === 'OWNER' || activeWorkspaceRole === 'ADMIN';

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setError('User email is required.');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await addMember(activeWorkspace.id, email.trim(), role);
      setSuccess(`User ${email.trim()} added as ${role} successfully.`);
      setEmail('');
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to add workspace member.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1100,
      }}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '520px',
          padding: '1.75rem',
          position: 'relative',
        }}
      >
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '1rem',
            right: '1rem',
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
          }}
        >
          <X size={20} />
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '0.5rem' }}>
          <Users size={24} style={{ color: 'var(--primary)' }} />
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>
            {activeWorkspace.name} — Members
          </h2>
        </div>

        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
          Workspace members have access to meetings recorded within this workspace.
        </p>

        {error && (
          <div
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#fca5a5',
              padding: '0.75rem',
              borderRadius: '6px',
              marginBottom: '1rem',
              fontSize: '0.8125rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div
            style={{
              backgroundColor: 'rgba(34, 197, 94, 0.1)',
              border: '1px solid rgba(34, 197, 94, 0.3)',
              color: '#86efac',
              padding: '0.75rem',
              borderRadius: '6px',
              marginBottom: '1rem',
              fontSize: '0.8125rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <CheckCircle size={16} />
            <span>{success}</span>
          </div>
        )}

        {/* Member Invitation Form (Owner / Admin only) */}
        {isOwnerOrAdmin ? (
          <form onSubmit={handleAddMember} style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#fff', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <UserPlus size={16} style={{ color: 'var(--primary)' }} />
              Add Member to Workspace
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <input
                type="email"
                className="input-search"
                placeholder="User email address..."
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{ flex: 1, minWidth: '200px', paddingLeft: '0.75rem' }}
              />

              <select
                value={role}
                onChange={(e) => setRole(e.target.value as 'ADMIN' | 'MEMBER')}
                style={{
                  backgroundColor: 'var(--bg-input)',
                  color: 'var(--text-main)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  padding: '0.5rem',
                  fontSize: '0.8125rem',
                }}
              >
                <option value="MEMBER">Member</option>
                <option value="ADMIN">Admin</option>
              </select>

              <button type="submit" className="btn btn-primary" disabled={loading || !email.trim()}>
                {loading && <Loader2 size={16} className="animate-spin" />}
                <span>Add</span>
              </button>
            </div>
          </form>
        ) : (
          <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1rem', fontStyle: 'italic' }}>
            Only workspace Owners and Admins can invite new members.
          </div>
        )}

        {/* Existing Member List */}
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>
            Current Members ({activeWorkspace.members.length})
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '220px', overflowY: 'auto' }}>
            {activeWorkspace.members.map((member) => (
              <div
                key={member.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.625rem 0.75rem',
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  fontSize: '0.8125rem',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, color: '#fff' }}>
                    {member.user?.email || `User #${member.user_id}`}
                  </div>
                </div>

                <span
                  style={{
                    fontSize: '0.6875rem',
                    padding: '0.125rem 0.5rem',
                    borderRadius: '4px',
                    backgroundColor:
                      member.role === 'OWNER'
                        ? 'rgba(234, 179, 8, 0.15)'
                        : member.role === 'ADMIN'
                        ? 'rgba(99, 102, 241, 0.15)'
                        : 'rgba(148, 163, 184, 0.15)',
                    color:
                      member.role === 'OWNER'
                        ? '#fde047'
                        : member.role === 'ADMIN'
                        ? 'var(--primary)'
                        : 'var(--text-muted)',
                    fontWeight: 700,
                  }}
                >
                  {member.role}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
