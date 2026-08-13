import React, { useEffect, useState } from 'react';
import { meetingsApi } from '../api/meetings';
import { Meeting } from '../types/meeting';
import { MeetingCard } from '../components/meetings/MeetingCard';
import { Loader2, Plus, Sparkles, Filter, AlertCircle } from 'lucide-react';

interface DashboardProps {
  searchQuery: string;
  onSelectMeeting: (meetingId: number) => void;
  onOpenUploadModal: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  searchQuery,
  onSelectMeeting,
  onOpenUploadModal,
}) => {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page] = useState(1);
  const [total, setTotal] = useState(0);

  const fetchMeetings = async () => {
    setLoading(true);
    setError(null);
    try {
      const filter = statusFilter === 'all' ? undefined : statusFilter;
      let res;
      if (searchQuery.trim()) {
        res = await meetingsApi.searchMeetings(searchQuery.trim(), page, 20, filter);
      } else {
        res = await meetingsApi.listMeetings(page, 20, filter);
      }
      setMeetings(res.items);
      setTotal(res.total);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to fetch meetings.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMeetings();
  }, [searchQuery, statusFilter, page]);

  return (
    <div className="page-container">
      {/* Hero Banner */}
      <div
        className="card"
        style={{
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.1))',
          borderColor: 'rgba(99, 102, 241, 0.3)',
          marginBottom: '2rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1.5rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--primary)', fontWeight: 700, fontSize: '0.875rem', marginBottom: '0.5rem' }}>
            <Sparkles size={16} /> Autonomous Intelligence Platform
          </div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fff', marginBottom: '0.5rem' }}>
            AI Meeting Intelligence Hub
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9375rem', maxWidth: '600px' }}>
            Upload audio recordings to extract speaker-segmented transcripts, executive summaries, action item checklists, and topic chapters.
          </p>
        </div>

        <button className="btn btn-primary" onClick={onOpenUploadModal} style={{ padding: '0.75rem 1.5rem', fontSize: '0.9375rem' }}>
          <Plus size={20} />
          <span>Upload New Meeting</span>
        </button>
      </div>

      {/* Filter Toolbar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Filter size={16} style={{ color: 'var(--text-muted)' }} />
          <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)', fontWeight: 500 }}>Filter Status:</span>
          {['all', 'completed', 'transcribed', 'uploaded', 'failed'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              style={{
                background: statusFilter === st ? 'var(--primary)' : 'var(--bg-input)',
                color: statusFilter === st ? '#fff' : 'var(--text-muted)',
                border: '1px solid var(--border-color)',
                padding: '0.375rem 0.75rem',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                textTransform: 'capitalize',
                transition: 'all 0.2s ease',
              }}
            >
              {st}
            </button>
          ))}
        </div>

        <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          Showing {meetings.length} of {total} meetings
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#fca5a5',
            padding: '1rem',
            borderRadius: '8px',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div style={{ padding: '4rem 0', textAlign: 'center', color: 'var(--text-muted)' }}>
          <Loader2 size={36} className="animate-spin" style={{ color: 'var(--primary)', marginBottom: '1rem' }} />
          <div>Loading meeting intelligence records...</div>
        </div>
      ) : meetings.length > 0 ? (
        /* Meeting Cards Grid */
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
            gap: '1.5rem',
          }}
        >
          {meetings.map((meeting) => (
            <MeetingCard
              key={meeting.id}
              meeting={meeting}
              onClick={() => onSelectMeeting(meeting.id)}
            />
          ))}
        </div>
      ) : (
        /* Empty State */
        <div
          className="card"
          style={{
            padding: '4rem 2rem',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem',
          }}
        >
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: '50%',
              backgroundColor: 'var(--primary-light)',
              color: 'var(--primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Sparkles size={28} />
          </div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>No Meetings Found</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', maxWidth: '400px' }}>
            {searchQuery
              ? `No meetings match '${searchQuery}'. Try clearing search or changing filters.`
              : 'Get started by creating a new meeting and uploading an audio recording.'}
          </p>
          <button className="btn btn-primary" onClick={onOpenUploadModal} style={{ marginTop: '0.5rem' }}>
            <Plus size={18} /> Create & Upload Meeting
          </button>
        </div>
      )}
    </div>
  );
};
