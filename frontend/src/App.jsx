import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';

function renderInline(str, onCitationClick, onCitationHover) {
  if (!str) return '';
  // Strip any accidental markdown '#' hashtags so raw syntax never renders
  const cleanedStr = str.replace(/#{1,6}\s*/g, '');
  const parts = cleanedStr.split(/(\*\*.*?\*\*|\[Doc:.*?\])/g);
  return parts.map((part, idx) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={idx} style={{ color: '#ffffff', fontWeight: 700 }}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('[Doc:') && part.endsWith(']')) {
      return (
        <span
          key={idx}
          onClick={() => onCitationClick && onCitationClick(part)}
          onMouseEnter={() => onCitationHover && onCitationHover(part)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '2px 8px',
            borderRadius: '6px',
            background: 'rgba(56, 189, 248, 0.2)',
            border: '1px solid rgba(56, 189, 248, 0.5)',
            color: '#38BDF8',
            fontSize: '11px',
            fontWeight: 700,
            cursor: 'pointer',
            margin: '0 4px',
            verticalAlign: 'baseline',
            transition: 'all 0.2s ease',
            boxShadow: '0 2px 6px rgba(56, 189, 248, 0.2)'
          }}
          title="Click or hover to highlight raw document snippet in Provenance"
        >
          📄 {part.slice(1, -1)}
        </span>
      );
    }
    return part;
  });
}

function FormattedMarkdown({ text, onCitationClick, onCitationHover }) {
  if (!text) return null;

  // Clean any raw hashtags before rendering
  const blocks = text.split(/\n{2,}/);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '14px', lineHeight: '1.7', color: '#F1F5F9' }}>
      {blocks.map((block, bIdx) => {
        let trimmed = block.trim();
        if (!trimmed) return null;

        // Strip leading # symbols completely if present
        let isHeader = false;
        let headerLevel = 2;
        if (trimmed.startsWith('#')) {
          const match = trimmed.match(/^(#{1,6})\s*(.*)/s);
          if (match) {
            isHeader = true;
            headerLevel = match[1].length;
            trimmed = match[2];
          }
        }

        // Section header recognition: render without any # hashtag
        if (
          isHeader ||
          trimmed.startsWith('Governing Policy Verdict:') ||
          trimmed.startsWith('FLAGGED FOR HUMAN REVIEW:') ||
          trimmed.startsWith('Conflict Reasons:') ||
          trimmed.startsWith('Competing Positions') ||
          trimmed.startsWith('Precedence Justification') ||
          trimmed.startsWith('Previous Version Context') ||
          trimmed.startsWith('⚠️ Ripple Effect Tracker')
        ) {
          const fontSize = headerLevel <= 2 ? '16px' : headerLevel === 3 ? '15px' : '13.5px';
          const color = trimmed.includes('FLAGGED')
            ? '#FCA5A5'
            : trimmed.includes('Verdict')
            ? '#38BDF8'
            : trimmed.includes('Ripple')
            ? '#FCD34D'
            : '#93C5FD';
          return (
            <div
              key={bIdx}
              style={{
                margin: '6px 0 2px 0',
                fontSize,
                fontWeight: 800,
                color,
                letterSpacing: '-0.01em',
                borderBottom: trimmed.includes('Verdict') || trimmed.includes('FLAGGED') ? '1px solid rgba(148, 163, 184, 0.2)' : 'none',
                paddingBottom: '4px'
              }}
            >
              {renderInline(trimmed, onCitationClick, onCitationHover)}
            </div>
          );
        }

        // Blockquote
        if (trimmed.startsWith('>')) {
          const content = trimmed.replace(/^>\s*/gm, '');
          return (
            <div key={bIdx} style={{
              borderLeft: '3px solid #38BDF8',
              background: 'rgba(56, 189, 248, 0.08)',
              padding: '10px 14px',
              borderRadius: '0 8px 8px 0',
              fontStyle: 'italic',
              color: '#CBD5E1'
            }}>
              {renderInline(content, onCitationClick, onCitationHover)}
            </div>
          );
        }

        // Bullet list
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          const items = trimmed.split('\n').filter(line => line.trim().startsWith('- ') || line.trim().startsWith('* '));
          return (
            <ul key={bIdx} style={{ margin: 0, paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {items.map((it, iIdx) => (
                <li key={iIdx}>
                  {renderInline(it.replace(/^[-*]\s*/, ''), onCitationClick, onCitationHover)}
                </li>
              ))}
            </ul>
          );
        }

        // Horizontal Rule
        if (trimmed === '---') {
          return <hr key={bIdx} style={{ border: 'none', borderTop: '1px solid rgba(148, 163, 184, 0.15)', margin: '8px 0' }} />;
        }

        // Normal paragraph
        return (
          <p key={bIdx} style={{ margin: 0 }}>
            {renderInline(trimmed, onCitationClick, onCitationHover)}
          </p>
        );
      })}
    </div>
  );
}

export default function App() {
  // Query & state
  const [query, setQuery] = useState('What is the annual paid leave entitlement in days?');
  const [targetDate, setTargetDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeRightTab, setActiveRightTab] = useState('critic'); // 'critic' | 'provenance' | 'vault'
  const [selectedCitation, setSelectedCitation] = useState(null);
  const [highlightedDoc, setHighlightedDoc] = useState(null);

  const handleCitationFocus = (citationText) => {
    setActiveRightTab('provenance');
    let target = '';
    if (typeof citationText === 'string') {
      const match = citationText.match(/\[Doc:\s*([^,]+)/);
      target = match ? match[1].trim() : citationText.trim();
    } else if (citationText?.title) {
      target = citationText.title.trim();
    }
    setHighlightedDoc(target);

    setTimeout(() => {
      const allCards = document.querySelectorAll('[data-doc-title]');
      for (const card of allCards) {
        const title = card.getAttribute('data-doc-title') || '';
        if (title.toLowerCase().includes(target.toLowerCase()) || target.toLowerCase().includes(title.toLowerCase())) {
          card.scrollIntoView({ behavior: 'smooth', block: 'center' });
          break;
        }
      }
    }, 120);
  };

  // Document Vault & Ingestion Drawer
  const [documents, setDocuments] = useState([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);

  // Corpus Health Scanner
  const [corpusHealth, setCorpusHealth] = useState(null);
  const [showHealthModal, setShowHealthModal] = useState(false);
  const [healthLoading, setHealthLoading] = useState(false);

  const handleScanHealth = async () => {
    setHealthLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/corpus_health`);
      if (res.ok) {
        const data = await res.json();
        setCorpusHealth(data);
        setShowHealthModal(true);
      } else {
        alert('Failed to scan corpus health.');
      }
    } catch (e) {
      alert(`Corpus scan failed: ${e.message}`);
    } finally {
      setHealthLoading(false);
    }
  };
  const [uploadForm, setUploadForm] = useState({
    doc_id: '',
    title: '',
    version: '1.0',
    effective_date: new Date().toISOString().split('T')[0],
    issuer: 'Executive Board',
    authority_level: 3,
    supersedes: '',
    signature_verified: true,
  });

  // System Health
  const [health, setHealth] = useState({ online: false, provider: 'gemini', total_documents: 0 });

  function fetchHealth() {
    fetch(`${API_BASE}/api/health`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setHealth(data);
      })
      .catch((e) => console.warn('Backend not yet reachable', e));
  }

  function fetchDocuments() {
    fetch(`${API_BASE}/api/documents`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setDocuments(data.documents || []);
      })
      .catch((e) => console.warn('Failed to fetch documents', e));
  }

  // Fetch health and documents on mount
  useEffect(() => {
    fetchHealth();
    fetchDocuments();
  }, []);

  const handleQuery = async (e) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setResult(null);
    setSelectedCitation(null);

    try {
      const res = await fetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          target_date: targetDate.trim() ? targetDate.trim() : null
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Query execution failed');
      }

      const data = await res.json();
      setResult(data);
      fetchDocuments();
    } catch (err) {
      alert(`Query error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) {
      alert('Please select a document file (.pdf, .txt, .md).');
      return;
    }

    setUploadLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('doc_id', uploadForm.doc_id || uploadFile.name.replace(/\.[^/.]+$/, ''));
      formData.append('title', uploadForm.title || uploadFile.name.replace(/\.[^/.]+$/, ''));
      formData.append('version', uploadForm.version);
      formData.append('effective_date', uploadForm.effective_date);
      formData.append('issuer', uploadForm.issuer);
      formData.append('authority_level', uploadForm.authority_level);
      formData.append('supersedes', uploadForm.supersedes);
      formData.append('signature_verified', uploadForm.signature_verified);

      const res = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Upload failed');
      }

      const data = await res.json();
      alert(`Document '${data.title}' successfully ingested into TruthGuard! (${data.chunks_created} chunks embedded)`);
      setShowUploadModal(false);
      setUploadFile(null);
      fetchDocuments();
    } catch (err) {
      alert(`Upload error: ${err.message}`);
    } finally {
      setUploadLoading(false);
    }
  };

  const handleSeedSamples = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/seed_samples`, { method: 'POST' });
      if (res.ok) {
        await fetchDocuments();
        alert('Sample corpus successfully seeded into ChromaDB! Try running standard questions.');
      }
    } catch (e) {
      alert(`Failed to seed samples: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleClearDocuments = async () => {
    if (!confirm('Are you sure you want to clear all documents from TruthGuard vector store?')) return;
    try {
      await fetch(`${API_BASE}/api/documents`, { method: 'DELETE' });
      setDocuments([]);
      setResult(null);
      alert('Vector store cleared.');
    } catch (e) {
      alert(`Clear failed: ${e.message}`);
    }
  };

  const samplePrompts = [
    { label: 'Standard Conflict (12 vs 15 days leave)', q: 'What is the annual paid leave entitlement in days?', date: '' },
    { label: 'Newer but Weaker (Board vs Slack)', q: 'What is the domestic per diem meal reimbursement allowance?', date: '' },
    { label: 'Ghost Reference (Unverified ID)', q: 'What is the remote work monthly equipment stipend?', date: '' },
    { label: 'Unverified Spoof (Unsigned bonus)', q: 'What is the engineer performance bonus percentage?', date: '' },
    { label: 'Time-Travel Query (2023-05-10)', q: 'What was the leave entitlement on 2023-05-10?', date: '' },
    { label: 'Time-Travel Picker (Year 2023)', q: 'What is the annual paid leave entitlement in days?', date: '2023-06-01' }
  ];

  const getStatusBadge = (status) => {
    if (status === 'VERIFIED') {
      return (
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 14px',
          borderRadius: '20px',
          background: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid #10B981',
          color: '#10B981',
          fontWeight: 700,
          fontSize: '12px'
        }}>
          ● VERIFIED (No Contradictions)
        </span>
      );
    }
    if (status === 'CONFLICT_RESOLVED') {
      return (
        <span style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 14px',
          borderRadius: '20px',
          background: 'rgba(56, 189, 248, 0.15)',
          border: '1px solid #38BDF8',
          color: '#38BDF8',
          fontWeight: 700,
          fontSize: '12px'
        }}>
          ● CONFLICT RESOLVED (Governing Precedence Enforced)
        </span>
      );
    }
    return (
      <span style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '6px 14px',
        borderRadius: '20px',
        background: 'rgba(245, 158, 11, 0.15)',
        border: '1px solid #F59E0B',
        color: '#F59E0B',
        fontWeight: 700,
        fontSize: '12px'
      }}>
        ▲ FLAGGED FOR REVIEW (Irreconcilable Conflict)
      </span>
    );
  };

  const getAuthorityBadge = (level) => {
    if (level === 3) {
      return <span style={{ background: 'rgba(99, 102, 241, 0.2)', color: '#A5B4FC', border: '1px solid #6366F1', padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 700 }}>L3 • Board / Executive</span>;
    }
    if (level === 2) {
      return <span style={{ background: 'rgba(56, 189, 248, 0.2)', color: '#7DD3FC', border: '1px solid #38BDF8', padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 700 }}>L2 • Dept Head</span>;
    }
    return <span style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#FCA5A5', border: '1px solid #EF4444', padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 700 }}>L1 • Informal / Unverified</span>;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: '#07111F', color: '#F8FAFC' }}>
      {/* Top Navbar */}
      <header style={{
        padding: '16px 32px',
        borderBottom: '1px solid rgba(148, 163, 184, 0.15)',
        background: 'rgba(10, 22, 40, 0.85)',
        backdropFilter: 'blur(16px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 50
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, #6366F1 0%, #38BDF8 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '22px',
            boxShadow: '0 4px 14px rgba(56, 189, 248, 0.3)'
          }}>
            🛡️
          </div>
          <div>
            <h1 style={{ fontSize: '20px', fontWeight: 800, margin: 0, letterSpacing: '-0.02em', background: 'linear-gradient(135deg, #38BDF8 0%, #A5B4FC 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              TruthGuard
            </h1>
            <p style={{ margin: 0, fontSize: '11px', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 700 }}>
              Adversarial Verification for Multi-Agent Document Q&A
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            fontSize: '11px',
            padding: '4px 10px',
            borderRadius: '16px',
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(148, 163, 184, 0.2)',
            color: '#94A3B8'
          }}>
            LLM: <strong style={{ color: '#38BDF8' }}>{health.provider.toUpperCase()}</strong> | Docs: <strong style={{ color: '#10B981' }}>{documents.length}</strong>
          </div>

          <button
            onClick={handleScanHealth}
            disabled={healthLoading}
            style={{
              background: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.35)',
              color: '#10B981',
              borderRadius: '8px',
              padding: '8px 14px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: healthLoading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            🩺 {healthLoading ? 'Scanning Corpus...' : 'Scan Corpus Health'}
          </button>

          <button
            onClick={handleSeedSamples}
            style={{
              background: 'rgba(56, 189, 248, 0.1)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              color: '#38BDF8',
              borderRadius: '8px',
              padding: '8px 14px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            ⚡ Load Sample Corpus
          </button>

          <button
            onClick={() => setShowUploadModal(true)}
            style={{
              background: 'linear-gradient(135deg, #6366F1 0%, #38BDF8 100%)',
              border: 'none',
              color: '#ffffff',
              borderRadius: '8px',
              padding: '8px 16px',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(99, 102, 241, 0.25)'
            }}
          >
            + Ingest Document
          </button>
        </div>
      </header>

      {/* Main Dual-Pane Container */}
      <div style={{ display: 'flex', flex: 1, padding: '24px 32px', gap: '28px', maxWidth: '1800px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
        
        {/* LEFT PANE: User Q&A & Verdict */}
        <section style={{ flex: '1 1 50%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Query Box Card */}
          <div style={{
            background: '#0F1E33',
            border: '1px solid rgba(148, 163, 184, 0.15)',
            borderRadius: '16px',
            padding: '24px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.3)'
          }}>
            <h2 style={{ fontSize: '15px', fontWeight: 700, color: '#F8FAFC', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>🔍 Ask Question Across Policies</span>
            </h2>

            <form onSubmit={handleQuery} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g., What is the annual paid leave entitlement in days?"
                  style={{
                    width: '100%',
                    background: 'rgba(7, 17, 31, 0.8)',
                    border: '1px solid rgba(148, 163, 184, 0.25)',
                    borderRadius: '10px',
                    padding: '12px 16px',
                    color: '#ffffff',
                    fontSize: '14px',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                />
              </div>

              {/* Time-Travel Date Picker & Run Button */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <label style={{ fontSize: '12px', color: '#94A3B8', fontWeight: 600 }}>
                    ⏳ Historical Target Date (Optional):
                  </label>
                  <input
                    type="date"
                    value={targetDate}
                    onChange={(e) => setTargetDate(e.target.value)}
                    style={{
                      background: 'rgba(7, 17, 31, 0.8)',
                      border: '1px solid rgba(148, 163, 184, 0.25)',
                      borderRadius: '8px',
                      padding: '6px 10px',
                      color: '#ffffff',
                      fontSize: '12px',
                      outline: 'none'
                    }}
                  />
                  {targetDate && (
                    <button
                      type="button"
                      onClick={() => setTargetDate('')}
                      style={{ background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', fontSize: '11px' }}
                    >
                      Clear
                    </button>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  style={{
                    background: 'linear-gradient(135deg, #38BDF8 0%, #6366F1 100%)',
                    border: 'none',
                    color: '#ffffff',
                    borderRadius: '8px',
                    padding: '10px 24px',
                    fontSize: '13px',
                    fontWeight: 700,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    boxShadow: '0 4px 15px rgba(56, 189, 248, 0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  {loading ? 'Adversarially Auditing...' : 'Run TruthGuard Audit ⚡'}
                </button>
              </div>
            </form>

            {/* Quick Prompts */}
            <div style={{ marginTop: '16px', borderTop: '1px solid rgba(148, 163, 184, 0.1)', paddingTop: '12px' }}>
              <span style={{ fontSize: '11px', color: '#94A3B8', fontWeight: 600, display: 'block', marginBottom: '8px' }}>
                Test Scenarios:
              </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {samplePrompts.map((sp, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setQuery(sp.q);
                      setTargetDate(sp.date);
                    }}
                    style={{
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid rgba(148, 163, 184, 0.15)',
                      borderRadius: '6px',
                      padding: '4px 10px',
                      fontSize: '11px',
                      color: '#CBD5E1',
                      cursor: 'pointer'
                    }}
                  >
                    {sp.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Answer / Result Card */}
          <div style={{
            background: '#0F1E33',
            border: '1px solid rgba(148, 163, 184, 0.15)',
            borderRadius: '16px',
            padding: '24px',
            flex: 1,
            boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
              <h2 style={{ fontSize: '16px', fontWeight: 800, color: '#F8FAFC', margin: 0 }}>
                TruthGuard Verified Ruling
              </h2>
              {result && getStatusBadge(result.status)}
            </div>

            {loading && (
              <div style={{ textAlign: 'center', padding: '60px 0', color: '#94A3B8' }}>
                <div style={{
                  display: 'inline-block',
                  width: '36px',
                  height: '36px',
                  border: '3px solid rgba(56, 189, 248, 0.2)',
                  borderTopColor: '#38BDF8',
                  borderRadius: '50%',
                  animation: 'spin 1s linear infinite'
                }} />
                <p style={{ marginTop: '16px', fontSize: '13px' }}>
                  Agents cross-verifying passages, checking staleness, and enforcing authority hierarchies...
                </p>
                <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
              </div>
            )}

            {!loading && !result && (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: '#94A3B8', border: '1px dashed rgba(148, 163, 184, 0.15)', borderRadius: '12px' }}>
                <span style={{ fontSize: '32px' }}>🛡️</span>
                <p style={{ fontSize: '14px', marginTop: '12px', fontWeight: 600 }}>
                  Enter a question or choose a scenario above to execute the adversarial audit.
                </p>
                <p style={{ fontSize: '12px', color: '#64748B' }}>
                  TruthGuard evaluates contradictions, supersession chains, and authority precedence.
                </p>
              </div>
            )}

            {!loading && result && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
                {/* Final Answer Text */}
                <div style={{
                  background: 'rgba(7, 17, 31, 0.5)',
                  border: '1px solid rgba(148, 163, 184, 0.12)',
                  borderRadius: '12px',
                  padding: '20px'
                }}>
                  <FormattedMarkdown
                    text={result.final_answer}
                    onCitationClick={(tag) => handleCitationFocus(tag)}
                    onCitationHover={(tag) => handleCitationFocus(tag)}
                  />
                </div>

                {/* Citations List */}
                {result.citations && result.citations.length > 0 && (
                  <div>
                    <h3 style={{ fontSize: '12px', textTransform: 'uppercase', color: '#94A3B8', letterSpacing: '0.05em', marginBottom: '8px' }}>
                      Cited Authoritative Passages (Click / Hover to Highlight):
                    </h3>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {result.citations.map((c, i) => (
                        <div
                          key={i}
                          onClick={() => {
                            setSelectedCitation(c);
                            handleCitationFocus(c.title);
                          }}
                          onMouseEnter={() => handleCitationFocus(c.title)}
                          style={{
                            padding: '6px 12px',
                            borderRadius: '8px',
                            background: (highlightedDoc && c.title.toLowerCase().includes(highlightedDoc.toLowerCase())) ? 'rgba(56, 189, 248, 0.35)' : 'rgba(56, 189, 248, 0.1)',
                            border: (highlightedDoc && c.title.toLowerCase().includes(highlightedDoc.toLowerCase())) ? '1px solid #38BDF8' : '1px solid rgba(56, 189, 248, 0.3)',
                            color: '#38BDF8',
                            fontSize: '12px',
                            fontWeight: 600,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            transition: 'all 0.2s ease',
                            boxShadow: (highlightedDoc && c.title.toLowerCase().includes(highlightedDoc.toLowerCase())) ? '0 0 12px rgba(56, 189, 248, 0.4)' : 'none'
                          }}
                        >
                          📄 {c.title} (v{c.version})
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>

        {/* RIGHT PANE: Adversarial Audit Trail */}
        <section style={{ flex: '1 1 50%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{
            background: '#0F1E33',
            border: '1px solid rgba(148, 163, 184, 0.15)',
            borderRadius: '16px',
            padding: '24px',
            flex: 1,
            boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
            display: 'flex',
            flexDirection: 'column'
          }}>
            {/* Right Pane Navigation Tabs */}
            <div style={{ display: 'flex', borderBottom: '1px solid rgba(148, 163, 184, 0.15)', marginBottom: '20px', gap: '8px' }}>
              <button
                onClick={() => setActiveRightTab('critic')}
                style={{
                  background: 'none',
                  border: 'none',
                  borderBottom: activeRightTab === 'critic' ? '2px solid #38BDF8' : '2px solid transparent',
                  color: activeRightTab === 'critic' ? '#38BDF8' : '#94A3B8',
                  padding: '10px 16px',
                  fontWeight: 700,
                  fontSize: '13px',
                  cursor: 'pointer'
                }}
              >
                ⚖️ Critic Breakdown
              </button>

              <button
                onClick={() => setActiveRightTab('provenance')}
                style={{
                  background: 'none',
                  border: 'none',
                  borderBottom: activeRightTab === 'provenance' ? '2px solid #38BDF8' : '2px solid transparent',
                  color: activeRightTab === 'provenance' ? '#38BDF8' : '#94A3B8',
                  padding: '10px 16px',
                  fontWeight: 700,
                  fontSize: '13px',
                  cursor: 'pointer'
                }}
              >
                📑 Provenance Comparison
              </button>

              <button
                onClick={() => setActiveRightTab('vault')}
                style={{
                  background: 'none',
                  border: 'none',
                  borderBottom: activeRightTab === 'vault' ? '2px solid #38BDF8' : '2px solid transparent',
                  color: activeRightTab === 'vault' ? '#38BDF8' : '#94A3B8',
                  padding: '10px 16px',
                  fontWeight: 700,
                  fontSize: '13px',
                  cursor: 'pointer'
                }}
              >
                🗄️ Document Vault ({documents.length})
              </button>
            </div>

            {/* TAB 1: Critic Breakdown */}
            {activeRightTab === 'critic' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
                {result?.critique ? (
                  <>
                    {/* Critic Metrics Cards */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                      <div style={{ background: 'rgba(7, 17, 31, 0.7)', border: '1px solid rgba(148, 163, 184, 0.12)', borderRadius: '10px', padding: '12px' }}>
                        <span style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase', fontWeight: 700 }}>Contradiction</span>
                        <div style={{ fontSize: '16px', fontWeight: 800, marginTop: '4px', color: result.critique.has_contradiction ? '#EF4444' : '#10B981' }}>
                          {result.critique.has_contradiction ? '⚠️ DETECTED' : '✓ NONE'}
                        </div>
                      </div>

                      <div style={{ background: 'rgba(7, 17, 31, 0.7)', border: '1px solid rgba(148, 163, 184, 0.12)', borderRadius: '10px', padding: '12px' }}>
                        <span style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase', fontWeight: 700 }}>Staleness</span>
                        <div style={{ fontSize: '16px', fontWeight: 800, marginTop: '4px', color: result.critique.has_staleness ? '#F59E0B' : '#10B981' }}>
                          {result.critique.has_staleness ? '⚠️ DETECTED' : '✓ NONE'}
                        </div>
                      </div>

                      <div style={{ background: 'rgba(7, 17, 31, 0.7)', border: '1px solid rgba(148, 163, 184, 0.12)', borderRadius: '10px', padding: '12px' }}>
                        <span style={{ fontSize: '10px', color: '#94A3B8', textTransform: 'uppercase', fontWeight: 700 }}>Revisions Made</span>
                        <div style={{ fontSize: '16px', fontWeight: 800, marginTop: '4px', color: '#38BDF8' }}>
                          {result.revision_count || 0} Passes
                        </div>
                      </div>
                    </div>

                    {/* Contradiction details */}
                    {result.critique.contradiction_details?.length > 0 && (
                      <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '10px', padding: '14px' }}>
                        <h4 style={{ color: '#FCA5A5', fontSize: '12px', textTransform: 'uppercase', margin: '0 0 8px 0' }}>
                          Factual Contradictions Identified:
                        </h4>
                        <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '13px', color: '#FEE2E2', lineHeight: '1.6' }}>
                          {result.critique.contradiction_details.map((item, idx) => (
                            <li key={idx}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Staleness details */}
                    {result.critique.staleness_details?.length > 0 && (
                      <div style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: '10px', padding: '14px' }}>
                        <h4 style={{ color: '#FCD34D', fontSize: '12px', textTransform: 'uppercase', margin: '0 0 8px 0' }}>
                          Staleness & Precedence Findings:
                        </h4>
                        <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '13px', color: '#FEF3C7', lineHeight: '1.6' }}>
                          {result.critique.staleness_details.map((item, idx) => (
                            <li key={idx}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Quarantined Chunks Guard */}
                    {result.provenance_details?.quarantined_chunks?.length > 0 && (
                      <div style={{ background: 'rgba(168, 85, 247, 0.08)', border: '1px solid rgba(168, 85, 247, 0.25)', borderRadius: '10px', padding: '14px' }}>
                        <h4 style={{ color: '#D8B4FE', fontSize: '12px', textTransform: 'uppercase', margin: '0 0 8px 0' }}>
                          🛡️ Quarantined / Spoofed Inputs (Quarantine Filter):
                        </h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {result.provenance_details.quarantined_chunks.map((q, idx) => (
                            <div key={idx} style={{ background: 'rgba(7, 17, 31, 0.6)', padding: '10px', borderRadius: '6px', fontSize: '12px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, color: '#E9D5FF' }}>
                                <span>{q.title} ({q.issuer})</span>
                                <span style={{ color: '#F87171' }}>Auth: {q.authority_level} | Verified: {String(q.signature_verified)}</span>
                              </div>
                              <p style={{ margin: '4px 0 0 0', color: '#94A3B8', fontSize: '11px' }}>
                                Reason: {q.reasons?.join(', ')}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div style={{ textAlign: 'center', padding: '40px', color: '#94A3B8', fontSize: '13px' }}>
                    Run a query to inspect the Adversarial Verifier audit trail.
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: Provenance Comparison */}
            {activeRightTab === 'provenance' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
                {/* Ripple Effect Tracker Section */}
                {result?.provenance_details?.ripple_effects?.length > 0 && (
                  <div style={{
                    background: 'rgba(245, 158, 11, 0.08)',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    borderRadius: '12px',
                    padding: '16px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                      <span style={{ fontSize: '18px' }}>⚠️</span>
                      <div>
                        <h4 style={{ margin: 0, fontSize: '13px', textTransform: 'uppercase', color: '#FCD34D', fontWeight: 800 }}>
                          Ripple Effect Tracker: Downstream Dependencies
                        </h4>
                        <p style={{ margin: 0, fontSize: '11px', color: '#94A3B8' }}>
                          Identifies dependent policies, calculations, and ERP systems requiring realignment
                        </p>
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {result.provenance_details.ripple_effects.map((eff, eIdx) => (
                        <div key={eIdx} style={{ background: 'rgba(7, 17, 31, 0.75)', borderRadius: '8px', padding: '10px 12px', border: '1px solid rgba(148, 163, 184, 0.15)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                            <span style={{ fontWeight: 700, fontSize: '12px', color: '#FFFFFF' }}>{eff.dependent_entity}</span>
                            <span style={{
                              fontSize: '10px',
                              fontWeight: 800,
                              padding: '2px 8px',
                              borderRadius: '4px',
                              background: eff.urgency === 'CRITICAL' ? 'rgba(239, 68, 68, 0.25)' : eff.urgency === 'HIGH' ? 'rgba(245, 158, 11, 0.25)' : 'rgba(56, 189, 248, 0.25)',
                              color: eff.urgency === 'CRITICAL' ? '#EF4444' : eff.urgency === 'HIGH' ? '#F59E0B' : '#38BDF8',
                              border: `1px solid ${eff.urgency === 'CRITICAL' ? '#EF4444' : eff.urgency === 'HIGH' ? '#F59E0B' : '#38BDF8'}`
                            }}>
                              {eff.urgency}
                            </span>
                          </div>
                          <div style={{ fontSize: '11px', color: '#94A3B8', marginBottom: '4px' }}>
                            Impact Type: <strong style={{ color: '#CBD5E1' }}>{eff.impact_type}</strong>
                          </div>
                          <div style={{ fontSize: '11.5px', color: '#E2E8F0', lineHeight: 1.5 }}>
                            {eff.impact_description}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Document Excerpt Cards with Interactive Citation Highlighting */}
                {result?.provenance_details?.side_by_side ? (
                  result.provenance_details.side_by_side.map((doc, idx) => {
                    const isMatch = highlightedDoc && (
                      doc.title.toLowerCase().includes(highlightedDoc.toLowerCase()) ||
                      highlightedDoc.toLowerCase().includes(doc.title.toLowerCase()) ||
                      doc.doc_id.toLowerCase().includes(highlightedDoc.toLowerCase())
                    );

                    return (
                      <div
                        key={idx}
                        data-doc-title={doc.title}
                        id={`doc-card-${doc.doc_id}`}
                        style={{
                          background: isMatch ? 'rgba(56, 189, 248, 0.14)' : 'rgba(7, 17, 31, 0.7)',
                          border: isMatch ? '2px solid #38BDF8' : '1px solid rgba(148, 163, 184, 0.15)',
                          borderRadius: '12px',
                          padding: '16px',
                          boxShadow: isMatch ? '0 0 25px rgba(56, 189, 248, 0.4)' : 'none',
                          transition: 'all 0.3s ease'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <h4 style={{ margin: 0, fontSize: '14px', color: isMatch ? '#38BDF8' : '#F1F5F9', fontWeight: 700 }}>
                              {doc.title} <span style={{ color: '#94A3B8', fontSize: '12px', fontWeight: 500 }}>v{doc.version}</span>
                            </h4>
                            {isMatch && (
                              <span style={{ fontSize: '10px', background: '#38BDF8', color: '#07111F', fontWeight: 800, padding: '2px 6px', borderRadius: '4px' }}>
                                🎯 ACTIVE CITATION TARGET
                              </span>
                            )}
                          </div>
                          {getAuthorityBadge(doc.authority_level)}
                        </div>
                        <div style={{ fontSize: '11px', color: '#94A3B8', marginBottom: '10px' }}>
                          Issuer: <strong style={{ color: '#E2E8F0' }}>{doc.issuer}</strong> | Effective: <strong style={{ color: '#E2E8F0' }}>{doc.effective_date}</strong>
                          {doc.supersedes?.length > 0 && <span> | Supersedes: <strong style={{ color: '#FCD34D' }}>{doc.supersedes.join(', ')}</strong></span>}
                        </div>
                        <div style={{
                          background: 'rgba(15, 30, 51, 0.8)',
                          padding: '12px',
                          borderRadius: '8px',
                          fontSize: '12.5px',
                          color: isMatch ? '#FFFFFF' : '#CBD5E1',
                          lineHeight: '1.6',
                          borderLeft: isMatch ? '3px solid #38BDF8' : '3px solid rgba(148, 163, 184, 0.3)'
                        }}>
                          "{doc.excerpt}"
                        </div>
                      </div>
                    );
                  })
                ) : result?.citations?.length > 0 ? (
                  result.citations.map((c, idx) => (
                    <div
                      key={idx}
                      data-doc-title={c.title}
                      style={{
                        background: 'rgba(7, 17, 31, 0.7)',
                        border: '1px solid rgba(148, 163, 184, 0.15)',
                        borderRadius: '10px',
                        padding: '14px'
                      }}
                    >
                      <h4 style={{ margin: 0, fontSize: '14px', color: '#38BDF8' }}>
                        {c.title} (v{c.version})
                      </h4>
                      <p style={{ fontSize: '12px', color: '#94A3B8', margin: '4px 0 0 0' }}>
                        Effective Date: {c.effective_date}
                      </p>
                    </div>
                  ))
                ) : (
                  <div style={{ textAlign: 'center', padding: '40px', color: '#94A3B8', fontSize: '13px' }}>
                    No provenance comparison data for current query.
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: Document Vault */}
            {activeRightTab === 'vault' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontSize: '12px', color: '#94A3B8' }}>{documents.length} Total Registered Policies</span>
                  <button
                    onClick={handleClearDocuments}
                    style={{ background: 'none', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#EF4444', borderRadius: '6px', padding: '4px 8px', fontSize: '11px', cursor: 'pointer' }}
                  >
                    Clear All
                  </button>
                </div>

                {documents.map((doc, idx) => (
                  <div key={idx} style={{
                    background: 'rgba(7, 17, 31, 0.7)',
                    border: '1px solid rgba(148, 163, 184, 0.15)',
                    borderRadius: '8px',
                    padding: '12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 700, fontSize: '13px', color: '#F1F5F9' }}>{doc.title}</span>
                      {getAuthorityBadge(doc.authority_level)}
                    </div>
                    <div style={{ fontSize: '11px', color: '#94A3B8' }}>
                      ID: <code>{doc.doc_id}</code> | v{doc.version} | Date: {doc.effective_date}
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748B' }}>
                      Issuer: {doc.issuer} | Signed: {doc.signature_verified ? 'Yes' : 'No'}
                      {doc.supersedes?.length > 0 && ` | Supersedes: [${doc.supersedes.join(', ')}]`}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Upload Drawer / Modal */}
      {showUploadModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: '20px'
        }}>
          <div style={{
            background: '#0F1E33',
            border: '1px solid rgba(148, 163, 184, 0.25)',
            borderRadius: '16px',
            width: '100%',
            maxWidth: '560px',
            padding: '28px',
            boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
            maxHeight: '90vh',
            overflowY: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 800, color: '#ffffff' }}>
                Ingest Policy / Document
              </h3>
              <button
                onClick={() => setShowUploadModal(false)}
                style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: '20px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', color: '#94A3B8', fontWeight: 600, display: 'block', marginBottom: '6px' }}>
                  Select Document File (.pdf, .txt, .md):
                </label>
                <input
                  type="file"
                  accept=".pdf,.txt,.md,.markdown"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                  style={{ width: '100%', fontSize: '12px', color: '#CBD5E1' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '12px', color: '#94A3B8', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                    Document ID:
                  </label>
                  <input
                    type="text"
                    value={uploadForm.doc_id}
                    onChange={(e) => setUploadForm({ ...uploadForm, doc_id: e.target.value })}
                    placeholder="e.g., leave_policy_2025"
                    style={{ width: '100%', background: '#07111F', border: '1px solid rgba(148,163,184,0.2)', padding: '8px', borderRadius: '6px', color: '#fff', fontSize: '12px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', color: '#94A3B8', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                    Document Title:
                  </label>
                  <input
                    type="text"
                    value={uploadForm.title}
                    onChange={(e) => setUploadForm({ ...uploadForm, title: e.target.value })}
                    placeholder="e.g., Board Resolution on Leave"
                    style={{ width: '100%', background: '#07111F', border: '1px solid rgba(148,163,184,0.2)', padding: '8px', borderRadius: '6px', color: '#fff', fontSize: '12px' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '12px', color: '#94A3B8', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                    Version:
                  </label>
                  <input
                    type="text"
                    value={uploadForm.version}
                    onChange={(e) => setUploadForm({ ...uploadForm, version: e.target.value })}
                    placeholder="1.0"
                    style={{ width: '100%', background: '#07111F', border: '1px solid rgba(148,163,184,0.2)', padding: '8px', borderRadius: '6px', color: '#fff', fontSize: '12px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', color: '#94A3B8', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                    Effective Date:
                  </label>
                  <input
                    type="date"
                    value={uploadForm.effective_date}
                    onChange={(e) => setUploadForm({ ...uploadForm, effective_date: e.target.value })}
                    style={{ width: '100%', background: '#07111F', border: '1px solid rgba(148,163,184,0.2)', padding: '8px', borderRadius: '6px', color: '#fff', fontSize: '12px' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '12px', color: '#94A3B8', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                    Issuer / Authority:
                  </label>
                  <input
                    type="text"
                    value={uploadForm.issuer}
                    onChange={(e) => setUploadForm({ ...uploadForm, issuer: e.target.value })}
                    placeholder="Executive Board"
                    style={{ width: '100%', background: '#07111F', border: '1px solid rgba(148,163,184,0.2)', padding: '8px', borderRadius: '6px', color: '#fff', fontSize: '12px' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', color: '#94A3B8', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                    Authority Level:
                  </label>
                  <select
                    value={uploadForm.authority_level}
                    onChange={(e) => setUploadForm({ ...uploadForm, authority_level: parseInt(e.target.value) })}
                    style={{ width: '100%', background: '#07111F', border: '1px solid rgba(148,163,184,0.2)', padding: '8px', borderRadius: '6px', color: '#fff', fontSize: '12px' }}
                  >
                    <option value={3}>Level 3 (Board / Executive)</option>
                    <option value={2}>Level 2 (Department Head / Director)</option>
                    <option value={1}>Level 1 (Informal / Unverified)</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '12px', color: '#94A3B8', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  Supersedes (comma-separated document IDs):
                </label>
                <input
                  type="text"
                  value={uploadForm.supersedes}
                  onChange={(e) => setUploadForm({ ...uploadForm, supersedes: e.target.value })}
                  placeholder="e.g., leave_policy_2022"
                  style={{ width: '100%', background: '#07111F', border: '1px solid rgba(148,163,184,0.2)', padding: '8px', borderRadius: '6px', color: '#fff', fontSize: '12px' }}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  id="sig_verified"
                  checked={uploadForm.signature_verified}
                  onChange={(e) => setUploadForm({ ...uploadForm, signature_verified: e.target.checked })}
                />
                <label htmlFor="sig_verified" style={{ fontSize: '12px', color: '#CBD5E1', cursor: 'pointer' }}>
                  Signature Verified (Untick to test quarantine spoof protection)
                </label>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  style={{ background: 'none', border: '1px solid rgba(148,163,184,0.3)', color: '#94A3B8', padding: '8px 16px', borderRadius: '8px', cursor: 'pointer', fontSize: '12px' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploadLoading}
                  style={{
                    background: 'linear-gradient(135deg, #6366F1 0%, #38BDF8 100%)',
                    border: 'none',
                    color: '#fff',
                    padding: '8px 20px',
                    borderRadius: '8px',
                    fontWeight: 700,
                    cursor: uploadLoading ? 'not-allowed' : 'pointer',
                    fontSize: '12px'
                  }}
                >
                  {uploadLoading ? 'Ingesting...' : 'Ingest Document'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Corpus Health Scanner Modal */}
      {showHealthModal && corpusHealth && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.78)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: '20px'
        }}>
          <div style={{
            background: '#0F1E33',
            border: '1px solid rgba(16, 185, 129, 0.35)',
            borderRadius: '16px',
            width: '100%',
            maxWidth: '640px',
            padding: '28px',
            boxShadow: '0 20px 50px rgba(0,0,0,0.6)',
            maxHeight: '85vh',
            overflowY: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid rgba(148, 163, 184, 0.15)', paddingBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '24px' }}>🩺</span>
                <div>
                  <h3 style={{ margin: 0, fontSize: '17px', fontWeight: 800, color: '#F8FAFC' }}>
                    Corpus Health Audit Report
                  </h3>
                  <p style={{ margin: 0, fontSize: '11px', color: '#94A3B8' }}>
                    Proactive conflict detection across all {corpusHealth.total_documents} documents ({corpusHealth.total_chunks} chunks)
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowHealthModal(false)}
                style={{ background: 'none', border: 'none', color: '#94A3B8', fontSize: '20px', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            {/* Health Score Overview */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px', marginBottom: '18px' }}>
              <div style={{ background: 'rgba(7, 17, 31, 0.7)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(148, 163, 184, 0.15)', textAlign: 'center' }}>
                <span style={{ fontSize: '10px', textTransform: 'uppercase', color: '#94A3B8', fontWeight: 700 }}>Health Score</span>
                <div style={{ fontSize: '18px', fontWeight: 800, color: corpusHealth.health_score > 80 ? '#10B981' : '#F59E0B', marginTop: '4px' }}>
                  {corpusHealth.health_score}%
                </div>
              </div>
              <div style={{ background: 'rgba(7, 17, 31, 0.7)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(148, 163, 184, 0.15)', textAlign: 'center' }}>
                <span style={{ fontSize: '10px', textTransform: 'uppercase', color: '#94A3B8', fontWeight: 700 }}>Conflicts</span>
                <div style={{ fontSize: '18px', fontWeight: 800, color: corpusHealth.conflicts_count > 0 ? '#EF4444' : '#10B981', marginTop: '4px' }}>
                  {corpusHealth.conflicts_count}
                </div>
              </div>
              <div style={{ background: 'rgba(7, 17, 31, 0.7)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(148, 163, 184, 0.15)', textAlign: 'center' }}>
                <span style={{ fontSize: '10px', textTransform: 'uppercase', color: '#94A3B8', fontWeight: 700 }}>Stale Policies</span>
                <div style={{ fontSize: '18px', fontWeight: 800, color: corpusHealth.staleness_count > 0 ? '#F59E0B' : '#10B981', marginTop: '4px' }}>
                  {corpusHealth.staleness_count}
                </div>
              </div>
              <div style={{ background: 'rgba(7, 17, 31, 0.7)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(148, 163, 184, 0.15)', textAlign: 'center' }}>
                <span style={{ fontSize: '10px', textTransform: 'uppercase', color: '#94A3B8', fontWeight: 700 }}>Ghost Refs</span>
                <div style={{ fontSize: '18px', fontWeight: 800, color: corpusHealth.ghost_references_count > 0 ? '#EF4444' : '#10B981', marginTop: '4px' }}>
                  {corpusHealth.ghost_references_count}
                </div>
              </div>
            </div>

            {/* Findings Lists */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {corpusHealth.contradictions?.length > 0 && (
                <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', padding: '12px' }}>
                  <h4 style={{ margin: '0 0 6px 0', fontSize: '12px', color: '#FCA5A5', textTransform: 'uppercase' }}>
                    🚨 Latent Factual Contradictions Detected in Document Corpus:
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#FEE2E2', lineHeight: 1.5 }}>
                    {corpusHealth.contradictions.map((c, i) => <li key={i}>{c}</li>)}
                  </ul>
                </div>
              )}

              {corpusHealth.ghost_references?.length > 0 && (
                <div style={{ background: 'rgba(168, 85, 247, 0.08)', border: '1px solid rgba(168, 85, 247, 0.3)', borderRadius: '8px', padding: '12px' }}>
                  <h4 style={{ margin: '0 0 6px 0', fontSize: '12px', color: '#D8B4FE', textTransform: 'uppercase' }}>
                    👻 Unverified Ghost References in Supersedes Metadata:
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#F3E8FF', lineHeight: 1.5 }}>
                    {corpusHealth.ghost_references.map((g, i) => <li key={i}>{g}</li>)}
                  </ul>
                </div>
              )}

              {corpusHealth.staleness?.length > 0 && (
                <div style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '8px', padding: '12px' }}>
                  <h4 style={{ margin: '0 0 6px 0', fontSize: '12px', color: '#FCD34D', textTransform: 'uppercase' }}>
                    ⏳ Superseded / Stale Policies in Corpus:
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#FEF3C7', lineHeight: 1.5 }}>
                    {corpusHealth.staleness.map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </div>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button
                onClick={() => setShowHealthModal(false)}
                style={{ background: 'rgba(255, 255, 255, 0.1)', border: '1px solid rgba(148, 163, 184, 0.3)', color: '#fff', padding: '8px 18px', borderRadius: '8px', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}
              >
                Close Audit
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
