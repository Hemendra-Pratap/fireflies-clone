import React, { useEffect, useState, useRef } from 'react';
import { meetingsApi } from '../api/meetings';
import { Meeting } from '../types/meeting';
import { MeetingCard } from '../components/meetings/MeetingCard';
import { UpcomingMeetings } from '../components/calendar/UpcomingMeetings';
import { useWorkspace } from '../context/WorkspaceContext';
import { Loader2, Plus, Sparkles, Filter, AlertCircle, Calendar, FileText } from 'lucide-react';

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
  const { activeWorkspace } = useWorkspace();
  const [activeTab, setActiveTab] = useState<'recordings' | 'upcoming'>('recordings');
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState(searchQuery);

  // Debounce search query changes
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Reset page to 1 & clear stale meetings when active workspace, search, or status filter changes
  useEffect(() => {
    setPage(1);
    setMeetings([]);
  }, [activeWorkspace?.id, debouncedSearchQuery, statusFilter]);

  const fetchMeetings = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError(null);
    try {
      const filter = statusFilter === 'all' ? undefined : statusFilter;
      const wsId = activeWorkspace?.id;
      let res;
      if (debouncedSearchQuery.trim()) {
        res = await meetingsApi.searchMeetings(debouncedSearchQuery.trim(), page, 20, filter, wsId);
      } else {
        res = await meetingsApi.listMeetings(page, 20, filter, wsId);
      }
      setMeetings(res.items);
      setTotal(res.total);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to fetch meetings.';
      setError(msg);
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'recordings') {
      fetchMeetings(true);
    }
  }, [activeWorkspace?.id, debouncedSearchQuery, statusFilter, page, activeTab]);

  // Gentle polling only when there are in-progress processing meetings
  const hasInProgressRef = useRef(false);
  hasInProgressRef.current = meetings.some((m) =>
    ['created', 'uploaded', 'transcribing', 'transcribed', 'analyzing'].includes(m.status)
  );

  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval> | null = null;
    if (activeTab === 'recordings' && hasInProgressRef.current) {
      intervalId = setInterval(() => {
        fetchMeetings(false);
      }, 5000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [meetings, activeTab]);

  const pageSize = 20;
  const totalPages = Math.ceil(total / pageSize) || 1;

  const filterStatuses = [
    'all',
    'created',
    'uploaded',
    'transcribing',
    'transcribed',
    'analyzing',
    'completed',
    'failed',
  ];

  return (
    <div className="page-container">
      {/* Hero Banner */}
      <div
        className="card"
        style={{
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.1))',
          borderColor: 'rgba(99, 102, 241, 0.3)',
          marginBottom: '1.5rem',
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
            Connect Google Calendar to sync upcoming scheduled meetings or upload audio recordings to extract speaker-segmented transcripts, executive summaries, action item checklists, and topic chapters.
          </p>
        </div>

        <button className="btn btn-primary" onClick={onOpenUploadModal} style={{ padding: '0.75rem 1.5rem', fontSize: '0.9375rem' }}>
          <Plus size={20} />
          <span>Upload New Meeting</span>
        </button>
      </div>

      {/* Main Dashboard Navigation Tabs (Recordings vs Upcoming Meetings) */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', marginBottom: '1.5rem', paddingBottom: '0.5rem' }}>
        <button
          className={`nav-item ${activeTab === 'recordings' ? 'active' : ''}`}
          onClick={() => setActiveTab('recordings')}
          style={{ width: 'auto', padding: '0.625rem 1.25rem' }}
        >
          <FileText size={16} /> All Meetings & Recordings ({total})
        </button>

        <button
          className={`nav-item ${activeTab === 'upcoming' ? 'active' : ''}`}
          onClick={() => setActiveTab('upcoming')}
          style={{ width: 'auto', padding: '0.625rem 1.25rem' }}
        >
          <Calendar size={16} /> Upcoming Scheduled Meetings
        </button>
      </div>

      {activeTab === 'upcoming' && activeWorkspace && (
        <UpcomingMeetings
          workspaceId={activeWorkspace.id}
          onSelectMeeting={onSelectMeeting}
        />
      )}

      {activeTab === 'recordings' && (
        <>
          {/* Filter Toolbar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <Filter size={16} style={{ color: 'var(--text-muted)' }} />
              <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)', fontWeight: 500 }}>Filter Status:</span>
              {filterStatuses.map((st) => (
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
            <>
              {/* Meeting Cards Grid */}
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

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem', marginTop: '2rem' }}>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1 || loading}
                    style={{ fontSize: '0.875rem' }}
                  >
                    Previous
                  </button>
                  <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                    Page {page} of {totalPages}
                  </span>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages || loading}
                    style={{ fontSize: '0.875rem' }}
                  >
                    Next
                  </button>
                </div>
              )}
            </>
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
                {debouncedSearchQuery
                  ? `No meetings match '${debouncedSearchQuery}'. Try clearing search or changing filters.`
                  : 'Get started by creating a new meeting and uploading an audio recording.'}
              </p>
              <button className="btn btn-primary" onClick={onOpenUploadModal} style={{ marginTop: '0.5rem' }}>
                <Plus size={18} /> Create & Upload Meeting
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};
