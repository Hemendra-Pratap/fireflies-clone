import React, { useState, useEffect, useRef } from 'react';
import { searchApi } from '../../api/search';
import { SearchResultItem } from '../../types/search';
import { useWorkspace } from '../../context/WorkspaceContext';
import {
  FileText,
  MessageSquare,
  Sparkles,
  CheckCircle2,
  Bookmark,
  User,
  Loader2,
  AlertCircle,
  Clock,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

interface SearchDropdownProps {
  query: string;
  onSelectMeeting: (meetingId: number) => void;
  onClose: () => void;
}

const formatTimestamp = (ms: number | null): string | null => {
  if (ms === null || ms < 0) return null;
  const totalSecs = Math.floor(ms / 1000);
  const mins = Math.floor(totalSecs / 60);
  const secs = totalSecs % 60;
  return `[${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}]`;
};

const getBadgeConfig = (matchType: string) => {
  switch (matchType) {
    case 'title':
      return { label: 'Title', icon: FileText, color: '#818cf8', bg: 'rgba(99, 102, 241, 0.15)' };
    case 'transcript':
      return { label: 'Transcript', icon: MessageSquare, color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.15)' };
    case 'summary':
      return { label: 'Summary', icon: Sparkles, color: '#f472b6', bg: 'rgba(244, 114, 182, 0.15)' };
    case 'action_item':
      return { label: 'Action Item', icon: CheckCircle2, color: '#4ade80', bg: 'rgba(74, 222, 128, 0.15)' };
    case 'chapter':
      return { label: 'Chapter', icon: Bookmark, color: '#fbbf24', bg: 'rgba(251, 191, 36, 0.15)' };
    case 'participant':
      return { label: 'Participant', icon: User, color: '#c084fc', bg: 'rgba(192, 132, 252, 0.15)' };
    default:
      return { label: matchType, icon: FileText, color: 'var(--text-muted)', bg: 'var(--bg-input)' };
  }
};

export const SearchDropdown: React.FC<SearchDropdownProps> = ({
  query,
  onSelectMeeting,
  onClose,
}) => {
  const { activeWorkspace } = useWorkspace();
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [matchFilter, setMatchFilter] = useState<string>('all');
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  // Reset page to 1 when query or category filter changes
  useEffect(() => {
    setPage(1);
  }, [query, matchFilter]);

  // Fetch search results with AbortController for race-condition prevention
  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      setTotal(0);
      setTotalPages(1);
      setLoading(false);
      setError(null);
      return;
    }

    const abortController = new AbortController();
    setLoading(true);
    setError(null);

    const filter = matchFilter === 'all' ? undefined : matchFilter;
    searchApi
      .search(trimmed, page, 10, filter, activeWorkspace?.id, abortController.signal)
      .then((res) => {
        setResults(res.items);
        setTotal(res.total);
        setTotalPages(res.pages || 1);
      })
      .catch((err) => {
        if (err.name === 'CanceledError' || err.name === 'AbortError') return;
        const msg = err.response?.data?.detail || err.message || 'Search request failed.';
        setError(msg);
      })
      .finally(() => {
        if (!abortController.signal.aborted) {
          setLoading(false);
        }
      });

    return () => {
      abortController.abort();
    };
  }, [query, page, matchFilter, activeWorkspace?.id]);

  if (!query.trim()) return null;

  const categories = [
    { key: 'all', label: 'All' },
    { key: 'title', label: 'Titles' },
    { key: 'transcript', label: 'Transcripts' },
    { key: 'summary', label: 'Summaries' },
    { key: 'action_item', label: 'Action Items' },
    { key: 'chapter', label: 'Chapters' },
    { key: 'participant', label: 'Participants' },
  ];

  return (
    <div
      ref={dropdownRef}
      style={{
        position: 'absolute',
        top: 'calc(100% + 0.5rem)',
        left: 0,
        right: 0,
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: '10px',
        boxShadow: '0 20px 40px -10px rgba(0, 0, 0, 0.6)',
        zIndex: 1050,
        maxHeight: '520px',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* Search Header & Category Filter Bar */}
      <div
        style={{
          padding: '0.75rem 1rem',
          borderBottom: '1px solid var(--border-color)',
          backgroundColor: 'var(--bg-input)',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <span>
            Search results for <strong style={{ color: '#fff' }}>"{query.trim()}"</strong>
          </span>
          {!loading && <span>{total} matches found</span>}
        </div>

        {/* Category Pills */}
        <div style={{ display: 'flex', gap: '0.375rem', overflowX: 'auto', paddingBottom: '0.25rem' }}>
          {categories.map((cat) => (
            <button
              key={cat.key}
              onClick={() => setMatchFilter(cat.key)}
              style={{
                background: matchFilter === cat.key ? 'var(--primary)' : 'transparent',
                color: matchFilter === cat.key ? '#fff' : 'var(--text-muted)',
                border: '1px solid',
                borderColor: matchFilter === cat.key ? 'var(--primary)' : 'var(--border-color)',
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                fontSize: '0.6875rem',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease',
              }}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Results Container */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem 1rem' }}>
        {loading ? (
          <div style={{ padding: '2rem 0', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Loader2 size={24} className="animate-spin" style={{ color: 'var(--primary)', marginBottom: '0.5rem' }} />
            <div style={{ fontSize: '0.8125rem' }}>Searching meeting intelligence...</div>
          </div>
        ) : error ? (
          <div style={{ padding: '1.5rem', textAlign: 'center', color: '#fca5a5', fontSize: '0.8125rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        ) : results.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>
            {results.map((item, idx) => {
              const badge = getBadgeConfig(item.match_type);
              const BadgeIcon = badge.icon;
              const timestamp = formatTimestamp(item.timestamp_ms);

              return (
                <div
                  key={`${item.meeting_id}-${item.match_type}-${idx}`}
                  onClick={() => {
                    onSelectMeeting(item.meeting_id);
                    onClose();
                  }}
                  style={{
                    padding: '0.75rem',
                    backgroundColor: 'var(--bg-primary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--primary)')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-color)')}
                >
                  {/* Top Bar: Badge, Timestamp, Meeting Title */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.375rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span
                        style={{
                          fontSize: '0.6875rem',
                          fontWeight: 700,
                          padding: '0.125rem 0.375rem',
                          borderRadius: '4px',
                          backgroundColor: badge.bg,
                          color: badge.color,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                        }}
                      >
                        <BadgeIcon size={12} />
                        {badge.label}
                      </span>

                      {timestamp && (
                        <span
                          style={{
                            fontSize: '0.6875rem',
                            color: 'var(--text-muted)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            fontFamily: 'monospace',
                          }}
                        >
                          <Clock size={12} />
                          {timestamp}
                        </span>
                      )}
                    </div>

                    <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '220px' }}>
                      {item.meeting_title}
                    </div>
                  </div>

                  {/* Matched Text Snippet */}
                  <div
                    style={{
                      fontSize: '0.8125rem',
                      color: 'var(--text-main)',
                      lineHeight: 1.4,
                      backgroundColor: 'var(--bg-input)',
                      padding: '0.375rem 0.5rem',
                      borderRadius: '4px',
                      borderLeft: `3px solid ${badge.color}`,
                    }}
                  >
                    {item.matched_text}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* Empty Search Results */
          <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#fff', marginBottom: '0.25rem' }}>
              No matches found
            </div>
            <div style={{ fontSize: '0.8125rem' }}>
              No items in this workspace match <strong style={{ color: '#fff' }}>"{query.trim()}"</strong>.
            </div>
          </div>
        )}
      </div>

      {/* Pagination Footer */}
      {totalPages > 1 && (
        <div
          style={{
            padding: '0.5rem 1rem',
            borderTop: '1px solid var(--border-color)',
            backgroundColor: 'var(--bg-input)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
          }}
        >
          <span>
            Page {page} of {totalPages}
          </span>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              className="btn btn-secondary"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
            >
              <ChevronLeft size={14} /> Prev
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
