import React, { useState } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { Dashboard } from './pages/Dashboard';
import { MeetingDetail } from './pages/MeetingDetail';
import { CreateMeetingModal } from './components/meetings/CreateMeetingModal';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [selectedMeetingId, setSelectedMeetingId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);

  const handleMeetingCreated = (meeting: any) => {
    setSelectedMeetingId(meeting.id);
  };

  return (
    <div className="app-container">
      <Sidebar currentTab={currentTab} setCurrentTab={(tab) => {
        setCurrentTab(tab);
        if (tab === 'dashboard') setSelectedMeetingId(null);
      }} />

      <div className="main-content">
        <Header
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          onOpenUploadModal={() => setIsUploadModalOpen(true)}
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
