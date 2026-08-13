import React, { useState, useEffect } from 'react';
import { ActionItem, Participant } from '../../types/meeting';
import { actionItemsApi } from '../../api/actionItems';
import { CheckSquare, Square, Calendar, User as UserIcon, AlertCircle } from 'lucide-react';

interface ActionItemsTabProps {
  actionItems: ActionItem[];
  participants: Participant[];
}

export const ActionItemsTab: React.FC<ActionItemsTabProps> = ({
  actionItems: initialActionItems,
  participants,
}) => {
  const [items, setItems] = useState<ActionItem[]>(initialActionItems);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setItems(initialActionItems);
  }, [initialActionItems]);

  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(() => setError(null), 4000);
    return () => clearTimeout(timer);
  }, [error]);

  const participantMap = new Map<number, Participant>();
  participants.forEach((p) => participantMap.set(p.id, p));

  const handleToggle = async (item: ActionItem) => {
    const newStatus = !item.is_completed;
    setUpdatingId(item.id);
    setError(null);

    // Optimistic UI update
    setItems((prev) =>
      prev.map((i) => (i.id === item.id ? { ...i, is_completed: newStatus } : i))
    );

    try {
      const updated = await actionItemsApi.updateActionItem(item.id, {
        is_completed: newStatus,
      });

      // Server state is authoritative
      setItems((prev) => prev.map((i) => (i.id === item.id ? updated : i)));
    } catch (err: any) {
      // Revert UI on failure
      setItems((prev) =>
        prev.map((i) => (i.id === item.id ? { ...i, is_completed: item.is_completed } : i))
      );
      setError(`Failed to update action item: ${err.message || 'Network error'}`);
    } finally {
      setUpdatingId(null);
    }
  };

  if (!items || items.length === 0) {
    return (
      <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        No action items extracted for this meeting.
      </div>
    );
  }

  const completedCount = items.filter((i) => i.is_completed).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>
          Action Items Checklist ({completedCount} / {items.length} completed)
        </h4>
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
            justifyContent: 'space-between',
            gap: '0.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            style={{ background: 'none', border: 'none', color: '#fca5a5', cursor: 'pointer', fontSize: '0.875rem' }}
          >
            ×
          </button>
        </div>
      )}

      {items.map((item) => {
        const participant = item.participant_id ? participantMap.get(item.participant_id) : null;
        const isBusy = updatingId === item.id;

        return (
          <div
            key={item.id}
            className="card"
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '1rem',
              padding: '1.25rem',
              opacity: item.is_completed ? 0.65 : 1,
              transition: 'opacity 0.2s ease',
            }}
          >
            <button
              onClick={() => handleToggle(item)}
              disabled={isBusy}
              style={{
                background: 'none',
                border: 'none',
                color: item.is_completed ? 'var(--badge-completed)' : 'var(--text-dim)',
                cursor: isBusy ? 'wait' : 'pointer',
                marginTop: '0.125rem',
                flexShrink: 0,
              }}
            >
              {item.is_completed ? <CheckSquare size={22} /> : <Square size={22} />}
            </button>

            <div style={{ flex: 1 }}>
              <p
                style={{
                  fontSize: '0.9375rem',
                  fontWeight: 500,
                  color: item.is_completed ? 'var(--text-muted)' : '#fff',
                  textDecoration: item.is_completed ? 'line-through' : 'none',
                  lineHeight: 1.4,
                }}
              >
                {item.description}
              </p>

              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '1rem',
                  marginTop: '0.5rem',
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                }}
              >
                {participant && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--primary)' }}>
                    <UserIcon size={12} /> {participant.display_name || participant.speaker_label}
                  </span>
                )}

                {item.due_at && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                    <Calendar size={12} /> Due: {new Date(item.due_at).toLocaleDateString()}
                  </span>
                )}

                {item.completed_at && item.is_completed && (
                  <span style={{ color: 'var(--badge-completed)' }}>
                    Completed at {new Date(item.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
