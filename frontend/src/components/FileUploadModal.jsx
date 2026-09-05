import React, { useState } from 'react';
import { X, UploadCloud, FileText, Image as ImageIcon, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { uploadFiles } from '../api';

export default function FileUploadModal({ patientId, onClose, onUploadComplete }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [statusMsg, setStatusMsg] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      setSelectedFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0 || !patientId) return;

    setUploading(true);
    setStatusMsg(null);

    try {
      const res = await uploadFiles(patientId, selectedFiles);
      setStatusMsg({
        type: 'success',
        text: `Successfully processed ${res.files_processed.length} file(s) into ${res.total_chunks_stored} vector embeddings for ${patientId}.`
      });
      setTimeout(() => {
        onUploadComplete(patientId);
        onClose();
      }, 1500);
    } catch (err) {
      console.error(err);
      setStatusMsg({
        type: 'error',
        text: err.response?.data?.detail || 'Failed to upload and process files. Please try again.'
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div className="glass-panel fade-in" style={{
        width: '100%',
        maxWidth: '520px',
        background: '#0d1322',
        padding: '24px',
        position: 'relative'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-main)' }}>
              Upload Medical Records
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Target Patient: <span className="mono" style={{ color: 'var(--primary-teal)', fontWeight: 600 }}>{patientId}</span>
            </p>
          </div>
          <button onClick={onClose} className="btn-secondary" style={{ padding: '6px' }}>
            <X size={18} />
          </button>
        </div>

        {/* Drag and Drop Zone */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          style={{
            border: '2px dashed var(--border-color)',
            borderRadius: '12px',
            padding: '32px 20px',
            textAlign: 'center',
            background: 'rgba(255, 255, 255, 0.015)',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            marginBottom: '16px'
          }}
          onClick={() => document.getElementById('file-input-modal').click()}
        >
          <UploadCloud size={40} color="var(--primary-teal)" style={{ marginBottom: '10px' }} />
          <h4 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
            Drag & Drop Medical Files Here
          </h4>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginBottom: '12px' }}>
              Supports PDF reports, text notes (TXT), and X-ray/scan images (PNG, JPG, BMP).
          </p>
          <input
            id="file-input-modal"
            type="file"
            multiple
            accept=".pdf,.txt,text/plain,.png,.jpg,.jpeg,.bmp,.tiff"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <button type="button" className="btn-secondary" style={{ pointerEvents: 'none', fontSize: '0.8rem' }}>
            Browse Computer
          </button>
        </div>

        {/* Selected File List */}
        {selectedFiles.length > 0 && (
          <div style={{ marginBottom: '16px', maxHeight: '140px', overflowY: 'auto' }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600 }}>
              Files Ready for Ingestion ({selectedFiles.length}):
            </div>
            {selectedFiles.map((file, idx) => {
              const isTextDocument = file.name.toLowerCase().endsWith('.pdf') || file.name.toLowerCase().endsWith('.txt') || file.type.includes('pdf') || file.type.startsWith('text/plain');
              return (
                <div key={idx} style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 10px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  borderRadius: '6px',
                  marginBottom: '4px',
                  fontSize: '0.8rem'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                    {isTextDocument ? <FileText size={16} color="var(--accent-blue)" /> : <ImageIcon size={16} color="var(--primary-teal)" />}
                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: 'var(--text-main)' }}>
                      {file.name}
                    </span>
                  </div>
                  <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                    {(file.size / 1024).toFixed(1)} KB
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* Status Message */}
        {statusMsg && (
          <div style={{
            padding: '10px 12px',
            borderRadius: '8px',
            marginBottom: '16px',
            fontSize: '0.82rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: statusMsg.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            border: statusMsg.type === 'success' ? '1px solid rgba(52, 211, 153, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
            color: statusMsg.type === 'success' ? '#34d399' : '#f87171'
          }}>
            {statusMsg.type === 'success' ? <CheckCircle size={16} /> : <AlertCircle size={16} />}
            <span>{statusMsg.text}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          <button onClick={onClose} className="btn-secondary" disabled={uploading}>
            Cancel
          </button>
          <button
            onClick={handleUpload}
            className="btn-primary"
            disabled={uploading || selectedFiles.length === 0}
          >
            {uploading ? (
              <>
                <Loader2 size={16} className="pulsing" style={{ animation: 'spin 1s linear infinite' }} /> Processing & Embedding...
              </>
            ) : (
              'Upload & Index Records'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
