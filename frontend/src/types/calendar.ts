export interface CalendarConnectionRead {
  id: number;
  provider: string;
  account_email?: string | null;
  status: string;
  last_synced_at?: string | null;
  created_at: string;
}

export interface CalendarStatusResponse {
  connected: boolean;
  connection?: CalendarConnectionRead | null;
}

export interface CalendarEventRead {
  id: number;
  calendar_connection_id: number;
  workspace_id: number;
  user_id: number;
  external_event_id: string;
  title: string;
  description?: string | null;
  start_time: string;
  end_time: string;
  timezone?: string | null;
  organizer_email?: string | null;
  attendees_json?: string | null;
  meeting_url?: string | null;
  status: string;
  meeting_id?: number | null;
  synced_at?: string | null;
}

export interface UpcomingEventsResponse {
  items: CalendarEventRead[];
  total: number;
  page: number;
  size: number;
}

export interface CalendarSyncResponse {
  message: string;
  synced_events_count: number;
  created_meetings_count: number;
}
