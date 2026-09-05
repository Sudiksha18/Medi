import React, { useState } from 'react';
import { FileText, Copy, Check, RefreshCw, Sparkles, Download, Play } from 'lucide-react';
import { generateClinicalSummary } from '../api';

export default function ClinicalSummaryModal({ patientId }) {
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(null);

  const handleGenerate = async () => {
    if (!patientId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await generateClinicalSummary(patientId);
      setSummary(res.summary_markdown || 'No summary generated.');
    } catch (err) {
      console.error(err);
      setError('Failed to generate clinical summary. Please wait a moment and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!summary) return;
    navigator.clipboard.writeText(summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!summary) return;
    const blob = new Blob([summary], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `clinical_summary_${patientId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{
      flex: 1,
      overflowY: 'auto',
      padding: '28px',
      background: 'radial-gradient(circle at 50% 0%, rgba(139, 92, 246, 0.04), transparent 70%), var(--bg-dark)'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div>
          <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-dim)', letterSpacing: '0.05em' }}>
            STRUCTURED CLINICAL DOCUMENTATION
          </span>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-main)', margin: '4px 0 0 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileText color="#8b5cf6" />
            Clinical Brief & Discharge Summary: {patientId}
          </h2>
        </div>

        {summary && (
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="btn-secondary"
              style={{ fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <RefreshCw size={14} className={loading ? 'spin' : ''} /> Regenerate
            </button>
            <button
              onClick={handleCopy}
              disabled={!summary || loading}
              className="btn-secondary"
              style={{ fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
              {copied ? 'Copied!' : 'Copy Note'}
            </button>
            <button
              onClick={handleDownload}
              disabled={!summary || loading}
              className="btn-primary"
              style={{ fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Download size={14} /> Export Markdown
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '350px', color: 'var(--text-muted)', gap: '14px' }}>
          <Sparkles size={32} className="pulsing" color="var(--primary-teal)" />
          <div style={{ fontSize: '0.95rem' }}>Synthesizing comprehensive clinical brief from patient records...</div>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>Auditing active diagnoses, prescriptions, and lab records</span>
        </div>
      ) : error ? (
        <div style={{ padding: '20px', borderRadius: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#f87171' }}>
          {error}
          <div style={{ marginTop: '12px' }}>
            <button onClick={handleGenerate} className="btn-secondary" style={{ fontSize: '0.8rem' }}>
              Retry Generation
            </button>
          </div>
        </div>
      ) : !summary ? (
        <div style={{
          padding: '48px',
          textAlign: 'center',
          borderRadius: '16px',
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px dashed var(--border-color)',
          color: 'var(--text-muted)'
        }}>
          <FileText size={40} style={{ margin: '0 auto 14px auto', color: '#8b5cf6' }} />
          <h3 style={{ fontSize: '1.2rem', color: 'var(--text-main)', marginBottom: '8px' }}>
            Generate Patient Clinical Brief
          </h3>
          <p style={{ fontSize: '0.88rem', maxWidth: '480px', margin: '0 auto 20px auto', lineHeight: '1.6' }}>
            Synthesize all uploaded medical records, prescriptions, active diagnoses, and latest observation notes into a standardized consultation & discharge note.
          </p>
          <button
            onClick={handleGenerate}
            className="btn-primary"
            style={{ padding: '10px 24px', fontSize: '0.9rem', margin: '0 auto' }}
          >
            <Sparkles size={16} /> Generate Clinical Brief
          </button>
        </div>
      ) : (
        <div className="glass-panel" style={{
          padding: '28px',
          borderRadius: '16px',
          fontSize: '0.92rem',
          lineHeight: '1.7',
          color: 'var(--text-main)',
          whiteSpace: 'pre-wrap',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)'
        }}>
          {summary}
        </div>
      )}
    </div>
  );
}
