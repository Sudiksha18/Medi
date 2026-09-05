import React, { useState, useEffect } from 'react';
import { ShieldAlert, Activity, Heart, Stethoscope, Download, RefreshCw, FileCode, CheckCircle2, AlertTriangle } from 'lucide-react';
import { fetchPatientRiskCalculator, fetchPatientFhirBundle } from '../api';

export default function ClinicalRiskCalculatorView({ patientId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fhirData, setFhirData] = useState(null);
  const [showFhirModal, setShowFhirModal] = useState(false);

  const loadRiskProfile = async () => {
    if (!patientId) return;
    setLoading(true);
    try {
      const res = await fetchPatientRiskCalculator(patientId);
      setData(res);
    } catch (err) {
      console.error('Failed to calculate risk profile:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRiskProfile();
  }, [patientId]);

  const handleDownloadFhir = async () => {
    try {
      const bundle = await fetchPatientFhirBundle(patientId);
      setFhirData(bundle);
      setShowFhirModal(true);
    } catch (err) {
      console.error('Error fetching FHIR bundle:', err);
    }
  };

  const exportFhirFile = () => {
    if (!fhirData) return;
    const blob = new Blob([JSON.stringify(fhirData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `FHIR_R4_Bundle_${patientId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
        <RefreshCw size={24} className="spin" style={{ marginRight: '10px' }} /> Computing Clinical Risk Profile & Differential Diagnoses...
      </div>
    );
  }

  const ascvd = data?.ascvd_risk || {};
  const kidney = data?.kidney_function || {};
  const differentials = data?.differential_diagnoses || [];

  return (
    <div style={{ flex: 1, padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(15, 23, 42, 0.8)', padding: '16px 20px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
        <div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-main)' }}>
            <Activity color="var(--primary-teal)" /> Clinical Risk & Differential Diagnosis Dashboard
          </h2>
          <p style={{ fontSize: '0.84rem', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
            Automated Framingham/ASCVD Risk, eGFR Kidney Staging, and ICD-10 Differential Screening for Patient: <strong className="mono" style={{ color: 'var(--primary-teal)' }}>{patientId}</strong>
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={loadRiskProfile} className="btn-secondary" style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <RefreshCw size={14} /> Recalculate
          </button>
          <button onClick={handleDownloadFhir} className="btn-primary" style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <FileCode size={14} /> Export FHIR R4 JSON
          </button>
        </div>
      </div>

      {/* Risk Metrics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
        {/* ASCVD Risk Card */}
        <div style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Heart size={16} color="#ef4444" /> 10-Yr ASCVD Risk Score
            </span>
            <span style={{
              padding: '2px 10px', borderRadius: '12px', fontSize: '0.72rem', fontWeight: 700,
              background: ascvd.category === 'HIGH_RISK' ? 'rgba(239, 68, 68, 0.2)' : (ascvd.category === 'MODERATE_RISK' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(52, 211, 153, 0.2)'),
              color: ascvd.category === 'HIGH_RISK' ? '#ef4444' : (ascvd.category === 'MODERATE_RISK' ? '#f59e0b' : '#34d399')
            }}>
              {ascvd.category || 'LOW_RISK'}
            </span>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '8px' }}>
            {ascvd.risk_percentage}% <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 400 }}>10-Yr CVD Event Probability</span>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: '1.4', margin: 0 }}>
            {ascvd.recommendation}
          </p>
        </div>

        {/* eGFR Kidney Staging Card */}
        <div style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Activity size={16} color="#3b82f6" /> Renal Function (eGFR)
            </span>
            <span style={{
              padding: '2px 10px', borderRadius: '12px', fontSize: '0.72rem', fontWeight: 700,
              background: kidney.status === 'NORMAL' ? 'rgba(52, 211, 153, 0.2)' : 'rgba(245, 158, 11, 0.2)',
              color: kidney.status === 'NORMAL' ? '#34d399' : '#f59e0b'
            }}>
              {kidney.stage}
            </span>
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-main)', marginBottom: '8px' }}>
            {kidney.egfr} <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontWeight: 400 }}>mL/min/1.73m²</span>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: '1.4', margin: 0 }}>
            Based on CKD-EPI formula proxy using Serum Creatinine ({kidney.creatinine_used} mg/dL).
          </p>
        </div>
      </div>

      {/* ICD-10 Differential Diagnoses List */}
      <div style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '20px' }}>
        <h3 style={{ fontSize: '0.92rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)', margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Stethoscope size={18} color="var(--primary-teal)" /> ICD-10 Aligned Differential Diagnoses
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {differentials.map((item, idx) => (
            <div key={idx} style={{
              padding: '12px 16px', borderRadius: '8px', background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(255, 255, 255, 0.06)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span className="mono" style={{ background: 'rgba(20, 184, 166, 0.15)', color: 'var(--primary-teal)', padding: '4px 8px', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 700 }}>
                  {item.code}
                </span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-main)' }}>{item.condition}</div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Evidence: {item.evidence}</div>
                </div>
              </div>

              <span style={{
                fontSize: '0.74rem', fontWeight: 700, padding: '3px 8px', borderRadius: '10px',
                background: item.confidence === 'HIGH' ? 'rgba(52, 211, 153, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                color: item.confidence === 'HIGH' ? '#34d399' : '#f59e0b'
              }}>
                {item.confidence} CONFIDENCE
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* FHIR Bundle Export Modal */}
      {showFhirModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '20px' }}>
          <div style={{ background: 'var(--bg-dark)', border: '1px solid var(--border-color)', borderRadius: '14px', width: '600px', maxWidth: '100%', maxHeight: '80vh', display: 'flex', flexDirection: 'column', padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileCode color="var(--primary-teal)" /> HL7 FHIR R4 JSON Bundle ({patientId})
              </h3>
              <button onClick={() => setShowFhirModal(false)} className="btn-secondary" style={{ padding: '4px 10px' }}>✕</button>
            </div>

            <pre style={{ flex: 1, overflowY: 'auto', background: 'rgba(0,0,0,0.5)', padding: '14px', borderRadius: '8px', fontSize: '0.76rem', color: '#34d399', fontFamily: 'monospace' }}>
              {JSON.stringify(fhirData, null, 2)}
            </pre>

            <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button onClick={exportFhirFile} className="btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Download size={15} /> Download FHIR R4 JSON
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
