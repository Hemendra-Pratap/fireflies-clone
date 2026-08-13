import { User } from '../api/auth';

export type WorkspaceRole = 'OWNER' | 'ADMIN' | 'MEMBER';

export interface WorkspaceMember {
  id: number;
  workspace_id: number;
  user_id: number;
  role: WorkspaceRole | string;
  created_at: string;
  user?: User | null;
}

export interface Workspace {
  id: number;
  name: string;
  owner_id: number;
  created_at: string;
  updated_at: string;
  members: WorkspaceMember[];
}

export interface WorkspaceCreateInput {
  name: string;
}

export interface WorkspaceMemberCreateInput {
  user_email: string;
  role: WorkspaceRole | string;
}
