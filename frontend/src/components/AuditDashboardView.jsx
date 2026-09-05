import React, { useState, useEffect } from 'react';
import { ShieldCheck, AlertTriangle, Clock, ThumbsUp, ThumbsDown, RefreshCw, BarChart3, CheckCircle2 } from 'lucide-react';
import { fetchAuditLogs } from '../api';

export default function AuditDashboardView() {
  const [auditData, setAuditData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAuditLogs(50);
      setAuditData(data);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch system audit logs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  return (
    <div style={{
      flex: 1,
      overflowY: 'auto',
      padding: '28px',
      background: 'radial-gradient(circle at 50% 0%, rgba(16, 185, 129, 0.04), transparent 70%), var(--bg-dark)'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '24px'
      }}>
        <div>
          <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-dim)', letterSpacing: '0.05em' }}>
            REGULATORY COMPLIANCE & SAFETY GOVERNANCE
          </span>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-main)', margin: '4px 0 0 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck color="#10b981" />
            Audit Trail & Verification Dashboard
          </h2>
        </div>
        <button
          onClick={loadLogs}
          disabled={loading}
          className="btn-secondary"
          style={{ fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh Logs
        </button>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '300px', color: 'var(--text-muted)', gap: '10px' }}>
          <RefreshCw size={20} className="spin" />
          Loading audit logs and verification metrics...
        </div>
      ) : error ? (
        <div style={{ padding: '20px', borderRadius: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#f87171' }}>
          {error}
        </div>
      ) : !auditData ? null : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Top Metric Cards */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px'
          }}>
            <div className="glass-panel" style={{ padding: '18px', borderRadius: '12px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>TOTAL QUERIES LOGGED</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--text-main)', marginTop: '6px' }}>
                {auditData.total_queries}
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '18px', borderRadius: '12px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>VERIFIED RATE</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#10b981', marginTop: '6px' }}>
                {auditData.verified_percentage}%
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '18px', borderRadius: '12px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>AVG AUDIT CONFIDENCE</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--accent-cyan)', marginTop: '6px' }}>
                {(auditData.avg_confidence * 100).toFixed(0)}%
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '18px', borderRadius: '12px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>AVG LATENCY (2 LLM PASSES)</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#f59e0b', marginTop: '6px' }}>
                {auditData.avg_latency_sec}s
              </div>
            </div>

            <div className="glass-panel" style={{ padding: '18px', borderRadius: '12px' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>CLINICIAN FEEDBACK</div>
              <div style={{ display: 'flex', gap: '14px', alignItems: 'center', marginTop: '6px' }}>
                <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <ThumbsUp size={16} /> {auditData.feedback_stats?.thumbs_up || 0}
                </span>
                <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ef4444', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <ThumbsDown size={16} /> {auditData.feedback_stats?.thumbs_down || 0}
                </span>
              </div>
            </div>
          </div>

          {/* Audit Table */}
          <div className="glass-panel" style={{ padding: '20px', borderRadius: '14px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '14px' }}>
              Recent Audited Interactions ({auditData.recent_entries?.length || 0})
            </h3>

            {(!auditData.recent_entries || auditData.recent_entries.length === 0) ? (
              <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                No interactions logged yet. Run a chat query to generate audit records.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-dim)', textAlign: 'left' }}>
                      <th style={{ padding: '10px' }}>Timestamp</th>
                      <th style={{ padding: '10px' }}>Patient ID</th>
                      <th style={{ padding: '10px' }}>Question</th>
                      <th style={{ padding: '10px' }}>Status</th>
                      <th style={{ padding: '10px' }}>Confidence</th>
                      <th style={{ padding: '10px' }}>Latency</th>
                      <th style={{ padding: '10px' }}>Feedback</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditData.recent_entries.map((entry, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <td style={{ padding: '10px', color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>
                          {entry.timestamp}
                        </td>
                        <td className="mono" style={{ padding: '10px', color: 'var(--primary-teal)', fontWeight: 600 }}>
                          {entry.patient_id}
                        </td>
                        <td style={{ padding: '10px', color: 'var(--text-main)', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {entry.question}
                        </td>
                        <td style={{ padding: '10px' }}>
                          <span style={{
                            padding: '3px 8px',
                            borderRadius: '6px',
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            background: entry.verifier_status === 'VERIFIED' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                            color: entry.verifier_status === 'VERIFIED' ? '#10b981' : '#f59e0b',
                            border: entry.verifier_status === 'VERIFIED' ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(245, 158, 11, 0.4)'
                          }}>
                            {entry.verifier_status}
                          </span>
                        </td>
                        <td style={{ padding: '10px', color: 'var(--text-muted)' }}>
                          {(entry.confidence_score * 100).toFixed(0)}%
                        </td>
                        <td style={{ padding: '10px', color: 'var(--text-muted)' }}>
                          {entry.latency_sec}s
                        </td>
                        <td style={{ padding: '10px' }}>
                          {entry.clinician_feedback?.rating === 'THUMBS_UP' && (
                            <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '3px' }}>
                              <ThumbsUp size={12} /> Positive
                            </span>
                          )}
                          {entry.clinician_feedback?.rating === 'THUMBS_DOWN' && (
                            <span style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: '3px' }}>
                              <ThumbsDown size={12} /> Flagged
                            </span>
                          )}
                          {!entry.clinician_feedback && (
                            <span style={{ color: 'var(--text-dim)' }}>—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
