import React, { useState } from 'react';
import { User, authApi } from '../api/auth';
import { useWorkspace } from '../context/WorkspaceContext';
import {
  User as UserIcon,
  Lock,
  Building2,
  CheckCircle,
  AlertCircle,
  Loader2,
  KeyRound,
  ShieldCheck,
} from 'lucide-react';

interface SettingsPageProps {
  user: User;
  onUserUpdated: (updatedUser: User) => void;
  onNavigateToWorkspaces: () => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  user,
  onUserUpdated,
  onNavigateToWorkspaces,
}) => {
  const { activeWorkspace, activeWorkspaceRole } = useWorkspace();

  // Profile Form state
  const [fullName, setFullName] = useState(user.full_name || '');
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);

  // Password Form state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileLoading(true);
    setProfileError(null);
    setProfileSuccess(null);

    try {
      const updated = await authApi.updateProfile(fullName.trim());
      onUserUpdated(updated);
      setProfileSuccess('Profile updated successfully.');
    } catch (err: any) {
      setProfileError(err.response?.data?.detail || 'Failed to update profile.');
    } finally {
      setProfileLoading(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('New password and confirmation do not match.');
      return;
    }

    setPasswordLoading(true);
    setPasswordError(null);
    setPasswordSuccess(null);

    try {
      await authApi.changePassword(currentPassword, newPassword);
      setPasswordSuccess('Password changed successfully.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setPasswordError(err.response?.data?.detail || 'Failed to change password.');
    } finally {
      setPasswordLoading(false);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '840px', margin: '0 auto' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fff' }}>Account & Settings</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
          Manage your personal profile, security credentials, and active workspace overview.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
        {/* Profile Card */}
        <div className="card" style={{ padding: '1.5rem' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.625rem',
              marginBottom: '1.25rem',
              paddingBottom: '0.875rem',
              borderBottom: '1px solid var(--border-color)',
            }}
          >
            <UserIcon size={20} style={{ color: 'var(--primary)' }} />
            <h2 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#fff' }}>
              Personal Profile
            </h2>
          </div>

          {profileError && (
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
              <span>{profileError}</span>
            </div>
          )}

          {profileSuccess && (
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
              <span>{profileSuccess}</span>
            </div>
          )}

          <form onSubmit={handleUpdateProfile} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.375rem' }}>
                Email Address
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type="email"
                  value={user.email}
                  disabled
                  style={{
                    width: '100%',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '6px',
                    padding: '0.625rem 0.75rem 0.625rem 2.25rem',
                    color: 'var(--text-muted)',
                    fontSize: '0.875rem',
                    cursor: 'not-allowed',
                  }}
                />
                <Lock
                  size={14}
                  style={{
                    position: 'absolute',
                    left: '0.75rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-dim)',
                  }}
                />
              </div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '0.25rem', display: 'block' }}>
                Email address is locked to your authenticated account credentials.
              </span>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#fff', marginBottom: '0.375rem' }}>
                Full Display Name
              </label>
              <input
                type="text"
                className="input-search"
                placeholder="e.g. Jane Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                style={{ width: '100%', paddingLeft: '0.75rem' }}
              />
            </div>

            <div>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={profileLoading}
                style={{ padding: '0.625rem 1.25rem' }}
              >
                {profileLoading && <Loader2 size={16} className="animate-spin" />}
                <span>Save Profile</span>
              </button>
            </div>
          </form>
        </div>

        {/* Security & Password Card */}
        <div className="card" style={{ padding: '1.5rem' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.625rem',
              marginBottom: '1.25rem',
              paddingBottom: '0.875rem',
              borderBottom: '1px solid var(--border-color)',
            }}
          >
            <KeyRound size={20} style={{ color: '#f59e0b' }} />
            <h2 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#fff' }}>
              Security & Password
            </h2>
          </div>

          {passwordError && (
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
              <span>{passwordError}</span>
            </div>
          )}

          {passwordSuccess && (
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
              <span>{passwordSuccess}</span>
            </div>
          )}

          <form onSubmit={handleChangePassword} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#fff', marginBottom: '0.375rem' }}>
                Current Password
              </label>
              <input
                type="password"
                className="input-search"
                placeholder="Enter current password..."
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                style={{ width: '100%', paddingLeft: '0.75rem' }}
                required
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#fff', marginBottom: '0.375rem' }}>
                  New Password
                </label>
                <input
                  type="password"
                  className="input-search"
                  placeholder="Min 8 characters..."
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  style={{ width: '100%', paddingLeft: '0.75rem' }}
                  required
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#fff', marginBottom: '0.375rem' }}>
                  Confirm New Password
                </label>
                <input
                  type="password"
                  className="input-search"
                  placeholder="Re-enter new password..."
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  style={{ width: '100%', paddingLeft: '0.75rem' }}
                  required
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={passwordLoading || !currentPassword || !newPassword || !confirmPassword}
                style={{ padding: '0.625rem 1.25rem' }}
              >
                {passwordLoading && <Loader2 size={16} className="animate-spin" />}
                <span>Change Password</span>
              </button>
            </div>
          </form>
        </div>

        {/* Active Workspace Card */}
        {activeWorkspace && (
          <div className="card" style={{ padding: '1.5rem' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '1rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                <Building2 size={20} style={{ color: '#818cf8' }} />
                <div>
                  <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>
                    {activeWorkspace.name}
                  </h3>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Active Workspace • {activeWorkspace.members.length} member(s)
                  </span>
                </div>
              </div>

              <span
                style={{
                  fontSize: '0.75rem',
                  padding: '0.25rem 0.625rem',
                  borderRadius: '6px',
                  backgroundColor:
                    activeWorkspaceRole === 'OWNER'
                      ? 'rgba(234, 179, 8, 0.15)'
                      : activeWorkspaceRole === 'ADMIN'
                      ? 'rgba(99, 102, 241, 0.15)'
                      : 'rgba(148, 163, 184, 0.15)',
                  color:
                    activeWorkspaceRole === 'OWNER'
                      ? '#fde047'
                      : activeWorkspaceRole === 'ADMIN'
                      ? 'var(--primary)'
                      : 'var(--text-muted)',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                }}
              >
                <ShieldCheck size={14} />
                {activeWorkspaceRole}
              </span>
            </div>

            <button
              className="btn btn-secondary"
              onClick={onNavigateToWorkspaces}
              style={{ fontSize: '0.8125rem' }}
            >
              Manage Workspaces & Members
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
