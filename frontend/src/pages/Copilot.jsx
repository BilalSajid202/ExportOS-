import { useState, useEffect, useRef } from 'react';
import api from '../lib/api';

const PILLAR_ICONS = {
  INVENTORY: '📦',
  COSTING: '💰',
  DOCUMENTS: '📄',
  CONSISTENCY: '🔒',
  COMPLIANCE: '⚖️',
  LOGISTICS: '🚢',
  PAYMENT: '💵',
};

const PILLAR_STATUS_THEMES = {
  PASSED: {
    badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    icon: '✓',
    text: 'text-emerald-400',
  },
  WARNING: {
    badge: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    icon: '⚠',
    text: 'text-amber-400',
  },
  BLOCKED: {
    badge: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    icon: '✕',
    text: 'text-rose-400',
  },
  NOT_APPLICABLE: {
    badge: 'bg-slate-800 text-slate-400 border-slate-700',
    icon: '—',
    text: 'text-slate-400',
  },
};

export default function Copilot() {
  // Deal Selection State
  const [deals, setDeals] = useState([]);
  const [selectedDealId, setSelectedDealId] = useState('');
  const [selectedDeal, setSelectedDeal] = useState(null);

  // Chat & Query State
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      text: "👋 Welcome to **ExportOS Copilot**! I'm your grounded AI export specialist powered by **Qdrant Vector DB**, the **SBP Foreign Exchange Manual**, and **7-Pillar Export Readiness** validation.\n\nSelect a deal above or ask any question regarding Pakistan export compliance, Incoterms 2020, customs clearance, or order readiness.",
      citations: ['SBP Foreign Exchange Manual Chapter XII', 'ICC Incoterms 2020 Rules'],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isAsking, setIsAsking] = useState(false);
  const chatBottomRef = useRef(null);

  // Readiness State
  const [readiness, setReadiness] = useState(null);
  const [isLoadingReadiness, setIsLoadingReadiness] = useState(false);
  const [readinessError, setReadinessError] = useState('');

  // Right Side Panel Tab State: 'readiness' | 'drafter' | 'knowledge'
  const [activeSideTab, setActiveSideTab] = useState('readiness');

  // Commercial Drafter State
  const [draftTemplate, setDraftTemplate] = useState('ORDER_CONFIRMATION');
  const [draftNotes, setDraftNotes] = useState('');
  const [draftResult, setDraftResult] = useState(null);
  const [isDrafting, setIsDrafting] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);

  // Vector DB Sync State
  const [isSyncingDocs, setIsSyncingDocs] = useState(false);
  const [syncStatusMsg, setSyncStatusMsg] = useState('');

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Load deals on mount
  useEffect(() => {
    fetchDeals();
  }, []);

  // When deal changes, reload deal object & readiness inspection
  useEffect(() => {
    if (selectedDealId) {
      const deal = deals.find((d) => d.id === selectedDealId);
      setSelectedDeal(deal || null);
      fetchReadiness(selectedDealId);
    } else {
      setSelectedDeal(null);
      setReadiness(null);
    }
  }, [selectedDealId, deals]);

  const fetchDeals = async () => {
    try {
      const data = await api.get('/deals');
      setDeals(data || []);
      if (data && data.length > 0) {
        setSelectedDealId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load deals:', err);
    }
  };

  const fetchReadiness = async (dealId) => {
    if (!dealId) return;
    setIsLoadingReadiness(true);
    setReadinessError('');
    try {
      const data = await api.get(`/copilot/deals/${dealId}/readiness`);
      setReadiness(data);
    } catch (err) {
      setReadinessError(err.message || 'Failed to calculate deal readiness');
      setReadiness(null);
    } finally {
      setIsLoadingReadiness(false);
    }
  };

  const handleSendMessage = async (queryText = null) => {
    const query = (queryText || inputQuery).trim();
    if (!query || isAsking) return;

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputQuery('');
    setIsAsking(true);

    try {
      const payload = {
        query,
        deal_id: selectedDealId || null,
        top_k: 5,
      };

      const response = await api.post('/copilot/query', payload);

      const botMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        text: response.answer,
        citations: response.citations || [],
        retrieved_chunks: response.retrieved_chunks || [],
        readiness: response.readiness || null,
        suggested_followups: response.suggested_followups || [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, botMessage]);

      if (response.readiness) {
        setReadiness(response.readiness);
      }
    } catch (err) {
      const errorMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        text: `⚠️ **Error querying Copilot**: ${err.message || 'Network or service error'}`,
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsAsking(false);
    }
  };

  const handleGenerateDraft = async () => {
    if (!selectedDealId) {
      alert('Please select a deal first to generate commercial correspondence.');
      return;
    }
    setIsDrafting(true);
    setDraftResult(null);
    setCopySuccess(false);

    try {
      const response = await api.post(`/copilot/deals/${selectedDealId}/draft-message`, {
        template_type: draftTemplate,
        custom_notes: draftNotes.trim() || null,
      });
      setDraftResult(response);
    } catch (err) {
      alert(`Draft generation failed: ${err.message || 'Unknown error'}`);
    } finally {
      setIsDrafting(false);
    }
  };

  const handleCopyDraft = () => {
    if (!draftResult) return;
    const fullText = `Subject: ${draftResult.subject}\n\n${draftResult.body}`;
    navigator.clipboard.writeText(fullText);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2500);
  };

  const handleSyncDocs = async () => {
    setIsSyncingDocs(true);
    setSyncStatusMsg('');
    try {
      const response = await api.post('/copilot/sync-docs', {});
      setSyncStatusMsg(`✓ Synced ${response.indexed_chunks || 0} chunks to Qdrant successfully!`);
      setTimeout(() => setSyncStatusMsg(''), 4000);
    } catch (err) {
      setSyncStatusMsg(`✕ Sync failed: ${err.message || 'Error'}`);
    } finally {
      setIsSyncingDocs(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 overflow-hidden">
      {/* ── Top Bar / Deal Context Selector ─────────────────────── */}
      <header className="flex flex-wrap items-center justify-between gap-4 px-6 py-3.5 bg-slate-900/80 border-b border-slate-800/80 backdrop-blur z-10 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-emerald-400 p-[1px] shadow-sm shadow-indigo-500/20">
            <div className="w-full h-full bg-slate-950 rounded-[11px] flex items-center justify-center text-base font-bold">
              🤖
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-white tracking-tight">
                Export Copilot & Readiness Radar
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Qdrant Vector RAG Active
              </span>
            </div>
            <p className="text-xs text-slate-400">
              SBP Chapter XII Foreign Exchange Manual · Incoterms 2020 · 7-Pillar Verification
            </p>
          </div>
        </div>

        {/* Deal Selector & Knowledge Sync */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-950/80 border border-slate-800 px-3 py-1.5 rounded-xl">
            <span className="text-xs text-slate-400 font-medium">Deal Context:</span>
            <select
              value={selectedDealId}
              onChange={(e) => setSelectedDealId(e.target.value)}
              className="bg-transparent text-xs text-slate-200 font-semibold focus:outline-none cursor-pointer pr-2"
            >
              <option value="" className="bg-slate-900 text-slate-400">
                🌐 General Knowledge Mode (No Deal Selected)
              </option>
              {deals.map((deal) => (
                <option key={deal.id} value={deal.id} className="bg-slate-900 text-white">
                  {deal.reference} — {deal.buyer_name} ({deal.state})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleSyncDocs}
            disabled={isSyncingDocs}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/60 transition shadow-sm disabled:opacity-50"
            title="Re-chunk and sync editable markdown files from backend/data/docs to Qdrant"
          >
            <span>{isSyncingDocs ? '⏳' : '🔄'}</span>
            <span>{isSyncingDocs ? 'Syncing...' : 'Sync Docs DB'}</span>
          </button>
        </div>
      </header>

      {/* Notification Toast for Sync */}
      {syncStatusMsg && (
        <div className="bg-indigo-600/20 border-b border-indigo-500/30 text-indigo-300 px-6 py-1.5 text-xs text-center font-medium animate-fadeIn">
          {syncStatusMsg}
        </div>
      )}

      {/* ── Main Layout: Chat (Left) + Intelligence Radar & Tools (Right) ─ */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        {/* ── Left Column: Multi-turn Chat Console (60% width) ───── */}
        <div className="flex-1 flex flex-col bg-slate-950/60 border-r border-slate-800/80 overflow-hidden">
          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-3xl ${
                  msg.role === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
                }`}
              >
                {/* Avatar */}
                <div
                  className={`w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold flex-shrink-0 shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-gradient-to-tr from-indigo-600 to-indigo-500 text-white'
                      : 'bg-slate-800 text-emerald-400 border border-slate-700'
                  }`}
                >
                  {msg.role === 'user' ? 'YOU' : '🤖'}
                </div>

                {/* Message Bubble */}
                <div
                  className={`flex flex-col space-y-2 rounded-2xl p-4 text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-indigo-600 text-white rounded-tr-none shadow-md shadow-indigo-600/10'
                      : 'bg-slate-900/90 border border-slate-800 text-slate-200 rounded-tl-none shadow-sm'
                  }`}
                >
                  {/* Text with markdown formatting */}
                  <div className="whitespace-pre-wrap font-normal">{msg.text}</div>

                  {/* Readiness Snapshot in Bot Response */}
                  {msg.readiness && (
                    <div className="mt-2 p-3 bg-slate-950/80 rounded-xl border border-slate-800/80 text-xs">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-slate-300">
                          Live Readiness Inspection: {msg.readiness.reference}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            msg.readiness.is_ready_to_ship
                              ? 'bg-emerald-500/20 text-emerald-400'
                              : 'bg-rose-500/20 text-rose-400'
                          }`}
                        >
                          Score: {msg.readiness.score_percentage}%
                        </span>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                        {msg.readiness.pillars.map((p) => (
                          <div
                            key={p.key}
                            className="bg-slate-900/60 p-1.5 rounded border border-slate-800 flex items-center gap-1.5"
                          >
                            <span className="text-xs">{PILLAR_ICONS[p.key] || '📋'}</span>
                            <span
                              className={`text-[10px] font-semibold truncate ${
                                PILLAR_STATUS_THEMES[p.status]?.text || 'text-slate-300'
                              }`}
                            >
                              {p.name.split(' ')[0]}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Grounding Citations */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="pt-2 mt-2 border-t border-slate-800/60 flex flex-wrap items-center gap-1.5">
                      <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 flex items-center gap-1">
                        <span>📚 Sources:</span>
                      </span>
                      {msg.citations.map((c, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-300 border border-slate-700/60"
                        >
                          {c}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Expandable Retrieved Vector Chunks Drawer */}
                  {msg.retrieved_chunks && msg.retrieved_chunks.length > 0 && (
                    <details className="mt-1 group">
                      <summary className="text-[10px] text-indigo-400 hover:text-indigo-300 cursor-pointer list-none flex items-center gap-1 select-none font-semibold">
                        <span className="group-open:rotate-90 transition-transform">▶</span>
                        <span>
                          Inspect {msg.retrieved_chunks.length} Grounded Qdrant Vector Matches
                        </span>
                      </summary>
                      <div className="mt-2 space-y-1.5 pl-2 border-l-2 border-indigo-500/30">
                        {msg.retrieved_chunks.map((chunk, idx) => (
                          <div
                            key={idx}
                            className="p-2 rounded bg-slate-950/90 border border-slate-800/80 text-[11px] text-slate-300"
                          >
                            <div className="flex items-center justify-between font-mono text-[10px] text-slate-400 mb-1">
                              <span className="text-indigo-400 font-semibold">{chunk.source}</span>
                              <span className="bg-slate-900 px-1.5 py-0.2 rounded text-slate-400">
                                Score: {(chunk.score * 100).toFixed(1)}%
                              </span>
                            </div>
                            <p className="line-clamp-3 text-slate-300 italic">{chunk.text}</p>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}

                  <span className="text-[10px] text-slate-400 self-end pt-1">
                    {msg.timestamp}
                  </span>
                </div>
              </div>
            ))}

            {isAsking && (
              <div className="flex gap-3 max-w-xl mr-auto">
                <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-xs text-emerald-400">
                  🤖
                </div>
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl rounded-tl-none p-4 flex items-center gap-2">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce"></span>
                    <span
                      className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce"
                      style={{ animationDelay: '0.2s' }}
                    ></span>
                    <span
                      className="w-2 h-2 rounded-full bg-cyan-500 animate-bounce"
                      style={{ animationDelay: '0.4s' }}
                    ></span>
                  </div>
                  <span className="text-xs text-slate-400 italic">
                    Retrieving from Qdrant vector database & verifying deal readiness...
                  </span>
                </div>
              </div>
            )}

            <div ref={chatBottomRef} />
          </div>

          {/* Suggested Quick Prompt Chips */}
          <div className="px-4 py-2 bg-slate-900/40 border-t border-slate-800/50 flex items-center gap-2 overflow-x-auto no-scrollbar">
            <span className="text-[11px] text-slate-500 font-semibold whitespace-nowrap">
              Suggested:
            </span>
            {[
              'Is this order ready to ship?',
              'What documents or compliance items are missing?',
              'Explain the SBP 120-day realization deadline',
              'Draft shipping dispatch advice for buyer',
            ].map((prompt, i) => (
              <button
                key={i}
                onClick={() => handleSendMessage(prompt)}
                disabled={isAsking}
                className="px-2.5 py-1 rounded-full text-xs bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/60 whitespace-nowrap transition disabled:opacity-40"
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <div className="p-4 bg-slate-900/80 border-t border-slate-800/80">
            <div className="relative flex items-center">
              <textarea
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  selectedDeal
                    ? `Ask about ${selectedDeal.reference} (${selectedDeal.buyer_name}) or export regulations...`
                    : 'Ask any question on export rules, Incoterms, or select a deal above...'
                }
                rows={1}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-4 pr-24 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 resize-none"
              />
              <div className="absolute right-2 flex items-center gap-1.5">
                <button
                  onClick={() => handleSendMessage()}
                  disabled={!inputQuery.trim() || isAsking}
                  className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white text-xs font-semibold rounded-lg shadow-sm shadow-indigo-600/20 transition flex items-center gap-1.5"
                >
                  <span>Send</span>
                  <span>↗</span>
                </button>
              </div>
            </div>
            <p className="text-[10px] text-slate-500 mt-1.5 text-right">
              Press Enter to send · Shift+Enter for new line
            </p>
          </div>
        </div>

        {/* ── Right Column: Readiness Radar & Copilot Tools (40% width) ─ */}
        <div className="w-full lg:w-[460px] flex flex-col bg-slate-900/50 border-l border-slate-800/80 overflow-hidden flex-shrink-0">
          {/* Side Tabs Header */}
          <div className="flex items-center border-b border-slate-800/80 bg-slate-900 px-4 pt-3">
            {[
              { id: 'readiness', label: '7-Pillar Radar', icon: '🎯' },
              { id: 'drafter', label: 'Commercial Drafter', icon: '✉️' },
              { id: 'knowledge', label: 'Regulatory Docs', icon: '📚' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveSideTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-2.5 text-xs font-semibold border-b-2 transition ${
                  activeSideTab === tab.id
                    ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {/* Side Panel Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* ── TAB 1: 7-Pillar "Ready-to-Ship" Radar ──────────── */}
            {activeSideTab === 'readiness' && (
              <div className="space-y-4">
                {!selectedDealId ? (
                  <div className="p-6 text-center bg-slate-950/60 border border-slate-800 rounded-2xl">
                    <span className="text-3xl block mb-2">📋</span>
                    <h3 className="text-sm font-semibold text-slate-300">
                      No Deal Selected
                    </h3>
                    <p className="text-xs text-slate-500 mt-1">
                      Select a deal from the top bar dropdown to calculate live 7-pillar export readiness.
                    </p>
                  </div>
                ) : isLoadingReadiness ? (
                  <div className="p-8 text-center text-slate-400 text-xs flex flex-col items-center gap-2">
                    <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                    <span>Auditing deal across 7 readiness pillars...</span>
                  </div>
                ) : readinessError ? (
                  <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-xs">
                    {readinessError}
                  </div>
                ) : readiness ? (
                  <>
                    {/* Overall Score Gauge Card */}
                    <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-2xl shadow-sm">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">
                            Ready-to-Ship Radar
                          </span>
                          <h2 className="text-base font-bold text-white mt-0.5">
                            {readiness.reference}
                          </h2>
                          <p className="text-xs text-slate-400 truncate">
                            Buyer: {readiness.buyer_name}
                          </p>
                        </div>

                        {/* Circular Score Badge */}
                        <div className="flex flex-col items-center">
                          <div
                            className={`w-14 h-14 rounded-2xl flex flex-col items-center justify-center font-black text-lg border shadow-sm ${
                              readiness.is_ready_to_ship
                                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                                : readiness.score_percentage >= 50
                                ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                                : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                            }`}
                          >
                            <span>{readiness.score_percentage}%</span>
                          </div>
                          <span
                            className={`text-[9px] font-bold mt-1 px-1.5 py-0.5 rounded ${
                              readiness.is_ready_to_ship
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : 'bg-slate-800 text-slate-300'
                            }`}
                          >
                            {readiness.overall_status}
                          </span>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800">
                        <div
                          className={`h-full transition-all duration-500 ${
                            readiness.is_ready_to_ship
                              ? 'bg-emerald-500'
                              : readiness.score_percentage >= 50
                              ? 'bg-amber-500'
                              : 'bg-rose-500'
                          }`}
                          style={{ width: `${readiness.score_percentage}%` }}
                        ></div>
                      </div>
                    </div>

                    {/* Critical Blockers Alert */}
                    {readiness.blockers && readiness.blockers.length > 0 && (
                      <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl space-y-1.5">
                        <div className="flex items-center gap-1.5 text-xs font-bold text-rose-400">
                          <span>❌</span>
                          <span>Critical Action Required ({readiness.blockers.length} Blockers)</span>
                        </div>
                        <ul className="space-y-1 pl-5 list-disc text-xs text-rose-300">
                          {readiness.blockers.map((b, i) => (
                            <li key={i}>{b}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* 7 Pillars Breakdown Cards */}
                    <div className="space-y-2">
                      <span className="text-[11px] uppercase font-bold tracking-wider text-slate-400">
                        7 Deterministic Pillars
                      </span>
                      {readiness.pillars.map((pillar) => {
                        const theme = PILLAR_STATUS_THEMES[pillar.status] || PILLAR_STATUS_THEMES.BLOCKED;
                        return (
                          <div
                            key={pillar.key}
                            className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-1 hover:border-slate-700 transition"
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <span className="text-sm">{PILLAR_ICONS[pillar.key] || '📋'}</span>
                                <span className="text-xs font-semibold text-slate-200">
                                  {pillar.name}
                                </span>
                              </div>
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold border ${theme.badge}`}
                              >
                                {theme.icon} {pillar.status}
                              </span>
                            </div>
                            <p className="text-xs text-slate-300 leading-tight">
                              {pillar.message}
                            </p>
                            {pillar.evidence && (
                              <p className="text-[11px] font-mono text-slate-400 pt-0.5">
                                ↳ {pillar.evidence}
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </>
                ) : null}
              </div>
            )}

            {/* ── TAB 2: Commercial Drafter (Human Gate) ─────────── */}
            {activeSideTab === 'drafter' && (
              <div className="space-y-4">
                <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-2xl space-y-3">
                  <div>
                    <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">
                      Human-in-the-Loop Correspondence Gate (FR-COP-05)
                    </span>
                    <h3 className="text-sm font-semibold text-white mt-0.5">
                      Draft Export Commercial Email
                    </h3>
                    <p className="text-xs text-slate-400">
                      All correspondence is strictly gated and requires human approval before sending.
                    </p>
                  </div>

                  {/* Template Picker */}
                  <div>
                    <label className="text-xs font-medium text-slate-300 block mb-1">
                      Select Correspondence Template:
                    </label>
                    <select
                      value={draftTemplate}
                      onChange={(e) => setDraftTemplate(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 font-semibold focus:outline-none focus:border-indigo-500"
                    >
                      <option value="ORDER_CONFIRMATION">
                        1. Order Confirmation & Proforma Notice
                      </option>
                      <option value="SHIPPING_ADVICE">
                        2. Shipping Advice & Dispatch Notification
                      </option>
                      <option value="PAYMENT_REMINDER_SBP">
                        3. SBP Form-E Payment & Realization Notice
                      </option>
                      <option value="COMMERCIAL_UPDATE">
                        4. General Commercial Update
                      </option>
                    </select>
                  </div>

                  {/* Optional Custom Notes */}
                  <div>
                    <label className="text-xs font-medium text-slate-300 block mb-1">
                      Custom Notes or Instructions (Optional):
                    </label>
                    <textarea
                      value={draftNotes}
                      onChange={(e) => setDraftNotes(e.target.value)}
                      placeholder="e.g. Please expedite payment due to 120-day SBP deadline..."
                      rows={2}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
                    />
                  </div>

                  {/* Generate Button */}
                  <button
                    onClick={handleGenerateDraft}
                    disabled={isDrafting || !selectedDealId}
                    className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-semibold text-xs rounded-xl shadow-md shadow-indigo-600/20 transition flex items-center justify-center gap-2"
                  >
                    <span>{isDrafting ? '⏳' : '✍️'}</span>
                    <span>{isDrafting ? 'Drafting...' : 'Generate Grounded Email Draft'}</span>
                  </button>
                </div>

                {/* Draft Output Preview */}
                {draftResult && (
                  <div className="p-4 bg-slate-950 border border-indigo-500/30 rounded-2xl space-y-3 animate-fadeIn">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          🔒 Gated Draft (Review Required)
                        </span>
                      </div>
                      <button
                        onClick={handleCopyDraft}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg border border-slate-700 font-medium transition flex items-center gap-1"
                      >
                        <span>{copySuccess ? '✓ Copied!' : '📋 Copy Text'}</span>
                      </button>
                    </div>

                    <div>
                      <span className="text-[10px] text-slate-500 uppercase font-bold">Subject:</span>
                      <p className="text-xs font-semibold text-slate-200">{draftResult.subject}</p>
                    </div>

                    <div>
                      <span className="text-[10px] text-slate-500 uppercase font-bold">Message Body:</span>
                      <div className="mt-1 p-3 bg-slate-900/90 rounded-xl border border-slate-800 text-xs text-slate-300 font-mono whitespace-pre-wrap max-h-60 overflow-y-auto leading-relaxed">
                        {draftResult.body}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── TAB 3: Regulatory Docs (Editable Directory) ───── */}
            {activeSideTab === 'knowledge' && (
              <div className="space-y-3">
                <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-2xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">
                      Knowledge Corpus Directory
                    </span>
                    <span className="text-[10px] font-mono bg-slate-900 px-2 py-0.5 rounded text-indigo-400">
                      backend/data/docs/
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Editable markdown files ingested into Qdrant Vector Database with automatic change detection.
                  </p>
                </div>

                {[
                  {
                    name: 'sbp_fe_manual_chapter_xii.md',
                    title: 'SBP Foreign Exchange Manual (Chapter XII)',
                    desc: '120-day foreign currency realization deadline, Form-E reconciliation & Authorized Dealer requirements.',
                    tag: 'SBP REGULATION',
                  },
                  {
                    name: 'sbp_fe_circulars.md',
                    title: 'SBP FE Circulars & Retention Limit Rules',
                    desc: 'Foreign currency retention account allowances and penalty matrix for overdue export proceeds.',
                    tag: 'CIRCULAR',
                  },
                  {
                    name: 'destination_customs_eu_rex.md',
                    title: 'EU Registered Exporter System (REX) & GSP+',
                    desc: 'Preferential tariff declaration on invoice for consignments exceeding €6,000 to EU member states.',
                    tag: 'EU CUSTOMS',
                  },
                  {
                    name: 'destination_customs_us_cbp.md',
                    title: 'US Customs and Border Protection (CBP) Rules',
                    desc: 'ISF 10+2 filing 24hr prior to loading, C-TPAT security seal standards, and FDA prior notice.',
                    tag: 'US CBP',
                  },
                  {
                    name: 'incoterms_2020_rules.md',
                    title: 'ICC Incoterms 2020 Commercial Matrix',
                    desc: 'FOB vs CFR vs CIF risk division points, seller freight & insurance obligations, and port delivery.',
                    tag: 'INCOTERMS',
                  },
                  {
                    name: 'tdap_export_policy.md',
                    title: 'TDAP Export Policy Order & Subsidies',
                    desc: 'Duty drawback scheme, certification subsidies, and zero-rated export processing protocols.',
                    tag: 'TDAP POLICY',
                  },
                ].map((doc, i) => (
                  <div
                    key={i}
                    className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-1 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono text-indigo-400 font-semibold truncate max-w-[220px]">
                        {doc.name}
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-slate-800 text-slate-400 border border-slate-700">
                        {doc.tag}
                      </span>
                    </div>
                    <h4 className="text-xs font-semibold text-slate-200">{doc.title}</h4>
                    <p className="text-[11px] text-slate-400">{doc.desc}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
