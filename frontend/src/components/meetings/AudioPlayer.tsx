import React, { useState, useEffect, useRef } from 'react';
import { apiClient } from '../../api/client';
import { Play, Pause, RotateCcw, RotateCw, Volume2, VolumeX, Loader2, AlertCircle, Music } from 'lucide-react';

interface AudioPlayerProps {
  meetingId: number;
  audioFilename: string | null;
  durationMs: number | null;
  onTimeUpdate: (currentTimeMs: number) => void;
  seekTimeMs: number | null;
  onPlaybackEnd?: () => void;
}

const formatAudioTime = (seconds: number, forceHours = false): string => {
  if (isNaN(seconds) || seconds < 0) return forceHours ? '00:00:00' : '00:00';
  const totalSecs = Math.floor(seconds);
  const hrs = Math.floor(totalSecs / 3600);
  const mins = Math.floor((totalSecs % 3600) / 60);
  const secs = totalSecs % 60;

  if (hrs > 0 || forceHours) {
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

export const AudioPlayer: React.FC<AudioPlayerProps> = ({
  meetingId,
  audioFilename,
  durationMs,
  onTimeUpdate,
  seekTimeMs,
  onPlaybackEnd,
}) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTimeSec, setCurrentTimeSec] = useState<number>(0);
  const [durationSec, setDurationSec] = useState<number>(durationMs ? durationMs / 1000 : 0);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [volume, setVolume] = useState<number>(1.0);

  const lastReportedSecondRef = useRef<number>(-1);

  // Load audio Blob securely using apiClient with Authorization header
  useEffect(() => {
    let objectUrl: string | null = null;
    setLoading(true);
    setError(null);
    setIsPlaying(false);
    setCurrentTimeSec(0);
    lastReportedSecondRef.current = -1;

    apiClient
      .get(`/meetings/${meetingId}/audio`, { responseType: 'blob' })
      .then((res) => {
        objectUrl = URL.createObjectURL(res.data);
        setAudioUrl(objectUrl);
      })
      .catch((err) => {
        const msg = err.response?.data?.detail || 'Audio file unavailable or access denied.';
        setError(msg);
      })
      .finally(() => {
        setLoading(false);
      });

    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [meetingId]);

  // Handle external seek requests e.g. clicking transcript segment
  useEffect(() => {
    if (seekTimeMs !== null && audioRef.current) {
      const targetSec = seekTimeMs / 1000;
      audioRef.current.currentTime = targetSec;
      setCurrentTimeSec(targetSec);

      const ms = Math.floor(targetSec * 1000);
      onTimeUpdate(ms);

      audioRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch(() => {});
    }
  }, [seekTimeMs, onTimeUpdate]);

  const togglePlayPause = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch((err) => console.error('Playback error:', err));
    }
  };

  const handleTimeUpdate = () => {
    if (!audioRef.current) return;
    const curSec = audioRef.current.currentTime;
    setCurrentTimeSec(curSec);

    // Throttle onTimeUpdate calls to avoid excessive state churn
    const roundedSec = Math.floor(curSec);
    if (roundedSec !== lastReportedSecondRef.current) {
      lastReportedSecondRef.current = roundedSec;
      onTimeUpdate(Math.floor(curSec * 1000));
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current && audioRef.current.duration) {
      setDurationSec(audioRef.current.duration);
    }
  };

  const handleSeekChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const valSec = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = valSec;
      setCurrentTimeSec(valSec);
      onTimeUpdate(Math.floor(valSec * 1000));
    }
  };

  const skipSeconds = (secs: number) => {
    if (!audioRef.current) return;
    const newSec = Math.max(0, Math.min(durationSec, audioRef.current.currentTime + secs));
    audioRef.current.currentTime = newSec;
    setCurrentTimeSec(newSec);
    onTimeUpdate(Math.floor(newSec * 1000));
  };

  const toggleMute = () => {
    if (!audioRef.current) return;
    const newMuteState = !isMuted;
    audioRef.current.muted = newMuteState;
    setIsMuted(newMuteState);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVol = parseFloat(e.target.value);
    setVolume(newVol);
    if (audioRef.current) {
      audioRef.current.volume = newVol;
      if (newVol === 0) {
        setIsMuted(true);
      } else if (isMuted) {
        setIsMuted(false);
      }
    }
  };

  if (loading) {
    return (
      <div
        className="card"
        style={{
          padding: '1rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          color: 'var(--text-muted)',
          fontSize: '0.875rem',
        }}
      >
        <Loader2 size={18} className="animate-spin" style={{ color: 'var(--primary)' }} />
        <span>Loading meeting audio recording...</span>
      </div>
    );
  }

  if (error || !audioUrl) {
    return (
      <div
        style={{
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#fca5a5',
          padding: '0.875rem 1.25rem',
          borderRadius: '10px',
          marginBottom: '1.5rem',
          fontSize: '0.875rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.625rem',
        }}
      >
        <AlertCircle size={18} />
        <span>{error || 'Audio recording unavailable for this meeting.'}</span>
      </div>
    );
  }

  const isLongDuration = durationSec >= 3600;

  return (
    <div
      className="card"
      style={{
        padding: '1rem 1.25rem',
        marginBottom: '1.5rem',
        background: 'linear-gradient(180deg, var(--bg-card), var(--bg-input))',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
      }}
    >
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={() => {
          setIsPlaying(false);
          if (onPlaybackEnd) onPlaybackEnd();
        }}
        preload="metadata"
      />

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        {/* Playback Control Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            onClick={() => skipSeconds(-10)}
            className="btn btn-secondary"
            style={{ padding: '0.5rem', borderRadius: '50%' }}
            title="Rewind 10 seconds"
          >
            <RotateCcw size={16} />
          </button>

          <button
            onClick={togglePlayPause}
            className="btn btn-primary"
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '50%',
              padding: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(99, 102, 241, 0.4)',
            }}
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? <Pause size={20} /> : <Play size={20} style={{ marginLeft: '2px' }} />}
          </button>

          <button
            onClick={() => skipSeconds(10)}
            className="btn btn-secondary"
            style={{ padding: '0.5rem', borderRadius: '50%' }}
            title="Forward 10 seconds"
          >
            <RotateCw size={16} />
          </button>
        </div>

        {/* Timeline Slider & Time Display */}
        <div style={{ flex: 1, minWidth: '220px', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#fff', fontWeight: 600, minWidth: '55px' }}>
            {formatAudioTime(currentTimeSec, isLongDuration)}
          </span>

          <input
            type="range"
            min={0}
            max={durationSec || 100}
            step={0.1}
            value={currentTimeSec}
            onChange={handleSeekChange}
            style={{
              flex: 1,
              accentColor: 'var(--primary)',
              cursor: 'pointer',
              height: '6px',
            }}
          />

          <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', minWidth: '55px' }}>
            {formatAudioTime(durationSec, isLongDuration)}
          </span>
        </div>

        {/* Audio Filename & Volume Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {audioFilename && (
            <div
              style={{
                fontSize: '0.75rem',
                color: 'var(--primary)',
                backgroundColor: 'rgba(99, 102, 241, 0.15)',
                padding: '0.25rem 0.625rem',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                gap: '0.375rem',
                maxWidth: '160px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
              title={audioFilename}
            >
              <Music size={12} />
              <span>{audioFilename}</span>
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
            <button
              onClick={toggleMute}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '0.25rem' }}
              title={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted || volume === 0 ? <VolumeX size={18} /> : <Volume2 size={18} />}
            </button>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={isMuted ? 0 : volume}
              onChange={handleVolumeChange}
              style={{ width: '60px', accentColor: 'var(--primary)', cursor: 'pointer' }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
