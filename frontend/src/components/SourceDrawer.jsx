import React from 'react';
import { X, FileText, CheckCircle, Percent, Hash } from 'lucide-react';

export default function SourceDrawer({ isOpen, onClose, source, allSources = [], onSelectSource }) {
  if (!isOpen || !source) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      right: 0,
      bottom: 0,
      width: '420px',
      maxWidth: '90vw',
      background: 'rgba(15, 23, 42, 0.96)',
      backdropFilter: 'blur(16px)',
      borderLeft: '1px solid var(--border-color)',
      boxShadow: '-10px 0 30px rgba(0, 0, 0, 0.5)',
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column',
      animation: 'slideLeft 0.25s ease-out'
    }}>
      {/* Drawer Header */}
      <div style={{
        padding: '18px 20px',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(0, 0, 0, 0.2)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileText size={18} color="var(--primary-teal)" />
          <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
            Source Inspector
          </h3>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: '6px',
            display: 'flex'
          }}
        >
          <X size={20} />
        </button>
      </div>

      {/* Source Selector Pills (if multiple sources available) */}
      {allSources.length > 1 && (
        <div style={{
          padding: '10px 20px',
          display: 'flex',
          gap: '8px',
          overflowX: 'auto',
          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          background: 'rgba(0, 0, 0, 0.1)'
        }}>
          {allSources.map((s) => (
            <button
              key={s.source_id}
              onClick={() => onSelectSource && onSelectSource(s)}
              style={{
                padding: '4px 10px',
                borderRadius: '12px',
                fontSize: '0.75rem',
                fontWeight: 600,
                border: s.source_id === source.source_id ? '1px solid var(--primary-teal)' : '1px solid var(--border-color)',
                background: s.source_id === source.source_id ? 'rgba(20, 184, 166, 0.2)' : 'rgba(255, 255, 255, 0.04)',
                color: s.source_id === source.source_id ? 'var(--primary-teal)' : 'var(--text-muted)',
                cursor: 'pointer',
                whiteSpace: 'nowrap'
              }}
            >
              Source {s.source_id}
            </button>
          ))}
        </div>
      )}

      {/* Drawer Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Document Info Card */}
        <div style={{
          padding: '14px',
          borderRadius: '10px',
          background: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid rgba(255, 255, 255, 0.08)'
        }}>
          <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '4px' }}>
            DOCUMENT FILE
          </div>
          <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--accent-cyan)', wordBreak: 'break-all' }}>
            {source.filename}
          </div>
          <div style={{ display: 'flex', gap: '16px', marginTop: '10px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            <span>Page: <strong style={{ color: 'var(--text-main)' }}>{source.page || 1}</strong></span>
            <span>Type: <strong style={{ color: 'var(--text-main)' }}>{source.document_type || 'Record'}</strong></span>
          </div>
        </div>

        {/* Relevance Metrics */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '10px'
        }}>
          <div style={{
            padding: '12px',
            borderRadius: '8px',
            background: 'rgba(20, 184, 166, 0.08)',
            border: '1px solid rgba(20, 184, 166, 0.2)'
          }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>HYBRID MATCH SCORE</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--primary-teal)', marginTop: '4px' }}>
              {(source.score * 100).toFixed(1)}%
            </div>
          </div>
          <div style={{
            padding: '12px',
            borderRadius: '8px',
            background: 'rgba(6, 182, 212, 0.08)',
            border: '1px solid rgba(6, 182, 212, 0.2)'
          }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>VECTOR SIMILARITY</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-cyan)', marginTop: '4px' }}>
              {((source.vector_score || source.score) * 100).toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Verbatim Excerpt */}
        <div>
          <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '8px', fontWeight: 600 }}>
            VERBATIM RETRIEVED EXCERPT
          </div>
          <div style={{
            padding: '16px',
            borderRadius: '10px',
            background: 'rgba(0, 0, 0, 0.5)',
            border: '1px solid var(--border-color)',
            fontSize: '0.86rem',
            lineHeight: '1.6',
            color: 'var(--text-main)',
            whiteSpace: 'pre-wrap',
            fontFamily: 'inherit'
          }}>
            {source.text}
          </div>
        </div>
      </div>
    </div>
  );
}
