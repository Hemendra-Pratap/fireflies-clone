import { apiClient } from './client';
import {
  Meeting,
  MeetingCreateInput,
  MeetingIntelligence,
  MeetingListResponse,
  Summary,
  ActionItem,
  Chapter,
  TranscriptSegment,
} from '../types/meeting';

export const meetingsApi = {
  async listMeetings(page = 1, size = 20, status?: string): Promise<MeetingListResponse> {
    const params: Record<string, any> = { page, size };
    if (status) params.status = status;
    const res = await apiClient.get<MeetingListResponse>('/meetings', { params });
    return res.data;
  },

  async searchMeetings(q: string, page = 1, size = 20, status?: string): Promise<MeetingListResponse> {
    const params: Record<string, any> = { q, page, size };
    if (status) params.status = status;
    const res = await apiClient.get<MeetingListResponse>('/meetings/search', { params });
    return res.data;
  },

  async getMeeting(meetingId: number): Promise<Meeting> {
    const res = await apiClient.get<Meeting>(`/meetings/${meetingId}`);
    return res.data;
  },

  async createMeeting(input: MeetingCreateInput): Promise<Meeting> {
    const res = await apiClient.post<Meeting>('/meetings', input);
    return res.data;
  },

  async uploadAudio(
    meetingId: number,
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<Meeting> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await apiClient.post<Meeting>(`/meetings/${meetingId}/audio`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
    return res.data;
  },

  async triggerTranscription(meetingId: number): Promise<Meeting> {
    const res = await apiClient.post<Meeting>(`/meetings/${meetingId}/transcribe`);
    return res.data;
  },

  async triggerAnalysis(meetingId: number): Promise<Meeting> {
    const res = await apiClient.post<Meeting>(`/meetings/${meetingId}/analyze`);
    return res.data;
  },

  async getStatus(meetingId: number): Promise<{ id: number; status: string; error_message: string | null }> {
    const res = await apiClient.get(`/meetings/${meetingId}/status`);
    return res.data;
  },

  async getSummary(meetingId: number): Promise<Summary> {
    const res = await apiClient.get<Summary>(`/meetings/${meetingId}/summary`);
    return res.data;
  },

  async getActionItems(meetingId: number): Promise<ActionItem[]> {
    const res = await apiClient.get<ActionItem[]>(`/meetings/${meetingId}/action-items`);
    return res.data;
  },

  async getChapters(meetingId: number): Promise<Chapter[]> {
    const res = await apiClient.get<Chapter[]>(`/meetings/${meetingId}/chapters`);
    return res.data;
  },

  async getTranscript(meetingId: number): Promise<TranscriptSegment[]> {
    const res = await apiClient.get<TranscriptSegment[]>(`/meetings/${meetingId}/transcript`);
    return res.data;
  },

  async getIntelligence(meetingId: number): Promise<MeetingIntelligence> {
    const res = await apiClient.get<MeetingIntelligence>(`/meetings/${meetingId}/intelligence`);
    return res.data;
  },

  async deleteMeeting(meetingId: number): Promise<void> {
    await apiClient.delete(`/meetings/${meetingId}`);
  },
};
