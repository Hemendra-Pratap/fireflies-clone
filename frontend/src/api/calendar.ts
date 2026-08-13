import { apiClient } from './client';
import {
  CalendarStatusResponse,
  CalendarSyncResponse,
  UpcomingEventsResponse,
} from '../types/calendar';

export const calendarApi = {
  getConnectUrl: async (workspaceId: number): Promise<string> => {
    const res = await apiClient.get<{ auth_url: string }>('/calendar/connect', {
      params: { workspace_id: workspaceId },
    });
    return res.data.auth_url;
  },

  handleCallback: async (code: string, state: string) => {
    const res = await apiClient.post('/calendar/callback', { code, state });
    return res.data;
  },

  getStatus: async (workspaceId: number): Promise<CalendarStatusResponse> => {
    const res = await apiClient.get<CalendarStatusResponse>('/calendar/status', {
      params: { workspace_id: workspaceId },
    });
    return res.data;
  },

  disconnect: async (workspaceId: number): Promise<{ message: string }> => {
    const res = await apiClient.post<{ message: string }>('/calendar/disconnect', null, {
      params: { workspace_id: workspaceId },
    });
    return res.data;
  },

  sync: async (workspaceId: number): Promise<CalendarSyncResponse> => {
    const res = await apiClient.post<CalendarSyncResponse>('/calendar/sync', null, {
      params: { workspace_id: workspaceId },
    });
    return res.data;
  },

  getUpcomingEvents: async (
    workspaceId: number,
    page = 1,
    size = 20
  ): Promise<UpcomingEventsResponse> => {
    const res = await apiClient.get<UpcomingEventsResponse>('/calendar/upcoming', {
      params: { workspace_id: workspaceId, page, size },
    });
    return res.data;
  },
};
