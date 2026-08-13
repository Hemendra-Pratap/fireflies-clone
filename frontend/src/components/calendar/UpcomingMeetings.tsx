import React, { useEffect, useState } from 'react';
import { calendarApi } from '../../api/calendar';
import { CalendarEventRead, CalendarStatusResponse } from '../../types/calendar';
import { Calendar, Clock, Video, RefreshCw, CheckCircle2, AlertCircle, Loader2, Users, ExternalLink, Link2 } from 'lucide-react';

interface UpcomingMeetingsProps {
  workspaceId: number;
  onSelectMeeting?: (meetingId: number) => void;
}

export const UpcomingMeetings: React.FC<UpcomingMeetingsProps> = ({ workspaceId, onSelectMeeting }) => {
  const [status, setStatus] = useState<CalendarStatusResponse | null>(null);
  const [events, setEvents] = useState<CalendarEventRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncSuccessMsg, setSyncSuccessMsg] = useState<string | null>(null);

  const loadCalendarData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusRes, upcomingRes] = await Promise.all([
        calendarApi.getStatus(workspaceId),
        calendarApi.getUpcomingEvents(workspaceId),
      ]);
      setStatus(statusRes);
      setEvents(upcomingRes.items);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load calendar data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCalendarData();
  }, [workspaceId]);

  const handleConnect = async () => {
    setConnecting(true);
    setError(null);
    try {
      const authUrl = await calendarApi.getConnectUrl(workspaceId);
      window.location.href = authUrl;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to initiate Google Calendar connection.');
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Disconnect Google Calendar for this workspace?')) return;
    setLoading(true);
    try {
      await calendarApi.disconnect(workspaceId);
      await loadCalendarData();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to disconnect calendar.');
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncSuccessMsg(null);
    setError(null);
    try {
      const res = await calendarApi.sync(workspaceId);
      setSyncSuccessMsg(`Synced ${res.synced_events_count} events (${res.created_meetings_count} new meeting records).`);
      const upcomingRes = await calendarApi.getUpcomingEvents(workspaceId);
      setEvents(upcomingRes.items);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to sync calendar events.');
    } finally {
      setSyncing(false);
    }
  };

  const formatEventDate = (isoStart: string, isoEnd: string) => {
    try {
      const start = new Date(isoStart);
      const end = new Date(isoEnd);

      const dateStr = start.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
      });
      const timeStart = start.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
      const timeEnd = end.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

      return `${dateStr} • ${timeStart} - ${timeEnd}`;
    } catch {
      return `${isoStart} - ${isoEnd}`;
    }
  };

  const parseAttendees = (jsonStr?: string | null): Array<{ email: string; name: string }> => {
    if (!jsonStr) return [];
    try {
      return JSON.parse(jsonStr);
    } catch {
      return [];
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Calendar Connection Status Header Banner */}
      <div
        className="card"
        style={{
          padding: '1.25rem 1.5rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          background: 'linear-gradient(135deg, var(--bg-card), var(--bg-input))',
          border: '1px solid var(--border-color)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              backgroundColor: 'rgba(99, 102, 241, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--primary)',
            }}
          >
            <Calendar size={22} />
          </div>

          <div>
            <div style={{ fontWeight: 700, fontSize: '1rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span>Google Calendar Sync</span>
              {status?.connected ? (
                <span
                  style={{
                    fontSize: '0.75rem',
                    backgroundColor: 'rgba(34, 197, 94, 0.15)',
                    color: '#4ade80',
                    border: '1px solid rgba(34, 197, 94, 0.3)',
                    padding: '0.125rem 0.5rem',
                    borderRadius: '12px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                  }}
                >
                  <CheckCircle2 size={12} /> Connected
                </span>
              ) : (
                <span
                  style={{
                    fontSize: '0.75rem',
                    backgroundColor: 'rgba(148, 163, 184, 0.15)',
                    color: 'var(--text-muted)',
                    padding: '0.125rem 0.5rem',
                    borderRadius: '12px',
                  }}
                >
                  Not Connected
                </span>
              )}
            </div>

            <div style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '0.125rem' }}>
              {status?.connected && status.connection?.account_email
                ? `Connected to ${status.connection.account_email}`
                : 'Connect your Google Calendar to automatically ingest upcoming meetings.'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
          {status?.connected ? (
            <>
              <button
                className="btn btn-secondary"
                onClick={handleSync}
                disabled={syncing}
                style={{ fontSize: '0.8125rem', padding: '0.5rem 0.875rem' }}
              >
                <RefreshCw size={14} className={syncing ? 'animate-spin' : ''} />
                <span>{syncing ? 'Syncing...' : 'Sync Now'}</span>
              </button>

              <button
                className="btn btn-secondary"
                onClick={handleDisconnect}
                style={{ fontSize: '0.8125rem', padding: '0.5rem 0.875rem', color: '#fca5a5', borderColor: 'rgba(239, 68, 68, 0.3)' }}
              >
                Disconnect
              </button>
            </>
          ) : (
            <button
              className="btn btn-primary"
              onClick={handleConnect}
              disabled={connecting}
              style={{ fontSize: '0.875rem', padding: '0.5rem 1rem' }}
            >
              {connecting ? <Loader2 size={16} className="animate-spin" /> : <Link2 size={16} />}
              <span>Connect Google Calendar</span>
            </button>
          )}
        </div>
      </div>

      {error && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#fca5a5',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {syncSuccessMsg && (
        <div
          style={{
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            border: '1px solid rgba(34, 197, 94, 0.3)',
            color: '#4ade80',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <CheckCircle2 size={16} />
          <span>{syncSuccessMsg}</span>
        </div>
      )}

      {/* Upcoming Meetings Grid */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#fff' }}>
            Upcoming Scheduled Meetings ({events.length})
          </h2>
        </div>

        {loading ? (
          <div className="card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Loader2 size={32} className="animate-spin" style={{ color: 'var(--primary)', marginBottom: '0.75rem' }} />
            <div>Loading upcoming scheduled meetings...</div>
          </div>
        ) : events.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '1rem' }}>
            {events.map((evt) => {
              const attendees = parseAttendees(evt.attendees_json);

              return (
                <div
                  key={evt.id}
                  className="card"
                  style={{
                    padding: '1.25rem',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    gap: '1rem',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', marginBottom: '0.5rem' }}>
                      <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', lineHeight: 1.3 }}>
                        {evt.title}
                      </h3>
                      <span
                        style={{
                          fontSize: '0.7rem',
                          backgroundColor: 'rgba(99, 102, 241, 0.15)',
                          color: 'var(--primary)',
                          padding: '0.125rem 0.375rem',
                          borderRadius: '4px',
                          fontWeight: 600,
                          flexShrink: 0,
                        }}
                      >
                        Scheduled
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                      <Clock size={14} style={{ color: 'var(--primary)' }} />
                      <span>{formatEventDate(evt.start_time, evt.end_time)}</span>
                    </div>

                    {evt.description && (
                      <p style={{ fontSize: '0.8125rem', color: 'var(--text-dim)', lineHeight: 1.4, marginBottom: '0.75rem', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {evt.description}
                      </p>
                    )}

                    {/* Organizer & Attendees */}
                    {(evt.organizer_email || attendees.length > 0) && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                        <Users size={12} />
                        <span>
                          {evt.organizer_email ? `Organized by ${evt.organizer_email}` : ''}
                          {attendees.length > 0 ? ` (${attendees.length} attendees)` : ''}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Actions & Join Link */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '0.75rem', borderTop: '1px solid var(--border-color)' }}>
                    {evt.meeting_url ? (
                      <a
                        href={evt.meeting_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-primary"
                        style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem', gap: '0.25rem' }}
                      >
                        <Video size={12} /> Join Meeting <ExternalLink size={10} />
                      </a>
                    ) : (
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>No Video URL</span>
                    )}

                    {evt.meeting_id && onSelectMeeting && (
                      <button
                        className="btn btn-secondary"
                        onClick={() => onSelectMeeting(evt.meeting_id!)}
                        style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
                      >
                        View Meeting
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="card" style={{ padding: '3rem 2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Calendar size={36} style={{ color: 'var(--text-dim)', marginBottom: '0.75rem' }} />
            <div style={{ fontSize: '1rem', fontWeight: 600, color: '#fff', marginBottom: '0.375rem' }}>
              No Upcoming Scheduled Meetings
            </div>
            <div style={{ fontSize: '0.875rem', maxWidth: '400px', margin: '0 auto 1.25rem' }}>
              {status?.connected
                ? 'Your Google Calendar is connected, but there are no upcoming events in the next 14 days.'
                : 'Connect your Google Calendar to sync upcoming meetings automatically.'}
            </div>

            {!status?.connected && (
              <button className="btn btn-primary" onClick={handleConnect} disabled={connecting}>
                {connecting ? <Loader2 size={16} className="animate-spin" /> : <Link2 size={16} />}
                <span>Connect Google Calendar</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
