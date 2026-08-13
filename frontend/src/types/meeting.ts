export type MeetingStatus =
  | 'created'
  | 'uploaded'
  | 'transcribing'
  | 'transcribed'
  | 'analyzing'
  | 'completed'
  | 'failed';

export interface Meeting {
  id: number;
  title: string;
  source_name: string | null;
  recorded_at: string;
  duration_ms: number | null;
  status: MeetingStatus;
  audio_file_path: string | null;
  audio_filename: string | null;
  audio_mime_type: string | null;
  audio_size_bytes: number | null;
  workspace_id?: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface MeetingListResponse {
  items: Meeting[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface Participant {
  id: number;
  meeting_id: number;
  display_name: string;
  speaker_label: string | null;
  email: string | null;
  is_host: boolean;
}

export interface TranscriptSegment {
  id: number;
  meeting_id: number;
  participant_id: number | null;
  sequence_number: number;
  start_time_ms: number;
  end_time_ms: number;
  text: string;
}

export interface Summary {
  id: number;
  meeting_id: number;
  overview: string;
  key_points: string[];
}

export interface ActionItem {
  id: number;
  meeting_id: number;
  participant_id: number | null;
  description: string;
  is_completed: boolean;
  completed_at: string | null;
  due_at: string | null;
}

export interface Chapter {
  id: number;
  meeting_id: number;
  sequence_number: number;
  title: string;
  summary: string | null;
  start_time_ms: number;
  end_time_ms: number | null;
}

export interface MeetingIntelligence {
  meeting: Meeting;
  summary: Summary | null;
  action_items: ActionItem[];
  chapters: Chapter[];
  participants: Participant[];
  transcript_segments: TranscriptSegment[];
}

export interface MeetingCreateInput {
  title: string;
  source_name?: string;
  recorded_at?: string;
  duration_ms?: number;
  workspace_id?: number;
}
