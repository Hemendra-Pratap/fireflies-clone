import React from 'react';
import { MeetingStatus } from '../../types/meeting';
import { CheckCircle2, Clock, AlertCircle, Loader2 } from 'lucide-react';

interface StatusBadgeProps {
  status: MeetingStatus;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  switch (status) {
    case 'completed':
      return (
        <span className="badge badge-completed">
          <CheckCircle2 size={14} /> Completed
        </span>
      );
    case 'failed':
      return (
        <span className="badge badge-failed">
          <AlertCircle size={14} /> Failed
        </span>
      );
    case 'transcribing':
    case 'analyzing':
      return (
        <span className="badge badge-processing">
          <Loader2 size={14} className="animate-spin" /> {status === 'transcribing' ? 'Transcribing...' : 'AI Analyzing...'}
        </span>
      );
    case 'uploaded':
    case 'transcribed':
      return (
        <span className="badge badge-processing">
          <Clock size={14} /> Ready ({status})
        </span>
      );
    default:
      return (
        <span className="badge badge-created">
          <Clock size={14} /> Created
        </span>
      );
  }
};
