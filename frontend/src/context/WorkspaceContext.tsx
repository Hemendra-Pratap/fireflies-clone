import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { Workspace, WorkspaceMember } from '../types/workspace';
import { workspacesApi } from '../api/workspaces';
import { User } from '../api/auth';

interface WorkspaceContextType {
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  activeWorkspaceRole: string | null;
  loading: boolean;
  error: string | null;
  switchWorkspace: (workspaceId: number) => void;
  createWorkspace: (name: string) => Promise<Workspace>;
  updateWorkspaceName: (workspaceId: number, name: string) => Promise<Workspace>;
  addMember: (workspaceId: number, email: string, role: string) => Promise<WorkspaceMember>;
  updateMemberRole: (workspaceId: number, memberId: number, role: string) => Promise<WorkspaceMember>;
  removeMember: (workspaceId: number, memberId: number) => Promise<void>;
  refreshWorkspaces: () => Promise<void>;
  clearWorkspaceState: () => void;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

const ACTIVE_WORKSPACE_KEY = 'active_workspace_id';

export const WorkspaceProvider: React.FC<{ user: User | null; children: React.ReactNode }> = ({
  user,
  children,
}) => {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Compute active user's role in activeWorkspace
  const activeWorkspaceRole = React.useMemo(() => {
    if (!activeWorkspace || !user) return null;
    if (activeWorkspace.owner_id === user.id) return 'OWNER';
    const member = activeWorkspace.members.find((m) => m.user_id === user.id);
    return member?.role || 'MEMBER';
  }, [activeWorkspace, user]);

  const clearWorkspaceState = useCallback(() => {
    setWorkspaces([]);
    setActiveWorkspace(null);
    localStorage.removeItem(ACTIVE_WORKSPACE_KEY);
  }, []);

  const refreshWorkspaces = useCallback(async () => {
    if (!user) {
      clearWorkspaceState();
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const list = await workspacesApi.listWorkspaces();
      setWorkspaces(list);

      if (list.length > 0) {
        const savedIdStr = localStorage.getItem(ACTIVE_WORKSPACE_KEY);
        const savedId = savedIdStr ? parseInt(savedIdStr, 10) : null;
        const matching = list.find((w) => w.id === savedId);

        if (matching) {
          setActiveWorkspace(matching);
        } else {
          setActiveWorkspace(list[0]);
          localStorage.setItem(ACTIVE_WORKSPACE_KEY, list[0].id.toString());
        }
      } else {
        setActiveWorkspace(null);
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to load workspaces';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [user, clearWorkspaceState]);

  useEffect(() => {
    refreshWorkspaces();
  }, [refreshWorkspaces]);

  const switchWorkspace = useCallback(
    (workspaceId: number) => {
      const target = workspaces.find((w) => w.id === workspaceId);
      if (target) {
        setActiveWorkspace(target);
        localStorage.setItem(ACTIVE_WORKSPACE_KEY, target.id.toString());
      }
    },
    [workspaces]
  );

  const createWorkspace = useCallback(
    async (name: string) => {
      const newWs = await workspacesApi.createWorkspace({ name });
      await refreshWorkspaces();
      switchWorkspace(newWs.id);
      return newWs;
    },
    [refreshWorkspaces, switchWorkspace]
  );

  const updateWorkspaceName = useCallback(
    async (workspaceId: number, name: string) => {
      const updatedWs = await workspacesApi.updateWorkspace(workspaceId, name);
      await refreshWorkspaces();
      return updatedWs;
    },
    [refreshWorkspaces]
  );

  const addMember = useCallback(
    async (workspaceId: number, email: string, role: string) => {
      const newMember = await workspacesApi.addMember(workspaceId, { user_email: email, role });
      await refreshWorkspaces();
      return newMember;
    },
    [refreshWorkspaces]
  );

  const updateMemberRole = useCallback(
    async (workspaceId: number, memberId: number, role: string) => {
      const updatedMember = await workspacesApi.updateMemberRole(workspaceId, memberId, role);
      await refreshWorkspaces();
      return updatedMember;
    },
    [refreshWorkspaces]
  );

  const removeMember = useCallback(
    async (workspaceId: number, memberId: number) => {
      await workspacesApi.removeMember(workspaceId, memberId);
      await refreshWorkspaces();
    },
    [refreshWorkspaces]
  );

  return (
    <WorkspaceContext.Provider
      value={{
        workspaces,
        activeWorkspace,
        activeWorkspaceRole,
        loading,
        error,
        switchWorkspace,
        createWorkspace,
        updateWorkspaceName,
        addMember,
        updateMemberRole,
        removeMember,
        refreshWorkspaces,
        clearWorkspaceState,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
};

export const useWorkspace = (): WorkspaceContextType => {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
};
