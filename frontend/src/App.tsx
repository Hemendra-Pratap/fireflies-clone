import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { Dashboard } from './pages/Dashboard';
import { MeetingDetail } from './pages/MeetingDetail';
import { SettingsPage } from './pages/SettingsPage';
import { WorkspacesPage } from './pages/WorkspacesPage';
import { CreateMeetingModal } from './components/meetings/CreateMeetingModal';
import { CreateWorkspaceModal } from './components/workspace/CreateWorkspaceModal';
import { WorkspaceMembersModal } from './components/workspace/WorkspaceMembersModal';
import { AuthModal } from './components/auth/AuthModal';
import { authApi, User } from './api/auth';
import { WorkspaceProvider, useWorkspace } from './context/WorkspaceContext';
import { CalendarOAuthCallback } from './components/calendar/CalendarOAuthCallback';

interface AuthenticatedAppProps {
  user: User;
  onUserUpdated: (u: User) => void;
  onLogout: () => void;
}

const AuthenticatedApp: React.FC<AuthenticatedAppProps> = ({ user, onUserUpdated, onLogout }) => {
  const { activeWorkspace } = useWorkspace();
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [selectedMeetingId, setSelectedMeetingId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [isCreateWorkspaceModalOpen, setIsCreateWorkspaceModalOpen] = useState<boolean>(false);
  const [isManageMembersModalOpen, setIsManageMembersModalOpen] = useState<boolean>(false);

  // Clear selected meeting view when active workspace changes
  useEffect(() => {
    setSelectedMeetingId(null);
  }, [activeWorkspace?.id]);

  const handleMeetingCreated = (meeting: any) => {
    setSelectedMeetingId(meeting.id);
  };

  // Check if current route is OAuth callback
  const isCallbackRoute = window.location.pathname === '/calendar/callback';
  if (isCallbackRoute) {
    return (
      <CalendarOAuthCallback
        onComplete={() => {
          window.history.replaceState(null, '', '/');
          setCurrentTab('dashboard');
          setSelectedMeetingId(null);
        }}
      />
    );
  }

  const renderMainContent = () => {
    if (selectedMeetingId) {
      return (
        <MeetingDetail
          meetingId={selectedMeetingId}
          onBack={() => setSelectedMeetingId(null)}
        />
      );
    }

    switch (currentTab) {
      case 'workspaces':
        return (
          <WorkspacesPage
            user={user}
            onOpenCreateWorkspaceModal={() => setIsCreateWorkspaceModalOpen(true)}
          />
        );
      case 'settings':
        return (
          <SettingsPage
            user={user}
            onUserUpdated={onUserUpdated}
            onNavigateToWorkspaces={() => setCurrentTab('workspaces')}
          />
        );
      case 'all-meetings':
      case 'dashboard':
      default:
        return (
          <Dashboard
            searchQuery={searchQuery}
            onSelectMeeting={(id) => setSelectedMeetingId(id)}
            onOpenUploadModal={() => setIsUploadModalOpen(true)}
          />
        );
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        currentTab={currentTab}
        setCurrentTab={(tab) => {
          setCurrentTab(tab);
          setSelectedMeetingId(null);
        }}
        user={user}
        onLogout={onLogout}
      />

      <div className="main-content">
        <Header
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          onOpenUploadModal={() => setIsUploadModalOpen(true)}
          onOpenCreateWorkspace={() => setIsCreateWorkspaceModalOpen(true)}
          onOpenManageMembers={() => setIsManageMembersModalOpen(true)}
          onSelectMeeting={(id) => setSelectedMeetingId(id)}
          userEmail={user.email}
          onLogout={onLogout}
        />

        {renderMainContent()}
      </div>

      <CreateMeetingModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSuccess={handleMeetingCreated}
      />

      <CreateWorkspaceModal
        isOpen={isCreateWorkspaceModalOpen}
        onClose={() => setIsCreateWorkspaceModalOpen(false)}
      />

      <WorkspaceMembersModal
        isOpen={isManageMembersModalOpen}
        onClose={() => setIsManageMembersModalOpen(false)}
      />
    </div>
  );
};

export const App: React.FC = () => {
  // Auth state
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  // Logout handler — clears token and user state
  const handleLogout = useCallback(() => {
    authApi.logout();
    localStorage.removeItem('active_workspace_id');
    setUser(null);
  }, []);

  // On mount: check for existing token and resolve current user
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      setAuthLoading(false);
      return;
    }
    authApi
      .getMe()
      .then((u) => setUser(u))
      .catch(() => {
        // Token is invalid/expired — clear it
        authApi.logout();
        localStorage.removeItem('active_workspace_id');
      })
      .finally(() => setAuthLoading(false));
  }, []);

  // Listen for the custom auth:logout event fired by the 401 response interceptor
  useEffect(() => {
    const listener = () => {
      localStorage.removeItem('active_workspace_id');
      setUser(null);
    };
    window.addEventListener('auth:logout', listener);
    return () => window.removeEventListener('auth:logout', listener);
  }, []);

  const handleAuthenticated = (authenticatedUser: User) => {
    setUser(authenticatedUser);
  };

  // While resolving token on startup, show loading state
  if (authLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg-primary)',
          color: 'var(--text-muted)',
          fontSize: '0.9375rem',
        }}
      >
        Loading...
      </div>
    );
  }

  // If not authenticated, show the auth screen
  if (!user) {
    return <AuthModal onAuthenticated={handleAuthenticated} />;
  }

  return (
    <WorkspaceProvider user={user}>
      <AuthenticatedApp
        user={user}
        onUserUpdated={(updatedUser) => setUser(updatedUser)}
        onLogout={handleLogout}
      />
    </WorkspaceProvider>
  );
};

export default App;
