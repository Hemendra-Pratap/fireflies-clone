import React from 'react';
import { Meeting } from '../../types/meeting';
import { StatusBadge } from '../common/StatusBadge';
import { Calendar, Clock, FileAudio, ChevronRight } from 'lucide-react';

interface MeetingCardProps {
  meeting: Meeting;
  onClick: () => void;
}

export const MeetingCard: React.FC<MeetingCardProps> = ({ meeting, onClick }) => {
  const formatDate = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  const formatDuration = (ms: number | null) => {
    if (!ms) return 'N/A';
    const totalSec = Math.floor(ms / 1000);
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins}m ${secs}s`;
  };

  return (
    <div
      className="card"
      onClick={onClick}
      style={{
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        position: 'relative',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <h3
          style={{
            fontSize: '1.125rem',
            fontWeight: 600,
            color: '#fff',
            lineHeight: 1.3,
            paddingRight: '1rem',
          }}
        >
          {meeting.title}
        </h3>
        <StatusBadge status={meeting.status} />
      </div>

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '1.25rem',
          fontSize: '0.8125rem',
          color: 'var(--text-muted)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
          <Calendar size={14} />
          <span>{formatDate(meeting.recorded_at)}</span>
        </div>

        {meeting.duration_ms && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
            <Clock size={14} />
            <span>{formatDuration(meeting.duration_ms)}</span>
          </div>
        )}

        {meeting.audio_filename && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', color: 'var(--primary)' }}>
            <FileAudio size={14} />
            <span>{meeting.audio_filename}</span>
          </div>
        )}
      </div>

      {meeting.error_message && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#fca5a5',
            padding: '0.5rem 0.75rem',
            borderRadius: '6px',
            fontSize: '0.75rem',
          }}
        >
          {meeting.error_message}
        </div>
      )}

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          color: 'var(--text-dim)',
          fontSize: '0.8125rem',
          fontWeight: 500,
          marginTop: '0.5rem',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          View Intelligence <ChevronRight size={16} />
        </span>
      </div>
    </div>
  );
};
