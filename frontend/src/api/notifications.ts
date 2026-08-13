import { apiClient } from './client';
import {
  NotificationListResponse,
  NotificationRead,
  UnreadCountResponse,
} from '../types/notification';

export const notificationsApi = {
  listNotifications: async (
    workspaceId?: number,
    unreadOnly = false,
    page = 1,
    size = 20
  ): Promise<NotificationListResponse> => {
    const res = await apiClient.get<NotificationListResponse>('/notifications', {
      params: {
        workspace_id: workspaceId,
        unread_only: unreadOnly,
        page,
        size,
      },
    });
    return res.data;
  },

  getUnreadCount: async (workspaceId?: number): Promise<number> => {
    const res = await apiClient.get<UnreadCountResponse>('/notifications/unread-count', {
      params: { workspace_id: workspaceId },
    });
    return res.data.unread_count;
  },

  markAsRead: async (notificationId: number): Promise<NotificationRead> => {
    const res = await apiClient.post<NotificationRead>(
      `/notifications/${notificationId}/read`
    );
    return res.data;
  },

  markAllAsRead: async (workspaceId?: number): Promise<number> => {
    const res = await apiClient.post<{ marked_count: number }>(
      '/notifications/read-all',
      null,
      { params: { workspace_id: workspaceId } }
    );
    return res.data.marked_count;
  },
};
