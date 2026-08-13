import React, { useState } from 'react';
import { authApi, User } from '../../api/auth';
import { Sparkles, Mail, Lock, Eye, EyeOff, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';

interface AuthModalProps {
  onAuthenticated: (user: User) => void;
}

type Mode = 'login' | 'register';

export const AuthModal: React.FC<AuthModalProps> = ({ onAuthenticated }) => {
  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [registrationSuccess, setRegistrationSuccess] = useState(false);

  // Client-side validation
  const validateForm = (): string | null => {
    const trimmedEmail = email.trim();
    if (!trimmedEmail) return 'Email is required.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) return 'Please enter a valid email address.';
    if (!password) return 'Password is required.';
    if (mode === 'register' && password.length < 8) return 'Password must be at least 8 characters.';
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    const trimmedEmail = email.trim().toLowerCase();

    try {
      if (mode === 'register') {
        // Register the user
        await authApi.register(trimmedEmail, password);
        // Immediately log in after successful registration
        await authApi.login(trimmedEmail, password);
        const user = await authApi.getMe();
        setPassword(''); // clear password from memory
        onAuthenticated(user);
      } else {
        await authApi.login(trimmedEmail, password);
        const user = await authApi.getMe();
        setPassword(''); // clear password from memory
        onAuthenticated(user);
      }
    } catch (err: any) {
      setPassword(''); // always clear password on error
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (err.response?.status === 409) {
        setError('An account with this email already exists.');
      } else if (err.response?.status === 401) {
        setError('Invalid email or password.');
      } else {
        setError('Something went wrong. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (newMode: Mode) => {
    setMode(newMode);
    setError(null);
    setPassword('');
    setRegistrationSuccess(false);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-primary)',
        padding: '1.5rem',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '420px',
        }}
      >
        {/* Logo / Brand */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 56,
              height: 56,
              borderRadius: '16px',
              background: 'linear-gradient(135deg, #4f46e5, #9333ea)',
              marginBottom: '1rem',
              boxShadow: '0 8px 32px rgba(99, 102, 241, 0.35)',
            }}
          >
            <Sparkles size={26} color="#fff" />
          </div>
          <h1
            style={{
              fontSize: '1.75rem',
              fontWeight: 800,
              color: '#fff',
              marginBottom: '0.25rem',
              letterSpacing: '-0.025em',
            }}
          >
            FireFlies AI
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Autonomous Meeting Intelligence Platform
          </p>
        </div>

        {/* Card */}
        <div
          className="card"
          style={{ padding: '2rem' }}
        >
          {/* Tab Switcher */}
          <div
            style={{
              display: 'flex',
              background: 'var(--bg-input)',
              borderRadius: '10px',
              padding: '4px',
              marginBottom: '1.75rem',
              border: '1px solid var(--border-color)',
            }}
          >
            {(['login', 'register'] as Mode[]).map((m) => (
              <button
                key={m}
                id={`auth-tab-${m}`}
                type="button"
                onClick={() => switchMode(m)}
                style={{
                  flex: 1,
                  padding: '0.5rem 0',
                  borderRadius: '7px',
                  border: 'none',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  background: mode === m
                    ? 'linear-gradient(135deg, #4f46e5, #7c3aed)'
                    : 'transparent',
                  color: mode === m ? '#fff' : 'var(--text-muted)',
                  boxShadow: mode === m ? '0 2px 8px rgba(99,102,241,0.4)' : 'none',
                }}
              >
                {m === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            ))}
          </div>

          {/* Registration success banner */}
          {registrationSuccess && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: 'rgba(34, 197, 94, 0.1)',
                border: '1px solid rgba(34, 197, 94, 0.3)',
                color: '#86efac',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                fontSize: '0.875rem',
                marginBottom: '1.25rem',
              }}
            >
              <CheckCircle2 size={16} />
              Account created! Please sign in.
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div
              id="auth-error"
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.5rem',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#fca5a5',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                fontSize: '0.875rem',
                marginBottom: '1.25rem',
              }}
            >
              <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '0.125rem' }} />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} noValidate>
            {/* Email Field */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label
                htmlFor="auth-email"
                style={{
                  display: 'block',
                  fontSize: '0.8125rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: '0.5rem',
                }}
              >
                Email Address
              </label>
              <div style={{ position: 'relative' }}>
                <Mail
                  size={16}
                  style={{
                    position: 'absolute',
                    left: '0.875rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)',
                    pointerEvents: 'none',
                  }}
                />
                <input
                  id="auth-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  disabled={loading}
                  style={{
                    width: '100%',
                    padding: '0.75rem 0.875rem 0.75rem 2.5rem',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '0.9375rem',
                    outline: 'none',
                    transition: 'border-color 0.2s ease',
                    boxSizing: 'border-box',
                    opacity: loading ? 0.6 : 1,
                  }}
                  onFocus={(e) => (e.target.style.borderColor = '#4f46e5')}
                  onBlur={(e) => (e.target.style.borderColor = 'var(--border-color)')}
                />
              </div>
            </div>

            {/* Password Field */}
            <div style={{ marginBottom: '1.75rem' }}>
              <label
                htmlFor="auth-password"
                style={{
                  display: 'block',
                  fontSize: '0.8125rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  marginBottom: '0.5rem',
                }}
              >
                Password {mode === 'register' && <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(min 8 chars)</span>}
              </label>
              <div style={{ position: 'relative' }}>
                <Lock
                  size={16}
                  style={{
                    position: 'absolute',
                    left: '0.875rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)',
                    pointerEvents: 'none',
                  }}
                />
                <input
                  id="auth-password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  disabled={loading}
                  style={{
                    width: '100%',
                    padding: '0.75rem 2.75rem 0.75rem 2.5rem',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '0.9375rem',
                    outline: 'none',
                    transition: 'border-color 0.2s ease',
                    boxSizing: 'border-box',
                    opacity: loading ? 0.6 : 1,
                  }}
                  onFocus={(e) => (e.target.style.borderColor = '#4f46e5')}
                  onBlur={(e) => (e.target.style.borderColor = 'var(--border-color)')}
                />
                <button
                  type="button"
                  id="auth-toggle-password"
                  tabIndex={-1}
                  onClick={() => setShowPassword((v) => !v)}
                  style={{
                    position: 'absolute',
                    right: '0.875rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    padding: 0,
                  }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              id="auth-submit"
              type="submit"
              disabled={loading}
              className="btn btn-primary"
              style={{
                width: '100%',
                justifyContent: 'center',
                padding: '0.875rem',
                fontSize: '0.9375rem',
                fontWeight: 700,
                opacity: loading ? 0.7 : 1,
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  {mode === 'login' ? 'Signing in...' : 'Creating account...'}
                </>
              ) : (
                mode === 'login' ? 'Sign In' : 'Create Account'
              )}
            </button>
          </form>

          {/* Mode switch link */}
          <p
            style={{
              textAlign: 'center',
              fontSize: '0.8125rem',
              color: 'var(--text-muted)',
              marginTop: '1.25rem',
            }}
          >
            {mode === 'login' ? (
              <>
                Don't have an account?{' '}
                <button
                  id="auth-switch-to-register"
                  type="button"
                  onClick={() => switchMode('register')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--primary)',
                    fontWeight: 600,
                    cursor: 'pointer',
                    fontSize: '0.8125rem',
                    padding: 0,
                  }}
                >
                  Create one
                </button>
              </>
            ) : (
              <>
                Already have an account?{' '}
                <button
                  id="auth-switch-to-login"
                  type="button"
                  onClick={() => switchMode('login')}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--primary)',
                    fontWeight: 600,
                    cursor: 'pointer',
                    fontSize: '0.8125rem',
                    padding: 0,
                  }}
                >
                  Sign in
                </button>
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  );
};
