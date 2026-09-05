import React, { useState } from 'react';
import { ShieldCheck, AlertTriangle, Info, ChevronDown, ChevronUp } from 'lucide-react';

export default function VerificationBadge({ verification }) {
  const [expanded, setExpanded] = useState(false);

  if (!verification) return null;

  const isVerified = verification.status === 'VERIFIED';
  const confidencePercent = Math.round((verification.confidence_score || 1) * 100);

  return (
    <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
      {/* Badge Pill */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '20px',
            fontSize: '0.78rem',
            fontWeight: 700,
            letterSpacing: '0.03em',
            background: isVerified ? 'var(--badge-verified-bg)' : 'var(--badge-review-bg)',
            color: isVerified ? 'var(--badge-verified-text)' : 'var(--badge-review-text)',
            border: `1px solid ${isVerified ? 'var(--badge-verified-border)' : 'var(--badge-review-border)'}`
          }}>
            {isVerified ? <ShieldCheck size={14} /> : <AlertTriangle size={14} />}
            {isVerified ? 'VERIFIED' : 'NEEDS REVIEW'}
          </span>
          <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            Audit Score: {confidencePercent}%
          </span>
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}
        >
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {expanded ? 'Hide Audit Log' : 'Audit Details'}
        </button>
      </div>

      {/* Expanded Verification Details Drawer */}
      {expanded && (
        <div className="fade-in" style={{
          marginTop: '10px',
          padding: '12px',
          borderRadius: '8px',
          background: 'rgba(0, 0, 0, 0.3)',
          border: '1px solid rgba(255, 255, 255, 0.05)',
          fontSize: '0.8rem',
          lineHeight: '1.4'
        }}>
          <div style={{ color: 'var(--text-muted)', marginBottom: '6px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Info size={14} color="var(--accent-cyan)" /> 2nd-Stage LLM Auditor Analysis:
          </div>
          <div style={{ color: 'var(--text-main)', marginBottom: '8px' }}>
            {verification.reasoning}
          </div>

          {verification.flagged_claims && verification.flagged_claims.length > 0 && (
            <div style={{ marginTop: '8px' }}>
              <div style={{ color: '#fbbf24', fontWeight: 600, fontSize: '0.75rem', marginBottom: '4px' }}>
                Flagged or Unsupported Claims:
              </div>
              <ul style={{ paddingLeft: '18px', color: '#f87171', fontSize: '0.78rem' }}>
                {verification.flagged_claims.map((claim, idx) => (
                  <li key={idx} style={{ marginBottom: '2px' }}>{claim}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
