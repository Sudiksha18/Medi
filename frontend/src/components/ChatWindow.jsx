import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send, User, Bot, FileText, ChevronDown, ChevronRight,
  Loader2, Sparkles, ThumbsUp, ThumbsDown, Download, ExternalLink, ShieldCheck,
  RefreshCw, Clock
} from 'lucide-react';
import VerificationBadge from './VerificationBadge';
import SourceDrawer from './SourceDrawer';
import { sendChatMessage, submitFeedback, fetchPatientDocuments } from '../api';

const QUICK_PROMPTS = [
  "What active medications and prescriptions are recorded?",
  "What were the patient's blood pressure and lab readings?",
  "List documented medical conditions and diagnoses.",
  "What surgical procedures or medical interventions occurred?"
];

export default function ChatWindow({ patientId, onOpenUpload, docRefreshKey }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [openSources, setOpenSources] = useState({});
  const [feedbackGiven, setFeedbackGiven] = useState({});
  const [docSummary, setDocSummary] = useState({ has_documents: false, total_documents: 0, total_chunks: 0, documents: [] });
  const [rateLimitCountdown, setRateLimitCountdown] = useState({}); // msgId -> seconds remaining
  const retryQueryRef = useRef({}); // msgId -> { patientId, queryText }

  // Source Drawer state
  const [selectedSource, setSelectedSource] = useState(null);
  const [activeSourcesPool, setActiveSourcesPool] = useState([]);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    if (patientId) {
      fetchPatientDocuments(patientId)
        .then(res => setDocSummary(res || { has_documents: false, total_documents: 0, total_chunks: 0, documents: [] }))
        .catch(err => console.error('Failed to fetch doc summary:', err));
    }
  }, [patientId, docRefreshKey]);

  // Reset conversation when patient changes
  useEffect(() => {
    setMessages([
      {
        id: 'welcome',
        sender: 'system',
        text: `Active Patient Session: ${patientId}. Verified RAG is active. Ask clinical questions or use the quick chips below.`
      }
    ]);
    setFeedbackGiven({});
  }, [patientId]);

  const toggleSources = (msgId) => {
    setOpenSources(prev => ({ ...prev, [msgId]: !prev[msgId] }));
  };

  const handleOpenSourceDrawer = (src, allSources) => {
    setSelectedSource(src);
    setActiveSourcesPool(allSources);
    setIsDrawerOpen(true);
  };

  const handleFeedback = async (msgId, auditId, rating) => {
    if (!auditId) return;
    try {
      await submitFeedback(auditId, rating);
      setFeedbackGiven(prev => ({ ...prev, [msgId]: rating }));
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    }
  };

  const handleSend = async (e, customText = null) => {
    if (e) e.preventDefault();
    const queryText = customText || input.trim();
    if (!queryText || loading || !patientId) return;

    setInput('');

    const userMsg = {
      id: Date.now().toString(),
      sender: 'user',
      text: queryText
    };

    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await sendChatMessage(patientId, queryText);
      const botMsg = {
        id: (Date.now() + 1).toString(),
        sender: 'bot',
        text: res.answer,
        sources: res.sources,
        verification: res.verification,
        auditId: res.audit_id,
        latency: res.latency_sec
      };
      setMessages(prev => [...prev, botMsg]);
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.detail || err.message || '';
      const isRateLimit = detail.toLowerCase().includes('rate limit') ||
                          detail.toLowerCase().includes('429') ||
                          detail.toLowerCase().includes('quota');
      const errorId = (Date.now() + 1).toString();
      const errorMsg = {
        id: errorId,
        sender: 'error',
        isRateLimit,
        retryQuery: queryText,
        text: isRateLimit
          ? '⏱ Mistral API rate limit reached (free-tier: ~5 req/min). Click Retry below or wait 30–60 seconds.'
          : detail || 'An error occurred while retrieving medical records. Check backend connection.'
      };
      setMessages(prev => [...prev, errorMsg]);

      // If rate-limited, store the query for one-click retry and start a 45s countdown
      if (isRateLimit) {
        retryQueryRef.current[errorId] = { patientId, queryText };
        let secs = 45;
        setRateLimitCountdown(prev => ({ ...prev, [errorId]: secs }));
        const timer = setInterval(() => {
          secs -= 1;
          setRateLimitCountdown(prev => ({ ...prev, [errorId]: secs }));
          if (secs <= 0) clearInterval(timer);
        }, 1000);
      }
    } finally {
      setLoading(false);
    }
  };

  const exportChat = () => {
    if (messages.length <= 1) return;
    const lines = messages.map(m => `[${m.sender.toUpperCase()}] ${m.text}\n`).join('\n');
    const blob = new Blob([lines], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat_transcript_${patientId}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      position: 'relative',
      background: 'radial-gradient(circle at 50% 0%, rgba(20, 184, 166, 0.05), transparent 70%), var(--bg-dark)'
    }}>
      {/* Top Header */}
      <header style={{
        padding: '14px 24px',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(11, 15, 25, 0.8)',
        backdropFilter: 'blur(10px)'
      }}>
        <div>
          <span style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>
            CURRENT PATIENT CONTEXT
          </span>
          <h2 className="mono" style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--primary-teal)', display: 'flex', alignItems: 'center', gap: '12px', margin: 0 }}>
            {patientId}
            {docSummary.has_documents ? (
              <span style={{
                padding: '3px 10px',
                borderRadius: '12px',
                background: 'rgba(20, 184, 166, 0.15)',
                border: '1px solid rgba(20, 184, 166, 0.3)',
                color: 'var(--primary-teal)',
                fontSize: '0.74rem',
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}>
                <FileText size={12} /> {docSummary.total_documents} Document{docSummary.total_documents > 1 ? 's' : ''} Present ({docSummary.total_chunks} Chunks)
              </span>
            ) : (
              <span style={{
                padding: '3px 10px',
                borderRadius: '12px',
                background: 'rgba(245, 158, 11, 0.15)',
                border: '1px solid rgba(245, 158, 11, 0.3)',
                color: '#f59e0b',
                fontSize: '0.74rem',
                fontWeight: 600
              }}>
                ⚠️ No documents uploaded yet
              </span>
            )}
          </h2>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={exportChat} className="btn-secondary" style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Download size={14} /> Export Transcript
          </button>
          <button onClick={onOpenUpload} className="btn-secondary" style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <FileText size={14} /> Upload Records
          </button>
        </div>
      </header>

      {/* Messages Feed */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px'
      }}>
        {messages.map((msg) => {
          if (msg.sender === 'system') {
            return (
              <div key={msg.id} style={{
                margin: '0 auto',
                padding: '8px 16px',
                borderRadius: '20px',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                fontSize: '0.8rem',
                color: 'var(--text-muted)',
                textAlign: 'center',
                maxWidth: '80%'
              }}>
                {msg.text}
              </div>
            );
          }

          if (msg.sender === 'user') {
            return (
              <div key={msg.id} className="fade-in" style={{
                alignSelf: 'flex-end',
                maxWidth: '75%',
                display: 'flex',
                gap: '12px'
              }}>
                <div style={{
                  background: 'linear-gradient(135deg, rgba(20, 184, 166, 0.2), rgba(6, 182, 212, 0.2))',
                  border: '1px solid rgba(20, 184, 166, 0.4)',
                  padding: '14px 18px',
                  borderRadius: '18px 18px 2px 18px',
                  color: 'var(--text-main)',
                  fontSize: '0.92rem',
                  lineHeight: '1.5'
                }}>
                  {msg.text}
                </div>
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  background: 'rgba(255, 255, 255, 0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <User size={18} color="var(--text-main)" />
                </div>
              </div>
            );
          }

          if (msg.sender === 'bot') {
            const isSourcesOpen = openSources[msg.id];
            const currentRating = feedbackGiven[msg.id];

            return (
              <div key={msg.id} className="fade-in" style={{
                alignSelf: 'flex-start',
                maxWidth: '82%',
                display: 'flex',
                gap: '12px'
              }}>
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, var(--primary-teal), var(--accent-cyan))',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  color: '#000'
                }}>
                  <Bot size={20} />
                </div>
                <div className="glass-panel" style={{
                  padding: '18px',
                  borderRadius: '2px 18px 18px 18px',
                  flex: 1
                }}>
                  {/* Generated Answer Content */}
                  <div style={{ fontSize: '0.95rem', lineHeight: '1.6', color: 'var(--text-main)', whiteSpace: 'pre-wrap' }}>
                    {msg.text}
                  </div>

                  {/* Sources Accordion */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
                      <button
                        onClick={() => toggleSources(msg.id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--accent-cyan)',
                          cursor: 'pointer',
                          fontSize: '0.8rem',
                          fontWeight: 600,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        {isSourcesOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        Retrieved Evidence Sources ({msg.sources.length}) — Click source to inspect
                      </button>

                      {isSourcesOpen && (
                        <div className="fade-in" style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {msg.sources.map((src) => (
                            <div
                              key={src.source_id}
                              onClick={() => handleOpenSourceDrawer(src, msg.sources)}
                              style={{
                                padding: '10px 12px',
                                borderRadius: '8px',
                                background: 'rgba(0, 0, 0, 0.4)',
                                border: '1px solid rgba(255, 255, 255, 0.05)',
                                fontSize: '0.8rem',
                                cursor: 'pointer',
                                transition: 'background 0.2s ease, border-color 0.2s ease'
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.borderColor = 'var(--primary-teal)';
                                e.currentTarget.style.background = 'rgba(20, 184, 166, 0.08)';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.05)';
                                e.currentTarget.style.background = 'rgba(0, 0, 0, 0.4)';
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontWeight: 600, color: 'var(--primary-teal)' }}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  [Source {src.source_id}] {src.filename} (Page {src.page})
                                  <ExternalLink size={12} color="var(--accent-cyan)" />
                                </span>
                                <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                                  Relevance: {(src.score * 100).toFixed(1)}%
                                </span>
                              </div>
                              <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.78rem' }}>
                                "{src.text}"
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Verification Badge + Feedback Buttons */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', flexWrap: 'wrap', gap: '10px' }}>
                    <VerificationBadge verification={msg.verification} />

                    {/* Feedback Rating */}
                    {msg.auditId && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>Clinician Audit:</span>
                        <button
                          onClick={() => handleFeedback(msg.id, msg.auditId, 'THUMBS_UP')}
                          style={{
                            background: currentRating === 'THUMBS_UP' ? 'rgba(16, 185, 129, 0.25)' : 'none',
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                            borderRadius: '6px',
                            color: currentRating === 'THUMBS_UP' ? '#10b981' : 'var(--text-muted)',
                            padding: '3px 7px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontSize: '0.72rem'
                          }}
                        >
                          <ThumbsUp size={12} /> Accurate
                        </button>
                        <button
                          onClick={() => handleFeedback(msg.id, msg.auditId, 'THUMBS_DOWN')}
                          style={{
                            background: currentRating === 'THUMBS_DOWN' ? 'rgba(239, 68, 68, 0.25)' : 'none',
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                            borderRadius: '6px',
                            color: currentRating === 'THUMBS_DOWN' ? '#ef4444' : 'var(--text-muted)',
                            padding: '3px 7px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontSize: '0.72rem'
                          }}
                        >
                          <ThumbsDown size={12} /> Flag Issue
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          }

          if (msg.sender === 'error') {
            const countdown = rateLimitCountdown[msg.id] ?? 0;
            const canRetry = !loading && countdown <= 0;
            return (
              <div key={msg.id} style={{
                padding: '14px 18px',
                borderRadius: '12px',
                background: msg.isRateLimit ? 'rgba(251, 146, 60, 0.12)' : 'rgba(239, 68, 68, 0.15)',
                border: `1px solid ${msg.isRateLimit ? 'rgba(251, 146, 60, 0.4)' : 'rgba(239, 68, 68, 0.3)'}`,
                color: msg.isRateLimit ? '#fb923c' : '#f87171',
                fontSize: '0.85rem',
                alignSelf: 'center',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                maxWidth: '520px',
                width: '100%'
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                  {msg.isRateLimit ? <Clock size={16} style={{ flexShrink: 0, marginTop: '2px' }} /> : null}
                  <span>{msg.text}</span>
                </div>
                {msg.isRateLimit && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <button
                      id={`retry-btn-${msg.id}`}
                      disabled={!canRetry}
                      onClick={() => {
                        const stored = retryQueryRef.current[msg.id];
                        if (stored) {
                          // Remove old error message and retry
                          setMessages(prev => prev.filter(m => m.id !== msg.id));
                          handleSend(null, stored.queryText);
                        }
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '7px 16px',
                        borderRadius: '8px',
                        fontSize: '0.82rem',
                        fontWeight: 700,
                        border: '1px solid rgba(251, 146, 60, 0.5)',
                        background: canRetry ? 'rgba(251, 146, 60, 0.2)' : 'rgba(255,255,255,0.04)',
                        color: canRetry ? '#fb923c' : 'rgba(251,146,60,0.4)',
                        cursor: canRetry ? 'pointer' : 'not-allowed',
                        transition: 'all 0.2s ease'
                      }}
                    >
                      <RefreshCw size={13} />
                      {canRetry ? 'Retry Now' : `Retry in ${countdown}s`}
                    </button>
                    {countdown > 0 && (
                      <span style={{ fontSize: '0.78rem', color: 'rgba(251,146,60,0.6)' }}>
                        Cooling down — Mistral free-tier limit resets in ~{countdown}s
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          }

          return null;
        })}

        {loading && (
          <div style={{ alignSelf: 'flex-start', display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--primary-teal), var(--accent-cyan))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#000'
            }}>
              <Sparkles size={18} className="pulsing" />
            </div>
            <div className="glass-panel" style={{ padding: '12px 18px', borderRadius: '18px', fontSize: '0.85rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
              Executing hybrid retrieval, generating grounded answer & running 2nd-stage audit...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Clinical Prompts Bar */}
      <div style={{
        padding: '8px 24px 0 24px',
        display: 'flex',
        gap: '8px',
        overflowX: 'auto',
        background: 'rgba(11, 15, 25, 0.6)'
      }}>
        {QUICK_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            disabled={loading}
            onClick={() => handleSend(null, prompt)}
            style={{
              padding: '6px 12px',
              borderRadius: '16px',
              fontSize: '0.74rem',
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'background 0.2s, color 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = 'var(--primary-teal)';
              e.currentTarget.style.background = 'rgba(20, 184, 166, 0.1)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = 'var(--text-muted)';
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
            }}
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input Footer */}
      <footer style={{
        padding: '14px 24px 18px 24px',
        borderTop: '1px solid var(--border-color)',
        background: 'rgba(11, 15, 25, 0.9)'
      }}>
        <form onSubmit={(e) => handleSend(e)} style={{ display: 'flex', gap: '12px' }}>
          <input
            type="text"
            placeholder={`Ask a question about ${patientId}'s records (e.g. medications, labs, diagnoses)...`}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            style={{
              flex: 1,
              padding: '14px 18px',
              background: 'rgba(0, 0, 0, 0.4)',
              border: '1px solid var(--border-color)',
              borderRadius: '10px',
              color: 'var(--text-main)',
              fontSize: '0.95rem',
              outline: 'none'
            }}
          />
          <button
            type="submit"
            className="btn-primary"
            disabled={loading || !input.trim()}
            style={{ padding: '0 24px' }}
          >
            <Send size={18} /> Send
          </button>
        </form>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textAlign: 'center', marginTop: '8px' }}>
          Dual-LLM Verified RAG • Hybrid Retrieval • Strict Patient Isolation
        </div>
      </footer>

      {/* Source Drawer */}
      <SourceDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        source={selectedSource}
        allSources={activeSourcesPool}
        onSelectSource={(src) => setSelectedSource(src)}
      />
    </main>
  );
}
