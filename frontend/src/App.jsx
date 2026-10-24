import { useState, useEffect, useRef } from "react";
import { queryPipeline, ingestFile, getCollections, checkHealth } from "./api";
import "./index.css";

// ── Verdict chip colours ──────────────────────────────────────────────────────
const VERDICT_MAP = {
  SUPPORTED:     { label: "Supported",     cls: "SUPPORTED" },
  NOT_SUPPORTED: { label: "Not Supported", cls: "NOT_SUPPORTED" },
  PARTIAL:       { label: "Partial",       cls: "PARTIAL" },
  UNCITED:       { label: "Uncited",       cls: "UNCITED" },
  UNKNOWN:       { label: "Unknown",       cls: "UNKNOWN" },
};

// ── Top Nav ───────────────────────────────────────────────────────────────────
function TopNav({ health }) {
  const statusMap = {
    online:   { label: "API Online",   cls: "online" },
    offline:  { label: "API Offline",  cls: "offline" },
    checking: { label: "Checking…",    cls: "checking" },
  };
  const s = statusMap[health] || statusMap.checking;
  return (
    <header className="topnav">
      <div className="topnav-logo">
        <div className="logo-icon">🧠</div>
        RAG Pipeline
      </div>
      <div className="topnav-spacer" />
      <div className={`health-badge ${s.cls}`}>
        <div className="health-dot" />
        {s.label}
      </div>
    </header>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
function Sidebar({ page, setPage }) {
  const items = [
    { id: "query",       icon: "💬", label: "Query" },
    { id: "ingest",      icon: "📤", label: "Ingest Documents" },
    { id: "collections", icon: "🗂️", label: "Collections" },
    { id: "guide",       icon: "📖", label: "Pipeline Guide" },
  ];
  return (
    <nav className="sidebar">
      <div className="sidebar-section">
        <div className="sidebar-label">Navigation</div>
        {items.map(i => (
          <button
            key={i.id}
            className={`sidebar-btn ${page === i.id ? "active" : ""}`}
            onClick={() => setPage(i.id)}
          >
            <span className="btn-icon">{i.icon}</span>
            {i.label}
          </button>
        ))}
      </div>
    </nav>
  );
}

// ── Claim Card ────────────────────────────────────────────────────────────────
function ClaimCard({ claim }) {
  const v = VERDICT_MAP[claim.verdict] || { label: claim.verdict, cls: "UNKNOWN" };
  return (
    <div className="claim-card">
      <div className="claim-top">
        <span className={`verdict-chip ${v.cls}`}>{v.label}</span>
        <span className="claim-text">{claim.claim}</span>
      </div>
      {claim.reason && <div className="claim-reason">{claim.reason}</div>}
      {claim.citations?.length > 0 && (
        <div className="claim-citations">
          {claim.citations.map(c => (
            <span key={c} className="citation-tag">{c}</span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Verdict Donut Chart ───────────────────────────────────────────────────────
const VERDICT_COLORS = {
  SUPPORTED:     "#22c55e",
  PARTIAL:       "#f59e0b",
  NOT_SUPPORTED: "#ef4444",
  UNCITED:       "#8b5cf6",
  UNKNOWN:       "#6b7280",
};

function VerdictChart({ count }) {
  const entries = Object.entries(count).filter(([, v]) => v > 0);
  const total   = entries.reduce((s, [, v]) => s + v, 0);
  if (total === 0) return null;

  // Build conic-gradient segments
  let cursor = 0;
  const segments = entries.map(([verdict, val]) => {
    const pct   = (val / total) * 100;
    const color = VERDICT_COLORS[verdict] || "#6b7280";
    const seg   = `${color} ${cursor.toFixed(1)}% ${(cursor + pct).toFixed(1)}%`;
    cursor += pct;
    return seg;
  });
  const gradient = `conic-gradient(${segments.join(", ")})`;

  return (
    <div className="verdict-chart">
      <div className="verdict-chart-title">Verdict Breakdown</div>
      <div className="verdict-chart-body">
        {/* Donut */}
        <div className="donut-wrap">
          <div className="donut" style={{ background: gradient }} />
          <div className="donut-hole">
            <span className="donut-total">{total}</span>
            <span className="donut-label">claims</span>
          </div>
        </div>
        {/* Legend */}
        <div className="donut-legend">
          {entries.map(([verdict, val]) => (
            <div key={verdict} className="legend-row">
              <span className="legend-dot" style={{ background: VERDICT_COLORS[verdict] || "#6b7280" }} />
              <span className="legend-verdict">{verdict.replace("_", " ")}</span>
              <span className="legend-count">{val}</span>
              <span className="legend-pct">({((val / total) * 100).toFixed(0)}%)</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Bot Answer Card ───────────────────────────────────────────────────────────
function BotAnswer({ result }) {
  const isPass = result.overall === "PASS";
  return (
    <div className="message-bot">
      <div className="bot-answer-card">
        <div className={`overall-badge ${isPass ? "pass" : "review"}`}>
          {isPass ? "✓ Pass" : "⚠ Review"} · {Object.entries(result.count).map(([k,v]) => `${v} ${k.toLowerCase()}`).join(", ")}
        </div>
        <div className="answer-text">{result.answer}</div>
      </div>
      {result.claims?.length > 0 && (
        <>
          <VerdictChart count={result.count} />
          <div className="claims-section">
            <div className="claims-title">Claim Verification ({result.claims.length})</div>
            {result.claims.map((c, i) => <ClaimCard key={i} claim={c} />)}
          </div>
        </>
      )}
    </div>
  );
}

// ── Query Page ────────────────────────────────────────────────────────────────
function QueryPage({ setPage }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); executeSend(input); }
  };

  const executeSend = async (textToSend) => {
    const q = (textToSend ?? input).trim();
    if (!q || loading) return;
    setInput("");
    setMessages(prev => [...prev, { type: "user", text: q }]);
    setLoading(true);
    try {
      const result = await queryPipeline(q);
      setMessages(prev => [...prev, { type: "bot", result }]);
    } catch (err) {
      setMessages(prev => [...prev, { type: "error", text: err.message }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSampleClick = (q) => {
    setInput(q);
    executeSend(q);
  };

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Query</h1>
        <p className="page-subtitle">Ask a question — get a grounded, citation-verified answer.</p>
      </div>
      <div className="query-page">
        <div className="messages-list">
          {messages.length === 0 && (
            <div className="empty-state">
              <div className="empty-hero">
                <div className="empty-icon-glow">🧠</div>
                <h3 className="empty-title">Production-Grade Grounded RAG</h3>
                <p className="empty-subtitle">
                  Every answer is retrieved with hybrid search, constrained strictly to source documents, and verified claim-by-claim by an LLM-as-a-judge.
                </p>
              </div>

              {/* Quick Info Strip */}
              <div className="guide-summary-card">
                <div className="guide-summary-header">
                  <span>⚡ Quick Verdict Guide</span>
                  {setPage && (
                    <button className="link-btn" onClick={() => setPage("guide")}>
                      Open Full Guide →
                    </button>
                  )}
                </div>
                <div className="guide-chips-row">
                  <div className="guide-mini-chip">
                    <span className="verdict-chip SUPPORTED">Supported</span>
                    <span>100% verified fact</span>
                  </div>
                  <div className="guide-mini-chip">
                    <span className="verdict-chip PARTIAL">Partial</span>
                    <span>Assumption or missing sub-clause</span>
                  </div>
                  <div className="guide-mini-chip">
                    <span className="verdict-chip NOT_SUPPORTED">Not Supported</span>
                    <span>Contradicts source text</span>
                  </div>
                </div>
              </div>

              {/* Sample Queries */}
              <div className="sample-queries-box">
                <div className="sample-queries-label">Click a sample query to test:</div>
                <div className="sample-chips-wrap">
                  <button
                    className="sample-chip"
                    onClick={() => handleSampleClick("What is the maximum loan tenure?")}
                  >
                    🕒 Maximum loan tenure?
                  </button>
                  <button
                    className="sample-chip"
                    onClick={() => handleSampleClick("What are the KYC documentation requirements for salaried applicants?")}
                  >
                    📄 KYC requirements for salaried
                  </button>
                  <button
                    className="sample-chip"
                    onClick={() => handleSampleClick("Summarize the prepayment and foreclosure charges in bullet points")}
                  >
                    💳 Prepayment &amp; foreclosure charges
                  </button>
                </div>
              </div>
            </div>
          )}
          {messages.map((m, i) => {
            if (m.type === "user")  return <div key={i} className="message-user">{m.text}</div>;
            if (m.type === "bot")   return <BotAnswer key={i} result={m.result} />;
            if (m.type === "error") return <div key={i} className="error-msg">⚠ {m.text}</div>;
            return null;
          })}
          {loading && (
            <div className="message-bot">
              <div className="bot-answer-card" style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div className="spinner" />
                <span style={{ color: "var(--text-secondary)", fontSize: 13 }}>Running pipeline…</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <div className="query-input-area">
          <textarea
            className="query-textarea"
            rows={2}
            placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button className="send-btn" onClick={() => executeSend(input)} disabled={loading || !input.trim()}>
            {loading ? <div className="spinner" /> : "Send ↑"}
          </button>
        </div>
      </div>
    </>
  );
}

// ── Ingest Page ───────────────────────────────────────────────────────────────
function IngestPage({ results, setResults }) {
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const processFiles = async (files) => {
    const list = Array.from(files);
    if (!list.length) return;
    setLoading(true);
    for (const file of list) {
      try {
        const res = await ingestFile(file);
        setResults(prev => [...prev, { ok: true, filename: res.filename, detail: `${res.chunks_indexed} chunks indexed` }]);
      } catch (err) {
        setResults(prev => [...prev, { ok: false, filename: file.name, detail: err.message }]);
      }
    }
    setLoading(false);
  };

  const onDrop = (e) => {
    e.preventDefault(); setDragOver(false);
    processFiles(e.dataTransfer.files);
  };

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Ingest Documents</h1>
        <p className="page-subtitle">Upload files to be chunked, embedded, and indexed into Qdrant.</p>
      </div>
      <div className="ingest-page">
        <div
          className={`dropzone ${dragOver ? "drag-over" : ""}`}
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
        >
          <div className="dropzone-icon">{loading ? "⏳" : "📂"}</div>
          <h3>{loading ? "Uploading…" : "Drop files here"}</h3>
          <p>or click to browse · PDF, TXT, MD supported</p>
          <input
            type="file"
            multiple
            accept=".pdf,.txt,.md"
            onChange={e => processFiles(e.target.files)}
            disabled={loading}
          />
        </div>

        {results.length > 0 && (
          <div className="ingest-results">
            <div className="claims-title">Upload Results</div>
            {results.map((r, i) => (
              <div key={i} className={`ingest-result-card ${r.ok ? "success" : "error"}`}>
                <span className="result-icon">{r.ok ? "✅" : "❌"}</span>
                <div className="result-info">
                  <div className="result-filename">{r.filename}</div>
                  <div className="result-detail">{r.detail}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

// ── Collections Page ──────────────────────────────────────────────────────────
function CollectionsPage() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const res = await getCollections();
      setData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Collections</h1>
        <p className="page-subtitle">Overview of all indexed documents and chunks stored in Qdrant.</p>
      </div>
      <div className="collections-page">
        <button className="refresh-btn" onClick={load} disabled={loading}>
          {loading ? <><div className="spinner" style={{ borderTopColor: "var(--accent)" }} /> Refreshing…</> : "⟳ Refresh"}
        </button>

        {error && <div className="error-msg">⚠ {error}</div>}

        {data && (
          <>
            <div className="stats-row">
              <div className="stat-card">
                <div className="stat-value">{data.chunk_count.toLocaleString()}</div>
                <div className="stat-label">Total Chunks</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{data.sources.length}</div>
                <div className="stat-label">Source Files</div>
              </div>
            </div>

            <div>
              <div className="claims-title" style={{ marginBottom: 10 }}>Indexed Sources</div>
              {data.sources.length === 0 ? (
                <div className="empty-state" style={{ padding: "40px 0" }}>
                  <div className="empty-icon">📭</div>
                  <h3>No documents indexed yet</h3>
                  <p>Upload files in the Ingest tab to get started.</p>
                </div>
              ) : (
                <div className="sources-list">
                  {data.sources.map((src, i) => (
                    <div key={i} className="source-card">
                      <span className="source-icon">📄</span>
                      <span className="source-name">{src}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </>
  );
}

// ── Guide Page ────────────────────────────────────────────────────────────────
function GuidePage({ setPage }) {
  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Pipeline Guide</h1>
        <p className="page-subtitle">How this production RAG pipeline works, what it outputs, and what you should care about.</p>
      </div>
      <div className="guide-page-content">
        {/* Section 1: 4-Stage Architecture */}
        <div className="guide-card">
          <div className="guide-card-header">
            <span className="guide-badge">Architecture</span>
            <h2>How the Pipeline Works</h2>
          </div>
          <p className="guide-text">
            Standard RAG systems send text to an LLM and hope it does not hallucinate. This pipeline implements a <strong>closed-loop, audited RAG architecture</strong> across 4 decoupled stages:
          </p>
          <div className="guide-steps-grid">
            <div className="guide-step-card">
              <div className="step-badge">Stage 1</div>
              <h3>Multi-Format Ingestion</h3>
              <p>Parses PDF, Markdown, and HTML with layout and header awareness. Uses token-based sliding-window chunking with overlap to preserve cross-boundary context.</p>
            </div>
            <div className="guide-step-card">
              <div className="step-badge">Stage 2</div>
              <h3>Hybrid Search &amp; Fusion</h3>
              <p>Encodes dense semantic embeddings (<code>bge-small-en-v1.5</code>) and BM25 sparse vectors. Fuses rank lists inside Qdrant using Reciprocal Rank Fusion (RRF).</p>
            </div>
            <div className="guide-step-card">
              <div className="step-badge">Stage 3</div>
              <h3>Grounded Generation</h3>
              <p>Groq LLaMA 3.3 70B synthesizes the retrieved chunks into a direct response, strictly forced to cite bracketed indices like <code>[1]</code>, <code>[2]</code>.</p>
            </div>
            <div className="guide-step-card">
              <div className="step-badge">Stage 4</div>
              <h3>LLM-as-a-Judge Audit</h3>
              <p>A separate auditor LLM extracts every individual sentence as an atomic claim, cross-references it against cited chunks, and scores attribution.</p>
            </div>
          </div>
        </div>

        {/* Section 2: What You Receive */}
        <div className="guide-card">
          <div className="guide-card-header">
            <span className="guide-badge">Outputs</span>
            <h2>What You Receive From Every Query</h2>
          </div>
          <div className="guide-outputs-grid">
            <div className="guide-output-item">
              <div className="output-icon">📝</div>
              <div>
                <h4>1. Grounded Answer with Citations</h4>
                <p>A concise, readable response with inline tags like <code>[2][3]</code> linking directly to the retrieved passages.</p>
              </div>
            </div>
            <div className="guide-output-item">
              <div className="output-icon">⚖️</div>
              <div>
                <h4>2. Executive Audit Verdict (PASS / REVIEW)</h4>
                <p>A top-level health badge. <strong>PASS</strong> means 100% of claims are fully grounded. <strong>REVIEW</strong> signals at least one sentence needs human validation.</p>
              </div>
            </div>
            <div className="guide-output-item">
              <div className="output-icon">📊</div>
              <div>
                <h4>3. Verdict Breakdown Donut Chart</h4>
                <p>An instant visual summary of factual reliability: percentage of claims Supported vs Partial vs Uncited.</p>
              </div>
            </div>
            <div className="guide-output-item">
              <div className="output-icon">🔍</div>
              <div>
                <h4>4. Claim-by-Claim Audit Cards</h4>
                <p>Every claim is individually listed with its verification status, the source chunk IDs, and the exact reasoning from the judge.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: What You Have to Care About */}
        <div className="guide-card">
          <div className="guide-card-header">
            <span className="guide-badge">Verification</span>
            <h2>What You Have to Care About (Reading Verdicts)</h2>
          </div>
          <p className="guide-text">
            When reviewing an answer, check the claim chips below the text:
          </p>
          <div className="verdict-explain-table">
            <div className="verdict-explain-row">
              <div className="verdict-chip SUPPORTED">Supported</div>
              <div className="verdict-explain-desc">
                <strong>100% Backed by Document:</strong> The fact is explicitly confirmed by the cited chunk. Safe to use in automated workflows and decisions.
              </div>
            </div>
            <div className="verdict-explain-row">
              <div className="verdict-chip PARTIAL">Partial</div>
              <div className="verdict-explain-desc">
                <strong>Subtle Extrapolation or Missing Sub-Clause:</strong> The core premise may be accurate, but the LLM added an assumption or merged multiple facts where only some were in the cited chunk.
              </div>
            </div>
            <div className="verdict-explain-row">
              <div className="verdict-chip NOT_SUPPORTED">Not Supported</div>
              <div className="verdict-explain-desc">
                <strong>Contradiction / Hallucination:</strong> The assertion conflicts with the source material or cannot be found anywhere in the corpus.
              </div>
            </div>
            <div className="verdict-explain-row">
              <div className="verdict-chip UNKNOWN">Unknown / Uncited</div>
              <div className="verdict-explain-desc">
                <strong>Citation Mismatch:</strong> The claim lacks a source citation, or cited a chunk that discusses an unrelated section of the document.
              </div>
            </div>
          </div>
        </div>

        {/* Section 4: Tips for Optimal Grounding */}
        <div className="guide-card guide-accent-card">
          <div className="guide-card-header">
            <span className="guide-badge">Pro Tips</span>
            <h2>How to Get 100% PASS Rates</h2>
          </div>
          <div className="guide-tips-grid">
            <div className="tip-box">
              <h4>🎯 Ask Focused Questions</h4>
              <p>Targeted queries (e.g. <em>&quot;What is the maximum loan tenure?&quot;</em>) map directly to single chunks, guaranteeing tight 1-to-1 attribution.</p>
            </div>
            <div className="tip-box">
              <h4>📋 Request Bullet Points</h4>
              <p>For broad topics, ask for <em>&quot;bullet points with citations&quot;</em>. This prevents run-on paragraphs and avoids compound-claim dilution.</p>
            </div>
            <div className="tip-box">
              <h4>🔍 Check Citation Tags</h4>
              <p>If a claim is flagged as Partial, look at its citation numbers <code>[N]</code> to see which clause the generator relied on.</p>
            </div>
          </div>
          <div style={{ marginTop: 20 }}>
            <button className="send-btn" onClick={() => setPage("query")}>
              Go to Query Page →
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

// ── App Root ──────────────────────────────────────────────────────────────────
export default function App() {
  const [page, setPage]         = useState("query");
  const [health, setHealth]     = useState("checking");
  const [ingestResults, setIngestResults] = useState([]);

  useEffect(() => {
    const ping = async () => {
      try {
        await checkHealth();
        setHealth("online");
      } catch {
        setHealth("offline");
      }
    };
    ping();
    const id = setInterval(ping, 15000);
    return () => clearInterval(id);
  }, []);

  const pageMap = {
    query:       <QueryPage setPage={setPage} />,
    ingest:      <IngestPage results={ingestResults} setResults={setIngestResults} />,
    collections: <CollectionsPage />,
    guide:       <GuidePage setPage={setPage} />,
  };

  return (
    <div className="app-layout">
      <TopNav health={health} />
      <Sidebar page={page} setPage={setPage} />
      <main className="main-content">{pageMap[page]}</main>
    </div>
  );
}
