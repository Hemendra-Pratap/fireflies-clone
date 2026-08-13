import React, { useEffect, useState, useRef } from 'react';
import { meetingsApi } from '../../api/meetings';
import { Meeting } from '../../types/meeting';
import { Loader2, CheckCircle2, AlertCircle, RefreshCw, Sparkles, Mic, FileText } from 'lucide-react';

interface ProcessingStateViewProps {
  meeting: Meeting;
  onStatusUpdated: (updatedMeeting: Meeting) => void;
}

export const ProcessingStateView: React.FC<ProcessingStateViewProps> = ({
  meeting,
  onStatusUpdated,
}) => {
  const [currentStatus, setCurrentStatus] = useState(meeting.status);
  const [errorMessage, setErrorMessage] = useState<string | null>(meeting.error_message);
  const [actionLabel, setActionLabel] = useState<string>('Initializing pipeline...');
  const [isBusy, setIsBusy] = useState(false);
  const isTransitioningRef = useRef(false);

  useEffect(() => {
    setCurrentStatus(meeting.status);
    setErrorMessage(meeting.error_message);
  }, [meeting.status, meeting.error_message]);

  useEffect(() => {
    let timerId: ReturnType<typeof setTimeout> | null = null;
    let isCancelled = false;

    const pollAndTransition = async () => {
      if (isTransitioningRef.current || isCancelled) return;
      isTransitioningRef.current = true;

      try {
        const latestStatusData = await meetingsApi.getStatus(meeting.id);
        if (isCancelled) return;

        const status = latestStatusData.status;
        setCurrentStatus(status as any);
        setErrorMessage(latestStatusData.error_message);

        if (status === 'uploaded') {
          setActionLabel('Triggering Speech-to-Text Transcription...');
          setIsBusy(true);
          const updated = await meetingsApi.triggerTranscription(meeting.id);
          if (!isCancelled) {
            setCurrentStatus(updated.status);
            onStatusUpdated(updated);
          }
        } else if (status === 'transcribed') {
          setActionLabel('Triggering Gemini AI Meeting Analysis...');
          setIsBusy(true);
          const updated = await meetingsApi.triggerAnalysis(meeting.id);
          if (!isCancelled) {
            setCurrentStatus(updated.status);
            onStatusUpdated(updated);
          }
        } else if (status === 'transcribing') {
          setActionLabel('Speech-to-Text model transcribing audio recording...');
          setIsBusy(true);
        } else if (status === 'analyzing') {
          setActionLabel('Gemini AI generating summary, action items & chapters...');
          setIsBusy(true);
        } else if (status === 'completed') {
          setActionLabel('Processing complete!');
          setIsBusy(false);
          onStatusUpdated(meeting);
          return;
        } else if (status === 'failed') {
          setActionLabel('Processing failed');
          setIsBusy(false);
          return;
        }
      } catch (err: any) {
        console.error('Processing state workflow error:', err);
      } finally {
        isTransitioningRef.current = false;
        if (!isCancelled && ['created', 'uploaded', 'transcribing', 'transcribed', 'analyzing'].includes(currentStatus)) {
          timerId = setTimeout(pollAndTransition, 3000);
        }
      }
    };

    if (['created', 'uploaded', 'transcribing', 'transcribed', 'analyzing'].includes(currentStatus)) {
      pollAndTransition();
    }

    return () => {
      isCancelled = true;
      if (timerId) clearTimeout(timerId);
    };
  }, [meeting.id, currentStatus]);

  const handleRetry = async () => {
    setIsBusy(true);
    setErrorMessage(null);
    try {
      let transcriptExists = false;
      if (currentStatus === 'transcribed' || currentStatus === 'analyzing') {
        transcriptExists = true;
      } else {
        try {
          const segments = await meetingsApi.getTranscript(meeting.id);
          if (segments && segments.length > 0) {
            transcriptExists = true;
          }
        } catch {
          transcriptExists = false;
        }
      }

      if (transcriptExists) {
        setActionLabel('Retrying Gemini AI Meeting Analysis...');
        const updated = await meetingsApi.triggerAnalysis(meeting.id);
        setCurrentStatus(updated.status);
        onStatusUpdated(updated);
      } else {
        setActionLabel('Retrying Speech-to-Text Transcription...');
        const updated = await meetingsApi.triggerTranscription(meeting.id);
        setCurrentStatus(updated.status);
        onStatusUpdated(updated);
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Retry failed.';
      setErrorMessage(msg);
    } finally {
      setIsBusy(false);
    }
  };

  const steps = [
    { key: 'uploaded', label: 'Audio Ingested', icon: FileText },
    { key: 'transcribing', label: 'Transcription (STT)', icon: Mic },
    { key: 'analyzing', label: 'Gemini AI Intelligence', icon: Sparkles },
    { key: 'completed', label: 'Ready', icon: CheckCircle2 },
  ];

  const getStepState = (stepKey: string) => {
    const order = ['created', 'uploaded', 'transcribing', 'transcribed', 'analyzing', 'completed'];
    const currentIdx = order.indexOf(currentStatus);
    const stepIdx = order.indexOf(stepKey);

    if (currentStatus === 'failed') return 'error';
    if (currentIdx > stepIdx || currentStatus === 'completed') return 'done';
    if (currentStatus === stepKey || (stepKey === 'transcribing' && currentStatus === 'uploaded') || (stepKey === 'analyzing' && currentStatus === 'transcribed')) return 'active';
    return 'pending';
  };

  return (
    <div className="card" style={{ padding: '2rem', textAlign: 'center', margin: '1.5rem 0' }}>
      <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff', marginBottom: '0.5rem' }}>
        Processing Meeting Intelligence
      </h3>
      <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '2rem' }}>
        {actionLabel}
      </p>

      {/* Progress Stepper */}
      <div style={{ display: 'flex', justifyContent: 'space-between', position: 'relative', maxWidth: '640px', margin: '0 auto 2.5rem' }}>
        {steps.map((step) => {
          const state = getStepState(step.key);
          const Icon = step.icon;

          return (
            <div key={step.key} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', zIndex: 1, flex: 1 }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  backgroundColor:
                    state === 'done'
                      ? 'var(--badge-completed-bg)'
                      : state === 'active'
                      ? 'var(--primary-light)'
                      : state === 'error'
                      ? 'var(--badge-failed-bg)'
                      : 'var(--bg-input)',
                  border: `2px solid ${
                    state === 'done'
                      ? 'var(--badge-completed)'
                      : state === 'active'
                      ? 'var(--primary)'
                      : state === 'error'
                      ? 'var(--badge-failed)'
                      : 'var(--border-color)'
                  }`,
                  color:
                    state === 'done'
                      ? 'var(--badge-completed)'
                      : state === 'active'
                      ? 'var(--primary)'
                      : state === 'error'
                      ? 'var(--badge-failed)'
                      : 'var(--text-dim)',
                  transition: 'all 0.3s ease',
                }}
              >
                {state === 'active' && isBusy ? (
                  <Loader2 size={20} className="animate-spin" />
                ) : (
                  <Icon size={20} />
                )}
              </div>
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  marginTop: '0.5rem',
                  color: state === 'pending' ? 'var(--text-dim)' : '#fff',
                }}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>

      {currentStatus === 'failed' && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#fca5a5',
            padding: '1rem',
            borderRadius: '8px',
            maxWidth: '500px',
            margin: '0 auto 1.5rem',
            textAlign: 'left',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>
            <AlertCircle size={18} /> Processing Error
          </div>
          <div style={{ fontSize: '0.8125rem' }}>{errorMessage || 'An unknown error occurred during audio processing.'}</div>
          <button className="btn btn-secondary" onClick={handleRetry} style={{ marginTop: '0.75rem' }} disabled={isBusy}>
            <RefreshCw size={14} /> Retry Processing Step
          </button>
        </div>
      )}
    </div>
  );
};
