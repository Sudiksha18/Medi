import React, { useState, useEffect } from 'react';
import { MessageSquare, Activity, Calendar, FileText, ShieldCheck, UserCheck } from 'lucide-react';
import PatientSidebar from './components/PatientSidebar';
import ChatWindow from './components/ChatWindow';
import LabTrendsView from './components/LabTrendsView';
import PatientTimelineView from './components/PatientTimelineView';
import ClinicalSummaryModal from './components/ClinicalSummaryModal';
import ClinicalRiskCalculatorView from './components/ClinicalRiskCalculatorView';
import FileUploadModal from './components/FileUploadModal';
import { fetchPatients, createPatient as apiCreatePatient, deletePatient as apiDeletePatient, clearAllPatients as apiClearAllPatients, checkHealth } from './api';

export default function App() {
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [serverStatus, setServerStatus] = useState(null);
  const [docRefreshKey, setDocRefreshKey] = useState(0);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'labs' | 'timeline' | 'summary' | 'risk'

  const loadPatients = async () => {
    try {
      const pList = await fetchPatients();
      setPatients(pList);
      if (pList.length > 0 && (!selectedPatient || !pList.includes(selectedPatient))) {
        setSelectedPatient(pList[0]);
      } else if (pList.length === 0) {
        setSelectedPatient(null);
      }
    } catch (err) {
      console.error('Failed to fetch patient list:', err);
    }
  };

  const loadHealth = async () => {
    try {
      const status = await checkHealth();
      setServerStatus(status);
    } catch (err) {
      console.error('Failed health check:', err);
      setServerStatus({ qdrant_connected: false });
    }
  };

  useEffect(() => {
    loadPatients();
    loadHealth();
  }, []);

  const handleCreatePatient = async (newId) => {
    try {
      await apiCreatePatient(newId);
      if (!patients.includes(newId)) {
        setPatients(prev => [...prev, newId]);
      }
      setSelectedPatient(newId);
    } catch (err) {
      console.error('Error creating patient:', err);
    }
  };

  const handleDeletePatient = async (patientId) => {
    try {
      await apiDeletePatient(patientId);
      setPatients(prev => prev.filter(p => p !== patientId));
      if (selectedPatient === patientId) {
        const remaining = patients.filter(p => p !== patientId);
        setSelectedPatient(remaining.length > 0 ? remaining[0] : null);
      }
    } catch (err) {
      console.error('Error deleting patient:', err);
    }
  };

  const handleClearAllPatients = async () => {
    try {
      await apiClearAllPatients();
      setPatients([]);
      setSelectedPatient(null);
    } catch (err) {
      console.error('Error clearing patients:', err);
    }
  };

  const handleUploadComplete = async (patientId) => {
    await loadPatients();
    setSelectedPatient(patientId);
    setDocRefreshKey(prev => prev + 1);
  };

  const navTabs = [
    { id: 'chat', label: 'Medical Chat', icon: MessageSquare },
    { id: 'labs', label: 'Lab Trends & Vitals', icon: Activity },
    { id: 'timeline', label: 'Patient Timeline', icon: Calendar },
    { id: 'summary', label: 'Clinical Brief', icon: FileText },
    { id: 'risk', label: 'Risk & Differential', icon: ShieldCheck }
  ];

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', overflow: 'hidden' }}>
      {/* Patient Profile & Document Sidebar */}
      <PatientSidebar
        patients={patients}
        selectedPatient={selectedPatient}
        onSelectPatient={(pid) => setSelectedPatient(pid)}
        onCreatePatient={handleCreatePatient}
        onDeletePatient={handleDeletePatient}
        onClearAllPatients={handleClearAllPatients}
        onOpenUpload={() => setShowUploadModal(true)}
        serverStatus={serverStatus}
        docRefreshKey={docRefreshKey}
      />

      {/* Main Workspace Area */}
      {selectedPatient ? (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
          {/* Top Clinical Module Navigation Tabs */}
          <nav style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 20px',
            background: 'rgba(15, 23, 42, 0.95)',
            borderBottom: '1px solid var(--border-color)',
            overflowX: 'auto'
          }}>
            {navTabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    fontSize: '0.84rem',
                    fontWeight: 600,
                    border: isActive ? '1px solid var(--primary-teal)' : '1px solid transparent',
                    background: isActive ? 'rgba(20, 184, 166, 0.15)' : 'transparent',
                    color: isActive ? 'var(--primary-teal)' : 'var(--text-muted)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    whiteSpace: 'nowrap'
                  }}
                >
                  <Icon size={16} />
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Active Clinical View */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {activeTab === 'chat' && (
              <ChatWindow
                patientId={selectedPatient}
                onOpenUpload={() => setShowUploadModal(true)}
                docRefreshKey={docRefreshKey}
              />
            )}
            {activeTab === 'labs' && (
              <LabTrendsView patientId={selectedPatient} />
            )}
            {activeTab === 'timeline' && (
              <PatientTimelineView patientId={selectedPatient} />
            )}
            {activeTab === 'summary' && (
              <ClinicalSummaryModal patientId={selectedPatient} />
            )}
            {activeTab === 'risk' && (
              <ClinicalRiskCalculatorView patientId={selectedPatient} />
            )}
          </div>
        </div>
      ) : (
        <main style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: '16px',
          color: 'var(--text-muted)'
        }}>
          <h2 style={{ fontSize: '1.4rem', color: 'var(--text-main)' }}>Welcome to Medical RAG Clinical Platform</h2>
          <p style={{ fontSize: '0.9rem' }}>Select an existing patient profile or create a new one to start clinical analysis.</p>
        </main>
      )}

      {/* Upload Modal */}
      {showUploadModal && selectedPatient && (
        <FileUploadModal
          patientId={selectedPatient}
          onClose={() => setShowUploadModal(false)}
          onUploadComplete={handleUploadComplete}
        />
      )}
    </div>
  );
}
