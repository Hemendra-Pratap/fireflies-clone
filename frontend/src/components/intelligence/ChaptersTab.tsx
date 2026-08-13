import React from 'react';
import { Chapter } from '../../types/meeting';
import { Clock } from 'lucide-react';

interface ChaptersTabProps {
  chapters: Chapter[];
}

export const ChaptersTab: React.FC<ChaptersTabProps> = ({ chapters }) => {
  const formatTime = (ms: number | null) => {
    if (ms === null || ms === undefined) return '—';
    const totalSec = Math.floor(ms / 1000);
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (!chapters || chapters.length === 0) {
    return (
      <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        No topic chapters generated for this meeting.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {chapters.map((chapter) => (
        <div key={chapter.id} className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: '50%',
                  backgroundColor: 'var(--primary-light)',
                  color: 'var(--primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                }}
              >
                {chapter.sequence_number}
              </span>
              <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-heading)' }}>{chapter.title}</h4>
            </div>

            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.375rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                color: 'var(--primary)',
                backgroundColor: 'var(--bg-input)',
                padding: '0.25rem 0.625rem',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                fontFamily: 'var(--font-mono)',
              }}
            >
              <Clock size={12} />
              <span>
                {formatTime(chapter.start_time_ms)} - {formatTime(chapter.end_time_ms)}
              </span>
            </div>
          </div>

          {chapter.summary && (
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', lineHeight: 1.5, paddingLeft: '2rem' }}>
              {chapter.summary}
            </p>
          )}
        </div>
      ))}
    </div>
  );
};
