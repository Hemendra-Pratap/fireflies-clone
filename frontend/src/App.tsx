import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { Dashboard } from './pages/Dashboard';
import { MeetingDetail } from './pages/MeetingDetail';
import { CreateMeetingModal } from './components/meetings/CreateMeetingModal';
import { AuthModal } from './components/auth/AuthModal';
import { authApi, User } from './api/auth';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [selectedMeetingId, setSelectedMeetingId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);

  // Auth state
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  // Logout handler — clears token and user state
  const handleLogout = useCallback(() => {
    authApi.logout();
    setUser(null);
    setSelectedMeetingId(null);
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
      })
      .finally(() => setAuthLoading(false));
  }, []);

  // Listen for the custom auth:logout event fired by the 401 response interceptor
  useEffect(() => {
    const listener = () => setUser(null);
    window.addEventListener('auth:logout', listener);
    return () => window.removeEventListener('auth:logout', listener);
  }, []);

  const handleAuthenticated = (authenticatedUser: User) => {
    setUser(authenticatedUser);
  };

  const handleMeetingCreated = (meeting: any) => {
    setSelectedMeetingId(meeting.id);
  };

  // While resolving token on startup, show nothing (or a spinner)
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
    <div className="app-container">
      <Sidebar
        currentTab={currentTab}
        setCurrentTab={(tab) => {
          setCurrentTab(tab);
          if (tab === 'dashboard') setSelectedMeetingId(null);
        }}
        user={user}
        onLogout={handleLogout}
      />

      <div className="main-content">
        <Header
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          onOpenUploadModal={() => setIsUploadModalOpen(true)}
          userEmail={user.email}
          onLogout={handleLogout}
        />

        {selectedMeetingId ? (
          <MeetingDetail
            meetingId={selectedMeetingId}
            onBack={() => setSelectedMeetingId(null)}
          />
        ) : (
          <Dashboard
            searchQuery={searchQuery}
            onSelectMeeting={(id) => setSelectedMeetingId(id)}
            onOpenUploadModal={() => setIsUploadModalOpen(true)}
          />
        )}
      </div>

      <CreateMeetingModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSuccess={handleMeetingCreated}
      />
    </div>
  );
};

export default App;
