import { apiClient } from './client';
import { ActionItem } from '../types/meeting';

export const actionItemsApi = {
  async updateActionItem(
    actionItemId: number,
    patchData: { is_completed?: boolean; description?: string; due_at?: string | null }
  ): Promise<ActionItem> {
    const res = await apiClient.patch<ActionItem>(`/action-items/${actionItemId}`, patchData);
    return res.data;
  },
};
