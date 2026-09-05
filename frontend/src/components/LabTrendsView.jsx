import React, { useState, useEffect } from 'react';
import { Activity, TrendingUp, AlertCircle, CheckCircle2, RefreshCw, Layers } from 'lucide-react';
import { fetchPatientLabs } from '../api';

export default function LabTrendsView({ patientId }) {
  const [labData, setLabData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadLabs = async () => {
    if (!patientId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPatientLabs(patientId);
      setLabData(data);
    } catch (err) {
      console.error(err);
      setError('Failed to extract lab trends for active patient.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLabs();
  }, [patientId]);

  const getStatusColor = (status) => {
    if (!status) return 'var(--text-muted)';
    const s = status.toLowerCase();
    if (s.includes('normal')) return '#10b981';
    if (s.includes('elevated') || s.includes('prediabetes') || s.includes('overweight')) return '#f59e0b';
    if (s.includes('high') || s.includes('diabetic') || s.includes('tachycardia')) return '#ef4444';
    return 'var(--primary-teal)';
  };

  return (
    <div style={{
      flex: 1,
      overflowY: 'auto',
      padding: '28px',
      background: 'radial-gradient(circle at 50% 0%, rgba(20, 184, 166, 0.04), transparent 70%), var(--bg-dark)'
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
            CLINICAL BIOMARKER ANALYTICS
          </span>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-main)', margin: '4px 0 0 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity color="var(--primary-teal)" />
            Lab Trends & Vitals: {patientId}
          </h2>
        </div>
        <button
          onClick={loadLabs}
          disabled={loading}
          className="btn-secondary"
          style={{ fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh Biomarkers
        </button>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '300px', color: 'var(--text-muted)', gap: '10px' }}>
          <RefreshCw size={20} className="spin" />
          Extracting clinical observation series and lab values from records...
        </div>
      ) : error ? (
        <div style={{ padding: '20px', borderRadius: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#f87171' }}>
          {error}
        </div>
      ) : !labData || Object.keys(labData.metrics || {}).length === 0 ? (
        <div style={{
          padding: '48px',
          textAlign: 'center',
          borderRadius: '16px',
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px dashed var(--border-color)',
          color: 'var(--text-muted)'
        }}>
          <Layers size={36} style={{ margin: '0 auto 12px auto', color: 'var(--text-dim)' }} />
          <h3 style={{ fontSize: '1.1rem', color: 'var(--text-main)' }}>No Structured Lab Measurements Found</h3>
          <p style={{ fontSize: '0.85rem', maxWidth: '450px', margin: '8px auto 0 auto' }}>
            No standard lab numbers (e.g. blood pressure, glucose, lipids) were detected in this patient's current documents. Upload clinical PDFs or lab reports to populate this dashboard.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
          {Object.entries(labData.metrics).map(([key, metric]) => {
            const statusColor = getStatusColor(metric.latest_status);
            return (
              <div
                key={key}
                className="glass-panel"
                style={{
                  padding: '20px',
                  borderRadius: '14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '14px',
                  transition: 'transform 0.2s ease, border-color 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-dim)' }}>
                      TARGET BIOMARKER
                    </span>
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-main)', margin: '2px 0 0 0' }}>
                      {metric.name}
                    </h3>
                  </div>
                  <span style={{
                    padding: '4px 8px',
                    borderRadius: '8px',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    background: `${statusColor}20`,
                    color: statusColor,
                    border: `1px solid ${statusColor}40`
                  }}>
                    {metric.latest_status}
                  </span>
                </div>

                {/* Latest Value Display */}
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', padding: '12px', borderRadius: '10px', background: 'rgba(0, 0, 0, 0.3)' }}>
                  <span style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-main)' }}>
                    {metric.latest_value}
                  </span>
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                    {metric.unit}
                  </span>
                  <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    Ref: {metric.reference_range}
                  </span>
                </div>

                {/* Time Series History List */}
                <div>
                  <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '8px', fontWeight: 600 }}>
                    Historical Readings ({metric.data_points.length})
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '140px', overflowY: 'auto' }}>
                    {metric.data_points.map((pt, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          padding: '6px 10px',
                          borderRadius: '6px',
                          background: 'rgba(255, 255, 255, 0.02)',
                          fontSize: '0.78rem'
                        }}
                      >
                        <span style={{ color: 'var(--text-muted)' }}>{pt.date}</span>
                        <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                          {pt.value} {metric.unit}
                        </span>
                        <span style={{ color: getStatusColor(pt.status), fontWeight: 600, fontSize: '0.72rem' }}>
                          {pt.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
