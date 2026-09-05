import React, { useState, useEffect } from 'react';
import { User, Plus, FileUp, ShieldCheck, Activity, Database, Trash2, FileText, CheckCircle2, AlertCircle } from 'lucide-react';
import { fetchPatientDocuments } from '../api';

export default function PatientSidebar({
  patients,
  selectedPatient,
  onSelectPatient,
  onCreatePatient,
  onDeletePatient,
  onClearAllPatients,
  onOpenUpload,
  serverStatus,
  docRefreshKey
}) {
  const [newPatientId, setNewPatientId] = useState('');
  const [showInput, setShowInput] = useState(false);
  const [docSummary, setDocSummary] = useState({
    has_documents: false,
    total_documents: 0,
    total_chunks: 0,
    documents: []
  });
  const [loadingDocs, setLoadingDocs] = useState(false);

  const handleCreate = (e) => {
    e.preventDefault();
    if (!newPatientId.trim()) return;
    onCreatePatient(newPatientId.trim().toUpperCase());
    setNewPatientId('');
    setShowInput(false);
  };

  useEffect(() => {
    let isMounted = true;
    if (selectedPatient) {
      setLoadingDocs(true);
      fetchPatientDocuments(selectedPatient)
        .then(data => {
          if (isMounted) {
            setDocSummary(data || { has_documents: false, total_documents: 0, total_chunks: 0, documents: [] });
            setLoadingDocs(false);
          }
        })
        .catch(err => {
          console.error('Failed to load patient documents:', err);
          if (isMounted) setLoadingDocs(false);
        });
    } else {
      setDocSummary({ has_documents: false, total_documents: 0, total_chunks: 0, documents: [] });
    }
    return () => { isMounted = false; };
  }, [selectedPatient, docRefreshKey]);

  const formatPatientDisplay = (id) => {
    if (!id) return '';
    if (id.length > 20) {
      return `PT-${id.slice(0, 8)}...${id.slice(-4)}`;
    }
    return id;
  };

  return (
    <aside style={{
      width: '320px',
      background: 'rgba(11, 15, 25, 0.95)',
      borderRight: '1px solid var(--border-color)',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      padding: '20px 16px'
    }}>
      {/* Brand Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: '10px',
          background: 'linear-gradient(135deg, #14b8a6, #06b6d4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#000',
          fontWeight: 'bold',
          boxShadow: '0 4px 12px rgba(20, 184, 166, 0.3)'
        }}>
          <ShieldCheck size={22} />
        </div>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.02em', margin: 0 }}>
            MediRAG
          </h2>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Activity size={12} color="var(--primary-teal)" /> Dual-LLM Verifier
          </span>
        </div>
      </div>

      {/* System Health Status */}
      <div style={{
        padding: '8px 12px',
        background: 'rgba(255, 255, 255, 0.03)',
        borderRadius: '8px',
        border: '1px solid rgba(255, 255, 255, 0.06)',
        marginBottom: '16px',
        fontSize: '0.78rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)' }}>
          <Database size={13} /> Qdrant Store:
        </div>
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          padding: '2px 8px',
          borderRadius: '12px',
          fontSize: '0.7rem',
          fontWeight: 600,
          background: serverStatus?.qdrant_connected ? 'rgba(52, 211, 153, 0.15)' : 'rgba(239, 68, 68, 0.15)',
          color: serverStatus?.qdrant_connected ? '#34d399' : '#f87171'
        }}>
          <span style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: serverStatus?.qdrant_connected ? '#34d399' : '#f87171'
          }} />
          {serverStatus?.qdrant_connected ? 'Connected' : 'Offline'}
        </span>
      </div>

      {/* Patient Section Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <h3 style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', fontWeight: 600, margin: 0 }}>
          Patient Directory ({patients.length})
        </h3>
        <div style={{ display: 'flex', gap: '6px' }}>
          {patients.length > 0 && (
            <button
              onClick={() => {
                if (window.confirm('Are you sure you want to remove all patient records from the database?')) {
                  onClearAllPatients && onClearAllPatients();
                }
              }}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-dim)',
                cursor: 'pointer',
                padding: '4px',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center'
              }}
              title="Clear All Patients"
            >
              <Trash2 size={13} />
            </button>
          )}
          <button
            onClick={() => setShowInput(!showInput)}
            className="btn-secondary"
            style={{ padding: '3px 8px', fontSize: '0.72rem' }}
            title="Register New Patient Profile"
          >
            <Plus size={13} /> Add
          </button>
        </div>
      </div>

      {/* New Patient Form */}
      {showInput && (
        <form onSubmit={handleCreate} className="fade-in" style={{ marginBottom: '14px' }}>
          <div style={{ display: 'flex', gap: '6px' }}>
            <input
              type="text"
              placeholder="e.g. PATIENT-1001"
              value={newPatientId}
              onChange={(e) => setNewPatientId(e.target.value)}
              className="mono"
              style={{
                flex: 1,
                padding: '8px 10px',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                color: 'var(--text-main)',
                fontSize: '0.82rem'
              }}
              autoFocus
            />
            <button type="submit" className="btn-primary" style={{ padding: '6px 12px', fontSize: '0.78rem' }}>
              Save
            </button>
          </div>
        </form>
      )}

      {/* Patient List */}
      <div style={{ maxHeight: '180px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '16px' }}>
        {patients.length === 0 ? (
          <div style={{ padding: '20px 10px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.82rem' }}>
            No patient profiles registered.<br/>
            Click <strong style={{ color: 'var(--primary-teal)' }}>+ Add</strong> to create a profile.
          </div>
        ) : (
          patients.map((pid) => {
            const isSelected = selectedPatient === pid;
            return (
              <div
                key={pid}
                onClick={() => onSelectPatient(pid)}
                style={{
                  padding: '8px 12px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  background: isSelected ? 'rgba(20, 184, 166, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                  border: isSelected ? '1px solid rgba(20, 184, 166, 0.4)' : '1px solid rgba(255, 255, 255, 0.04)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
                  <User size={15} color={isSelected ? 'var(--primary-teal)' : 'var(--text-muted)'} style={{ flexShrink: 0 }} />
                  <div style={{ overflow: 'hidden' }}>
                    <div
                      className="mono"
                      title={pid}
                      style={{
                        fontWeight: 600,
                        fontSize: '0.82rem',
                        color: isSelected ? 'var(--primary-teal)' : 'var(--text-main)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis'
                      }}
                    >
                      {formatPatientDisplay(pid)}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  {isSelected && (
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--primary-teal)', boxShadow: '0 0 8px var(--primary-teal)' }} />
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm(`Delete records for ${pid}?`)) {
                        onDeletePatient && onDeletePatient(pid);
                      }
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-dim)',
                      cursor: 'pointer',
                      padding: '2px 4px',
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      opacity: 0.6
                    }}
                    title={`Delete ${pid}`}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Selected Patient Document Presence Section */}
      {selectedPatient && (
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          background: 'rgba(15, 23, 42, 0.6)',
          borderRadius: '10px',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          padding: '12px',
          overflow: 'hidden'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <h4 style={{ fontSize: '0.76rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', fontWeight: 600, margin: 0 }}>
              Stored Patient Documents
            </h4>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 8px',
              borderRadius: '12px',
              fontSize: '0.7rem',
              fontWeight: 600,
              background: docSummary.has_documents ? 'rgba(20, 184, 166, 0.15)' : 'rgba(245, 158, 11, 0.15)',
              color: docSummary.has_documents ? 'var(--primary-teal)' : '#f59e0b'
            }}>
              {docSummary.has_documents ? <CheckCircle2 size={11} /> : <AlertCircle size={11} />}
              {docSummary.has_documents ? `${docSummary.total_documents} File${docSummary.total_documents > 1 ? 's' : ''}` : 'No files'}
            </span>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {loadingDocs ? (
              <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.78rem' }}>
                Checking vector database...
              </div>
            ) : docSummary.has_documents ? (
              docSummary.documents.map((doc, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '8px 10px',
                    background: 'rgba(255, 255, 255, 0.03)',
                    borderRadius: '6px',
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  <FileText size={15} color="var(--primary-teal)" style={{ flexShrink: 0 }} />
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <div style={{
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      color: 'var(--text-main)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }} title={doc.filename}>
                      {doc.filename}
                    </div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', display: 'flex', gap: '8px' }}>
                      <span>{doc.document_type}</span>
                      <span>•</span>
                      <span>{doc.chunks} chunks indexed</span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div style={{ padding: '16px 8px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.78rem' }}>
                No medical documents present in database for this patient profile.<br/><br/>
                Click below to upload PDFs, text records, or scans.
              </div>
            )}
          </div>

          <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
            <button
              onClick={onOpenUpload}
              className="btn-primary"
              style={{ width: '100%', justifyContent: 'center', fontSize: '0.82rem', padding: '8px' }}
            >
              <FileUp size={15} /> Upload Patient Files
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
