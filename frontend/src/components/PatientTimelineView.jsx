import React, { useState, useEffect } from 'react';
import { Calendar, Clock, FileText, Activity, ShieldCheck, RefreshCw, Filter } from 'lucide-react';
import { fetchPatientTimeline } from '../api';

export default function PatientTimelineView({ patientId }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('ALL');
  const [error, setError] = useState(null);

  const loadTimeline = async () => {
    if (!patientId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPatientTimeline(patientId);
      setEvents(data.events || []);
    } catch (err) {
      console.error(err);
      setError('Failed to extract longitudinal timeline for active patient.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTimeline();
  }, [patientId]);

  const eventTypes = ['ALL', ...new Set(events.map(e => e.type))];

  const filteredEvents = filterType === 'ALL'
    ? events
    : events.filter(e => e.type === filterType);

  return (
    <div style={{
      flex: 1,
      overflowY: 'auto',
      padding: '28px',
      background: 'radial-gradient(circle at 50% 0%, rgba(59, 130, 246, 0.04), transparent 70%), var(--bg-dark)'
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
            LONGITUDINAL RECORD HISTORY
          </span>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-main)', margin: '4px 0 0 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Calendar color="#3b82f6" />
            Patient Clinical Timeline: {patientId}
          </h2>
        </div>
        <button
          onClick={loadTimeline}
          disabled={loading}
          className="btn-secondary"
          style={{ fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> Reload Timeline
        </button>
      </div>

      {/* Filter Chips */}
      {eventTypes.length > 1 && (
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', marginBottom: '24px', paddingBottom: '4px' }}>
          {eventTypes.map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              style={{
                padding: '6px 14px',
                borderRadius: '20px',
                fontSize: '0.78rem',
                fontWeight: 600,
                border: filterType === type ? '1px solid var(--accent-cyan)' : '1px solid var(--border-color)',
                background: filterType === type ? 'rgba(6, 182, 212, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                color: filterType === type ? 'var(--accent-cyan)' : 'var(--text-muted)',
                cursor: 'pointer',
                whiteSpace: 'nowrap'
              }}
            >
              {type}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '300px', color: 'var(--text-muted)', gap: '10px' }}>
          <RefreshCw size={20} className="spin" />
          Extracting chronological clinical history...
        </div>
      ) : error ? (
        <div style={{ padding: '20px', borderRadius: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', color: '#f87171' }}>
          {error}
        </div>
      ) : filteredEvents.length === 0 ? (
        <div style={{
          padding: '48px',
          textAlign: 'center',
          borderRadius: '16px',
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px dashed var(--border-color)',
          color: 'var(--text-muted)'
        }}>
          <Clock size={36} style={{ margin: '0 auto 12px auto', color: 'var(--text-dim)' }} />
          <h3 style={{ fontSize: '1.1rem', color: 'var(--text-main)' }}>No Timeline Events Recorded</h3>
          <p style={{ fontSize: '0.85rem', maxWidth: '450px', margin: '8px auto 0 auto' }}>
            No dated clinical encounters, diagnoses, or procedures were found in this patient's records.
          </p>
        </div>
      ) : (
        <div style={{ position: 'relative', paddingLeft: '32px' }}>
          {/* Vertical line */}
          <div style={{
            position: 'absolute',
            left: '11px',
            top: '10px',
            bottom: '10px',
            width: '2px',
            background: 'linear-gradient(to bottom, var(--primary-teal), rgba(255, 255, 255, 0.1))'
          }} />

          {/* Event Items */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {filteredEvents.map((evt, idx) => (
              <div key={idx} style={{ position: 'relative' }}>
                {/* Node dot */}
                <div style={{
                  position: 'absolute',
                  left: '-32px',
                  top: '14px',
                  width: '18px',
                  height: '18px',
                  borderRadius: '50%',
                  background: evt.badge_color || 'var(--primary-teal)',
                  border: '3px solid var(--bg-dark)',
                  boxShadow: `0 0 10px ${evt.badge_color || 'var(--primary-teal)'}80`
                }} />

                <div className="glass-panel" style={{
                  padding: '16px 20px',
                  borderRadius: '12px',
                  borderLeft: `4px solid ${evt.badge_color || 'var(--primary-teal)'}`
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '6px' }}>
                    <span style={{
                      padding: '3px 8px',
                      borderRadius: '6px',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      background: `${evt.badge_color}25`,
                      color: evt.badge_color,
                      border: `1px solid ${evt.badge_color}50`
                    }}>
                      {evt.type}
                    </span>
                    <span className="mono" style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Calendar size={13} /> {evt.date}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.98rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '6px' }}>
                    {evt.title}
                  </div>

                  <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                    {evt.details}
                  </div>

                  <div style={{ marginTop: '10px', fontSize: '0.72rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <FileText size={12} /> Source: {evt.source}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
