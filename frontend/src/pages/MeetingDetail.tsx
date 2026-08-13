import React, { useEffect, useState } from 'react';
import { meetingsApi } from '../api/meetings';
import { MeetingIntelligence } from '../types/meeting';
import { StatusBadge } from '../components/common/StatusBadge';
import { ProcessingStateView } from '../components/meetings/ProcessingStateView';
import { SummaryTab } from '../components/intelligence/SummaryTab';
import { ActionItemsTab } from '../components/intelligence/ActionItemsTab';
import { ChaptersTab } from '../components/intelligence/ChaptersTab';
import { TranscriptTab } from '../components/intelligence/TranscriptTab';
import { ArrowLeft, Calendar, Clock, FileAudio, Trash2, Sparkles, CheckSquare, Bookmark, FileText, Loader2, AlertCircle } from 'lucide-react';

interface MeetingDetailProps {
  meetingId: number;
  onBack: () => void;
}

export const MeetingDetail: React.FC<MeetingDetailProps> = ({ meetingId, onBack }) => {
  const [data, setData] = useState<MeetingIntelligence | null>(null);
  const [activeTab, setActiveTab] = useState<'summary' | 'action_items' | 'chapters' | 'transcript'>('summary');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchIntelligence = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await meetingsApi.getIntelligence(meetingId);
      setData(res);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to load meeting details.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntelligence();
  }, [meetingId]);

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this meeting and all associated data?')) {
      try {
        await meetingsApi.deleteMeeting(meetingId);
        onBack();
      } catch (err: any) {
        alert('Failed to delete meeting');
      }
    }
  };

  if (loading) {
    return (
      <div className="page-container" style={{ padding: '6rem 0', textAlign: 'center', color: 'var(--text-muted)' }}>
        <Loader2 size={40} className="animate-spin" style={{ color: 'var(--primary)', marginBottom: '1rem' }} />
        <div>Loading meeting intelligence payload...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="page-container">
        <button className="btn btn-secondary" onClick={onBack} style={{ marginBottom: '1.5rem' }}>
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#fca5a5',
            padding: '1.5rem',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
          }}
        >
          <AlertCircle size={24} />
          <div>
            <div style={{ fontWeight: 700, fontSize: '1rem' }}>Meeting Not Found</div>
            <div style={{ fontSize: '0.875rem' }}>{error || 'Unable to retrieve meeting data.'}</div>
          </div>
        </div>
      </div>
    );
  }

  const { meeting, summary, action_items, chapters, participants, transcript_segments } = data;
  const isCompleted = meeting.status === 'completed';

  const formatDate = (isoStr: string) => {
    try {
      return new Date(isoStr).toLocaleDateString('en-US', {
        weekday: 'short',
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
    <div className="page-container">
      {/* Back Button & Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <button className="btn btn-secondary" onClick={onBack}>
          <ArrowLeft size={16} /> Back to Dashboard
        </button>

        <button className="btn btn-secondary" onClick={handleDelete} style={{ color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.3)' }}>
          <Trash2 size={16} /> Delete Meeting
        </button>
      </div>

      {/* Meeting Title Banner */}
      <div className="card" style={{ marginBottom: '1.5rem', padding: '1.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <h1 style={{ fontSize: '1.625rem', fontWeight: 800, color: '#fff', lineHeight: 1.2, marginBottom: '0.5rem' }}>
              {meeting.title}
            </h1>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.25rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                <Calendar size={14} /> {formatDate(meeting.recorded_at)}
              </span>
              {meeting.duration_ms && (
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                  <Clock size={14} /> {formatDuration(meeting.duration_ms)}
                </span>
              )}
              {meeting.audio_filename && (
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', color: 'var(--primary)' }}>
                  <FileAudio size={14} /> {meeting.audio_filename}
                </span>
              )}
            </div>
          </div>

          <StatusBadge status={meeting.status} />
        </div>
      </div>

      {/* Processing Workflow Stepper (Shown if processing is incomplete) */}
      {!isCompleted && (
        <ProcessingStateView
          meeting={meeting}
          onStatusUpdated={() => fetchIntelligence()}
        />
      )}

      {/* Navigation Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-color)', marginBottom: '1.5rem', paddingBottom: '0.5rem' }}>
        <button
          className={`nav-item ${activeTab === 'summary' ? 'active' : ''}`}
          onClick={() => setActiveTab('summary')}
          style={{ width: 'auto', padding: '0.625rem 1.25rem' }}
        >
          <Sparkles size={16} /> Summary
        </button>

        <button
          className={`nav-item ${activeTab === 'action_items' ? 'active' : ''}`}
          onClick={() => setActiveTab('action_items')}
          style={{ width: 'auto', padding: '0.625rem 1.25rem' }}
        >
          <CheckSquare size={16} /> Action Items ({action_items.length})
        </button>

        <button
          className={`nav-item ${activeTab === 'chapters' ? 'active' : ''}`}
          onClick={() => setActiveTab('chapters')}
          style={{ width: 'auto', padding: '0.625rem 1.25rem' }}
        >
          <Bookmark size={16} /> Chapters ({chapters.length})
        </button>

        <button
          className={`nav-item ${activeTab === 'transcript' ? 'active' : ''}`}
          onClick={() => setActiveTab('transcript')}
          style={{ width: 'auto', padding: '0.625rem 1.25rem' }}
        >
          <FileText size={16} /> Transcript ({transcript_segments.length})
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === 'summary' && <SummaryTab summary={summary} />}
      {activeTab === 'action_items' && <ActionItemsTab actionItems={action_items} participants={participants} />}
      {activeTab === 'chapters' && <ChaptersTab chapters={chapters} />}
      {activeTab === 'transcript' && <TranscriptTab segments={transcript_segments} participants={participants} />}
    </div>
  );
};
