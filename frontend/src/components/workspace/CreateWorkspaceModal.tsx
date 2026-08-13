import React, { useState } from 'react';
import { useWorkspace } from '../../context/WorkspaceContext';
import { X, Building2, Loader2, AlertCircle } from 'lucide-react';

interface CreateWorkspaceModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CreateWorkspaceModal: React.FC<CreateWorkspaceModalProps> = ({ isOpen, onClose }) => {
  const { createWorkspace } = useWorkspace();
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Workspace name is required.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await createWorkspace(name.trim());
      setName('');
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to create workspace.';
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
          maxWidth: '440px',
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

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', marginBottom: '1rem' }}>
          <Building2 size={24} style={{ color: 'var(--primary)' }} />
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>Create Workspace</h2>
        </div>

        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
          Workspaces allow team members to collaborate on meetings and intelligence reports securely.
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

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1.25rem' }}>
            <label
              style={{
                display: 'block',
                fontSize: '0.8125rem',
                fontWeight: 600,
                color: 'var(--text-main)',
                marginBottom: '0.375rem',
              }}
            >
              Workspace Name
            </label>
            <input
              type="text"
              className="input-search"
              placeholder="e.g. Engineering Team, Marketing"
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={{ width: '100%', paddingLeft: '0.75rem' }}
              autoFocus
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading || !name.trim()}>
              {loading && <Loader2 size={16} className="animate-spin" />}
              <span>Create Workspace</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
