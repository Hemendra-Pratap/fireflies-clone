import { apiClient } from './client';
import {
  Workspace,
  WorkspaceCreateInput,
  WorkspaceMember,
  WorkspaceMemberCreateInput,
} from '../types/workspace';

export const workspacesApi = {
  async listWorkspaces(): Promise<Workspace[]> {
    const res = await apiClient.get<Workspace[]>('/workspaces');
    return res.data;
  },

  async createWorkspace(input: WorkspaceCreateInput): Promise<Workspace> {
    const res = await apiClient.post<Workspace>('/workspaces', input);
    return res.data;
  },

  async getWorkspace(workspaceId: number): Promise<Workspace> {
    const res = await apiClient.get<Workspace>(`/workspaces/${workspaceId}`);
    return res.data;
  },

  async updateWorkspace(workspaceId: number, name: string): Promise<Workspace> {
    const res = await apiClient.patch<Workspace>(`/workspaces/${workspaceId}`, { name });
    return res.data;
  },

  async listMembers(workspaceId: number): Promise<WorkspaceMember[]> {
    const res = await apiClient.get<WorkspaceMember[]>(`/workspaces/${workspaceId}/members`);
    return res.data;
  },

  async addMember(
    workspaceId: number,
    input: WorkspaceMemberCreateInput
  ): Promise<WorkspaceMember> {
    const res = await apiClient.post<WorkspaceMember>(
      `/workspaces/${workspaceId}/members`,
      input
    );
    return res.data;
  },

  async updateMemberRole(
    workspaceId: number,
    memberId: number,
    role: string
  ): Promise<WorkspaceMember> {
    const res = await apiClient.patch<WorkspaceMember>(
      `/workspaces/${workspaceId}/members/${memberId}`,
      { role }
    );
    return res.data;
  },

  async removeMember(workspaceId: number, memberId: number): Promise<void> {
    await apiClient.delete(`/workspaces/${workspaceId}/members/${memberId}`);
  },
};
