import React, { useState, useEffect } from 'react';
import { meetingsApi } from '../../api/meetings';
import { Meeting } from '../../types/meeting';
import { X, UploadCloud, FileAudio, AlertCircle, Loader2 } from 'lucide-react';

import { useWorkspace } from '../../context/WorkspaceContext';

interface CreateMeetingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (meeting: Meeting) => void;
}

const toDatetimeLocal = (d: Date) => {
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

export const CreateMeetingModal: React.FC<CreateMeetingModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { activeWorkspace } = useWorkspace();
  const [title, setTitle] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [recordedAt, setRecordedAt] = useState<string>(toDatetimeLocal(new Date()));
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setTitle('');
      setFile(null);
      setRecordedAt(toDatetimeLocal(new Date()));
      setLoading(false);
      setUploadProgress(0);
      setError(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      const validExtensions = ['.mp3', '.wav', '.m4a', '.ogg', '.webm', '.mp4', '.aac', '.flac'];
      const ext = selected.name.substring(selected.name.lastIndexOf('.')).toLowerCase();

      if (!validExtensions.includes(ext)) {
        setError(`Invalid audio file format '${ext}'. Allowed: MP3, WAV, M4A, OGG, WEBM, MP4, AAC, FLAC.`);
        setFile(null);
        return;
      }

      setError(null);
      setFile(selected);
      if (!title) {
        // Auto fill title from filename
        const baseName = selected.name.substring(0, selected.name.lastIndexOf('.'));
        setTitle(baseName.replace(/[-_]/g, ' '));
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Meeting title is required.');
      return;
    }
    if (!file) {
      setError('Please select an audio file to upload.');
      return;
    }

    setLoading(true);
    setError(null);
    setUploadProgress(0);

    let createdMeetingId: number | null = null;
    try {
      // 1. Create Meeting associated with active workspace
      const newMeeting = await meetingsApi.createMeeting({
        title: title.trim(),
        source_name: 'Web Upload',
        recorded_at: recordedAt ? new Date(recordedAt).toISOString() : new Date().toISOString(),
        workspace_id: activeWorkspace?.id,
      });
      createdMeetingId = newMeeting.id;

      // 2. Upload Audio File with Progress Tracking
      const updatedMeeting = await meetingsApi.uploadAudio(
        newMeeting.id,
        file,
        (progress) => setUploadProgress(progress)
      );

      // 3. Emit success
      onSuccess(updatedMeeting);
      onClose();
    } catch (err: any) {
      if (createdMeetingId !== null) {
        try {
          await meetingsApi.deleteMeeting(createdMeetingId);
        } catch {
          // Preserve original upload error if deletion fails
        }
      }
      const msg = err.response?.data?.detail || err.message || 'Failed to create meeting or upload audio.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fff' }}>Create & Upload Meeting</h2>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        </div>

        {error && (
          <div
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#fca5a5',
              padding: '0.75rem 1rem',
              borderRadius: '8px',
              marginBottom: '1.5rem',
              fontSize: '0.875rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-main)' }}>
              Meeting Title <span style={{ color: '#ef4444' }}>*</span>
            </label>
            <input
              type="text"
              className="input-search"
              style={{ width: '100%', paddingLeft: '1rem' }}
              placeholder="e.g. Product Strategy & Architecture Sync"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={loading}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-main)' }}>
              Date & Time Recorded
            </label>
            <input
              type="datetime-local"
              className="input-search"
              style={{ width: '100%', paddingLeft: '1rem', colorScheme: 'dark' }}
              value={recordedAt}
              onChange={(e) => setRecordedAt(e.target.value)}
              disabled={loading}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-main)' }}>
              Audio Recording <span style={{ color: '#ef4444' }}>*</span>
            </label>

            <div
              style={{
                border: '2px dashed var(--border-color)',
                borderRadius: '12px',
                padding: '2rem 1rem',
                textAlign: 'center',
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                cursor: loading ? 'not-allowed' : 'pointer',
                position: 'relative',
              }}
            >
              <input
                type="file"
                accept="audio/*,video/mp4"
                onChange={handleFileChange}
                disabled={loading}
                style={{
                  position: 'absolute',
                  inset: 0,
                  opacity: 0,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  width: '100%',
                  height: '100%',
                }}
              />

              {file ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem', color: 'var(--primary)' }}>
                  <FileAudio size={28} />
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.875rem' }}>{file.name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {(file.size / (1024 * 1024)).toFixed(2)} MB
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
                  <UploadCloud size={36} style={{ color: 'var(--primary)' }} />
                  <div style={{ fontWeight: 600, fontSize: '0.875rem', color: '#fff' }}>
                    Click or drag audio file to upload
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    MP3, WAV, M4A, OGG, WEBM, MP4 (Max 100 MB)
                  </div>
                </div>
              )}
            </div>
          </div>

          {loading && uploadProgress > 0 && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.375rem' }}>
                <span>Uploading audio binary...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div style={{ height: '6px', backgroundColor: 'var(--bg-input)', borderRadius: '3px', overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${uploadProgress}%`,
                    backgroundColor: 'var(--primary)',
                    transition: 'width 0.2s ease',
                  }}
                />
              </div>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1rem' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Uploading...
                </>
              ) : (
                'Start Upload & Processing'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
