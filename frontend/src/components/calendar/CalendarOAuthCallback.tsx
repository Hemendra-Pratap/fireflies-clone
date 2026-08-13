import React, { useEffect, useState } from 'react';
import { calendarApi } from '../../api/calendar';
import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

interface CalendarOAuthCallbackProps {
  onComplete: () => void;
}

export const CalendarOAuthCallback: React.FC<CalendarOAuthCallbackProps> = ({ onComplete }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');

    if (!code || !state) {
      setError('Missing authorization code or state token from Google OAuth redirect.');
      setLoading(false);
      return;
    }

    calendarApi
      .handleCallback(code, state)
      .then(() => {
        setSuccess(true);
        setTimeout(() => {
          onComplete();
        }, 1500);
      })
      .catch((err) => {
        const msg = err.response?.data?.detail || 'Failed to authorize Google Calendar connection.';
        setError(msg);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [onComplete]);

  return (
    <div className="page-container" style={{ padding: '6rem 0', textAlign: 'center' }}>
      <div className="card" style={{ maxWidth: '480px', margin: '0 auto', padding: '2.5rem 2rem' }}>
        {loading && (
          <div style={{ color: 'var(--text-muted)' }}>
            <Loader2 size={40} className="animate-spin" style={{ color: 'var(--primary)', marginBottom: '1rem' }} />
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff', marginBottom: '0.5rem' }}>
              Connecting Google Calendar...
            </h2>
            <p style={{ fontSize: '0.875rem' }}>Verifying OAuth authorization and ingesting upcoming meetings.</p>
          </div>
        )}

        {success && (
          <div style={{ color: '#4ade80' }}>
            <CheckCircle2 size={48} style={{ marginBottom: '1rem' }} />
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff', marginBottom: '0.5rem' }}>
              Calendar Connected!
            </h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              Redirecting back to your upcoming meetings...
            </p>
          </div>
        )}

        {error && (
          <div style={{ color: '#fca5a5' }}>
            <AlertCircle size={48} style={{ color: '#ef4444', marginBottom: '1rem' }} />
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff', marginBottom: '0.5rem' }}>
              Connection Failed
            </h2>
            <p style={{ fontSize: '0.875rem', marginBottom: '1.5rem' }}>{error}</p>
            <button className="btn btn-primary" onClick={onComplete}>
              Return to Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
