import React from 'react';
import { Summary } from '../../types/meeting';
import { Sparkles, CheckCircle } from 'lucide-react';

interface SummaryTabProps {
  summary: Summary | null;
}

export const SummaryTab: React.FC<SummaryTabProps> = ({ summary }) => {
  if (!summary) {
    return (
      <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        No summary available yet for this meeting.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Overview Card */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--primary)', fontWeight: 700, fontSize: '1rem', marginBottom: '0.75rem' }}>
          <Sparkles size={18} /> Executive Summary
        </div>
        <p style={{ color: 'var(--text-main)', fontSize: '0.9375rem', lineHeight: 1.6 }}>
          {summary.overview}
        </p>
      </div>

      {/* Key Discussion Points */}
      <div className="card">
        <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', marginBottom: '1rem' }}>
          Key Discussion Points
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {summary.key_points && summary.key_points.length > 0 ? (
            summary.key_points.map((point, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                <CheckCircle size={16} style={{ color: 'var(--primary)', marginTop: '0.2rem', flexShrink: 0 }} />
                <span style={{ fontSize: '0.875rem', color: 'var(--text-main)' }}>{point}</span>
              </div>
            ))
          ) : (
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>No key points extracted.</p>
          )}
        </div>
      </div>
    </div>
  );
};
