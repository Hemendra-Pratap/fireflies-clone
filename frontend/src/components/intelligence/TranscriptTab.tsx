import React, { useState } from 'react';
import { Participant, TranscriptSegment } from '../../types/meeting';
import { Search, User, Clock } from 'lucide-react';

interface TranscriptTabProps {
  segments: TranscriptSegment[];
  participants: Participant[];
}

export const TranscriptTab: React.FC<TranscriptTabProps> = ({ segments, participants }) => {
  const [filterText, setFilterText] = useState('');

  const participantMap = new Map<number, Participant>();
  participants.forEach((p) => participantMap.set(p.id, p));

  const formatTime = (ms: number) => {
    const totalSec = Math.floor(ms / 1000);
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const filteredSegments = segments.filter((seg) => {
    if (!filterText.trim()) return true;
    const p = seg.participant_id ? participantMap.get(seg.participant_id) : null;
    const speaker = p?.display_name || p?.speaker_label || 'Unknown';
    const matchText = `${speaker} ${seg.text}`.toLowerCase();
    return matchText.includes(filterText.toLowerCase());
  });

  if (!segments || segments.length === 0) {
    return (
      <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        No transcript segments available.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Transcript Filter Search Bar */}
      <div style={{ position: 'relative', maxWidth: '400px' }}>
        <Search
          size={16}
          style={{
            position: 'absolute',
            left: '0.75rem',
            top: '50%',
            transform: 'translateY(-50%)',
            color: 'var(--text-muted)',
          }}
        />
        <input
          type="text"
          className="input-search"
          placeholder="Filter transcript dialogue..."
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          style={{ width: '100%' }}
        />
      </div>

      <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {filteredSegments.length > 0 ? (
          filteredSegments.map((seg) => {
            const p = seg.participant_id ? participantMap.get(seg.participant_id) : null;
            const speakerName = p?.display_name || p?.speaker_label || 'Speaker';

            return (
              <div key={seg.id} style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                <div
                  style={{
                    fontSize: '0.75rem',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-dim)',
                    backgroundColor: 'var(--bg-input)',
                    padding: '0.2rem 0.5rem',
                    borderRadius: '4px',
                    marginTop: '0.125rem',
                    flexShrink: 0,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                  }}
                >
                  <Clock size={10} />
                  <span>{formatTime(seg.start_time_ms)}</span>
                </div>

                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', marginBottom: '0.25rem' }}>
                    <User size={12} style={{ color: 'var(--primary)' }} />
                    <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--primary)' }}>
                      {speakerName}
                    </span>
                  </div>

                  <p style={{ fontSize: '0.9375rem', color: 'var(--text-main)', lineHeight: 1.6 }}>
                    {seg.text}
                  </p>
                </div>
              </div>
            );
          })
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1rem' }}>
            No transcript dialogue matching '{filterText}'.
          </div>
        )}
      </div>
    </div>
  );
};
