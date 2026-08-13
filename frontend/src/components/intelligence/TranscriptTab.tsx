import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Participant, TranscriptSegment } from '../../types/meeting';
import { Search, User, Clock, Play } from 'lucide-react';

interface TranscriptTabProps {
  segments: TranscriptSegment[];
  participants: Participant[];
  currentTimeMs?: number;
  onSegmentClick?: (startTimeMs: number) => void;
}

const formatSegmentTime = (ms: number | null, isLongRecording: boolean): string => {
  if (ms === null || ms === undefined || isNaN(ms)) return '--:--';
  const totalSecs = Math.max(0, Math.floor(ms / 1000));
  const hrs = Math.floor(totalSecs / 3600);
  const mins = Math.floor((totalSecs % 3600) / 60);
  const secs = totalSecs % 60;

  if (hrs > 0 || isLongRecording) {
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

export const TranscriptTab: React.FC<TranscriptTabProps> = ({
  segments,
  participants,
  currentTimeMs,
  onSegmentClick,
}) => {
  const [filterText, setFilterText] = useState('');
  const activeRef = useRef<HTMLDivElement | null>(null);

  // Participant lookup map
  const participantMap = useMemo(() => {
    const map = new Map<number, Participant>();
    participants.forEach((p) => map.set(p.id, p));
    return map;
  }, [participants]);

  // Deterministically sort segments by sequence_number and start_time_ms
  const sortedSegments = useMemo(() => {
    if (!segments) return [];
    return [...segments].sort((a, b) => {
      if (a.sequence_number !== b.sequence_number) {
        return a.sequence_number - b.sequence_number;
      }
      return a.start_time_ms - b.start_time_ms;
    });
  }, [segments]);

  // Check if recording is long (>= 1 hour) for time formatting
  const isLongRecording = useMemo(() => {
    if (sortedSegments.length === 0) return false;
    const maxEndMs = sortedSegments[sortedSegments.length - 1].end_time_ms;
    return maxEndMs >= 3600000;
  }, [sortedSegments]);

  // Identify active segment based on audio currentTimeMs
  const activeSegmentId = useMemo(() => {
    if (currentTimeMs === undefined || currentTimeMs === null) return null;
    const match = sortedSegments.find(
      (s) => currentTimeMs >= s.start_time_ms && currentTimeMs <= s.end_time_ms
    );
    return match ? match.id : null;
  }, [currentTimeMs, sortedSegments]);

  // Auto-scroll active segment into view
  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [activeSegmentId]);

  const filteredSegments = useMemo(() => {
    if (!filterText.trim()) return sortedSegments;
    const lowerFilter = filterText.toLowerCase().trim();
    return sortedSegments.filter((seg) => {
      const p = seg.participant_id ? participantMap.get(seg.participant_id) : null;
      const speaker = (p?.display_name || p?.speaker_label || 'Speaker').toLowerCase();
      const text = seg.text.toLowerCase();
      return speaker.includes(lowerFilter) || text.includes(lowerFilter);
    });
  }, [sortedSegments, filterText, participantMap]);

  if (!segments || segments.length === 0) {
    return (
      <div className="card" style={{ padding: '2.5rem 2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-heading)', marginBottom: '0.5rem' }}>
          No Transcript Available
        </div>
        <div style={{ fontSize: '0.875rem' }}>
          Transcript segments will appear here once audio transcription completes.
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Transcript Filter Search Bar */}
      <div style={{ position: 'relative', maxWidth: '440px' }}>
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
          placeholder="Filter transcript dialogue or speaker..."
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          style={{ width: '100%' }}
        />
      </div>

      <div className="card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
        {filteredSegments.length > 0 ? (
          filteredSegments.map((seg) => {
            const p = seg.participant_id ? participantMap.get(seg.participant_id) : null;
            const speakerName = p?.display_name || p?.speaker_label || 'Speaker';
            const isActive = seg.id === activeSegmentId;

            return (
              <div
                key={seg.id}
                ref={isActive ? activeRef : null}
                onClick={() => {
                  if (onSegmentClick) {
                    onSegmentClick(seg.start_time_ms);
                  }
                }}
                style={{
                  display: 'flex',
                  gap: '1rem',
                  alignItems: 'flex-start',
                  padding: '0.875rem 1rem',
                  borderRadius: '8px',
                  backgroundColor: isActive ? 'rgba(99, 102, 241, 0.12)' : 'transparent',
                  borderLeft: isActive ? '4px solid var(--primary)' : '4px solid transparent',
                  cursor: onSegmentClick ? 'pointer' : 'default',
                  transition: 'all 0.2s ease',
                  boxShadow: isActive ? '0 2px 8px rgba(99, 102, 241, 0.2)' : 'none',
                }}
              >
                {/* Timestamp Badge */}
                <div
                  style={{
                    fontSize: '0.75rem',
                    fontFamily: 'var(--font-mono)',
                    color: isActive ? '#fff' : 'var(--text-dim)',
                    backgroundColor: isActive ? 'var(--primary)' : 'var(--bg-input)',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '4px',
                    marginTop: '0.125rem',
                    flexShrink: 0,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.375rem',
                    fontWeight: isActive ? 700 : 500,
                  }}
                  title="Click to play from this segment"
                >
                  {isActive ? <Play size={10} style={{ fill: '#fff' }} /> : <Clock size={10} />}
                  <span>{formatSegmentTime(seg.start_time_ms, isLongRecording)}</span>
                </div>

                {/* Speaker & Dialogue */}
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', marginBottom: '0.25rem' }}>
                    <User size={12} style={{ color: isActive ? '#818cf8' : 'var(--primary)' }} />
                    <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: isActive ? '#fff' : 'var(--primary)' }}>
                      {speakerName}
                    </span>
                  </div>

                  <p
                    style={{
                      fontSize: '0.9375rem',
                      color: isActive ? '#ffffff' : 'var(--text-main)',
                      lineHeight: 1.6,
                      fontWeight: isActive ? 500 : 400,
                    }}
                  >
                    {seg.text}
                  </p>
                </div>
              </div>
            );
          })
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem' }}>
            No transcript dialogue matching '{filterText}'.
          </div>
        )}
      </div>
    </div>
  );
};
