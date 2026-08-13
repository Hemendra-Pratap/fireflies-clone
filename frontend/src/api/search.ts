import { apiClient } from './client';
import { SearchResponse } from '../types/search';

export const searchApi = {
  async search(
    query: string,
    page = 1,
    size = 20,
    status?: string,
    workspaceId?: number,
    signal?: AbortSignal
  ): Promise<SearchResponse> {
    const params: Record<string, any> = { q: query, page, size };
    if (status) params.status = status;
    if (workspaceId) params.workspace_id = workspaceId;
    const res = await apiClient.get<SearchResponse>('/search', { params, signal });
    return res.data;
  },
};
