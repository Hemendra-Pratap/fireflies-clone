export interface NotificationRead {
  id: number;
  user_id: number;
  workspace_id?: number | null;
  type: string;
  title: string;
  message: string;
  meeting_id?: number | null;
  read_at?: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationRead[];
  total: number;
  unread_count: number;
  page: number;
  size: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}
