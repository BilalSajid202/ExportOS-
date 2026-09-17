import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';

const DEAL_STATES = [
  { key: 'INQUIRY', label: 'Inquiry', icon: '📩' },
  { key: 'QUOTED', label: 'Quoted', icon: '📑' },
  { key: 'CONFIRMED', label: 'Confirmed', icon: '🤝' },
  { key: 'IN_PRODUCTION', label: 'In Production', icon: '⚙️' },
  { key: 'DOCS_READY', label: 'Docs Ready', icon: '📄' },
  { key: 'SHIPPED', label: 'Shipped', icon: '🚢' },
  { key: 'PAID', label: 'Paid', icon: '💰' },
  { key: 'CLOSED', label: 'Closed', icon: '🏁' },
];

const INCOTERMS = [
  { code: 'EXW', name: 'Ex Works (Factory)', desc: 'Product + Packaging' },
  { code: 'FCA', name: 'Free Carrier', desc: 'EXW + Inland Freight + Clearance' },
  { code: 'FOB', name: 'Free on Board', desc: 'FCA + Origin Port Handling' },
  { code: 'CFR', name: 'Cost and Freight', desc: 'FOB + Ocean/Air Freight' },
  { code: 'CIF', name: 'Cost, Insurance & Freight', desc: 'CFR + Marine Cargo Insurance' },
  { code: 'CPT', name: 'Carriage Paid To', desc: 'FCA + Main Freight to Place' },
  { code: 'CIP', name: 'Carriage & Insurance Paid', desc: 'CPT + Cargo Insurance' },
  { code: 'DAP', name: 'Delivered at Place', desc: 'CFR/CPT + Destination Place Delivery' },
  { code: 'DDP', name: 'Delivered Duty Paid', desc: 'DAP + Destination Import Duties' },
];

const COST_TYPES = [
  { value: 'PRODUCT_BASE', label: 'Base Product Cost' },
  { value: 'PACKAGING', label: 'Export Packaging / Crating' },
  { value: 'INLAND_FREIGHT', label: 'Inland Transport (Factory to Port)' },
  { value: 'PORT_HANDLING', label: 'Port Handling / THC Origin' },
  { value: 'EXPORT_CLEARANCE', label: 'Export Clearance & Customs (WeBOC)' },
  { value: 'OCEAN_FREIGHT', label: 'Ocean Freight (FCL/LCL)' },
  { value: 'AIR_FREIGHT', label: 'Air Freight' },
  { value: 'INSURANCE', label: 'Marine Cargo Insurance' },
  { value: 'IMPORT_DUTIES', label: 'Destination Duties & Tariffs' },
  { value: 'OTHER', label: 'Inspection / Certification / Other' },
];

const STATUS_STYLES = {
  AVAILABLE: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  PARTIALLY_AVAILABLE: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  UNAVAILABLE: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
};

const CONFIDENCE_BADGES = (conf) => {
  if (conf >= 0.85) return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
  if (conf >= 0.60) return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
  return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
};

function formatQty(value) {
  if (value == null) return '—';
  const n = Number(value);
  return Number.isInteger(n) ? String(n) : n.toLocaleString();
}

function formatMoney(value, currency = 'USD') {
  if (value == null) return '—';
  return `${currency} ${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function Deals() {
  const { dealId } = useParams();
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();
  const canCreate = isAdmin || ['EXPORT_MANAGER', 'SALES'].includes(user?.role);
  const canApproveQuote = isAdmin || user?.role === 'EXPORT_MANAGER';
  const canManageDocs = isAdmin || ['EXPORT_MANAGER', 'DOCUMENTATION_OFFICER'].includes(user?.role);
  const canReserve = isAdmin || ['EXPORT_MANAGER', 'ACCOUNTS'].includes(user?.role);

  const [deals, setDeals] = useState([]);
  const [deal, setDeal] = useState(null);
  const [availability, setAvailability] = useState(null);
  const [costing, setCosting] = useState(null);
  const [auditLog, setAuditLog] = useState([]);
  const [documentSet, setDocumentSet] = useState(null);
  const [consistency, setConsistency] = useState(null);
  const [products, setProducts] = useState([]);
  const [activeTab, setActiveTab] = useState('inventory'); // 'inventory', 'costing', 'documents', 'audit'

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  // Create Deal Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState('');
  const [form, setForm] = useState({
    buyer_name: '',
    notes: '',
    product_id: '',
    quantity: '',
  });

  // AI Extraction State
  const [extraction, setExtraction] = useState(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionError, setExtractionError] = useState('');
  const [extractionSuccess, setExtractionSuccess] = useState('');
  const [editableFields, setEditableFields] = useState({});

  // Cost Component Modal
  const [isCostModalOpen, setIsCostModalOpen] = useState(false);
  const [costForm, setCostForm] = useState({
    cost_type: 'PRODUCT_BASE',
    description: '',
    amount: '',
    currency: 'USD',
  });

  // Quote Generation Form
  const [quoteForm, setQuoteForm] = useState({
    incoterm: 'CIF',
    incoterm_place: 'Hamburg, Germany',
    margin_percentage: '15.00',
    currency: 'USD',
    notes: 'Standard 14-day validity quote',
  });
  const [isQuoting, setIsQuoting] = useState(false);

  // Document Preview Modal
  const [previewDoc, setPreviewDoc] = useState(null);
  const [previewHtml, setPreviewHtml] = useState('');
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const [isGeneratingDocs, setIsGeneratingDocs] = useState(false);

  // Transition State Modal
  const [isTransitionModalOpen, setIsTransitionModalOpen] = useState(false);
  const [transitionTarget, setTransitionTarget] = useState('');
  const [transitionReason, setTransitionReason] = useState('');

  const loadDeals = async () => {
    setIsLoading(true);
    try {
      const data = await api.get('/deals');
      setDeals(data);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load deals');
    } finally {
      setIsLoading(false);
    }
  };

  const loadDeal = async (id) => {
    setIsLoading(true);
    try {
      const [d, avail, cost, logs] = await Promise.all([
        api.get(`/deals/${id}`),
        api.get(`/deals/${id}/availability`),
        api.get(`/deals/${id}/costing`),
        api.get(`/deals/${id}/audit-trail`),
      ]);
      setDeal(d);
      setAvailability(avail);
      setCosting(cost);
      setAuditLog(logs);
      setError('');

      // Try loading extraction
      try {
        const ext = await api.get(`/deals/${id}/extraction`);
        setExtraction(ext);
        initEditableFields(ext.extracted_data);
      } catch {
        setExtraction(null);
      }

      // Try loading documents & consistency audit
      try {
        const docs = await api.get(`/deals/${id}/documents`);
        setDocumentSet(docs);
        if (docs) {
          try {
            const auditRes = await api.get(`/deals/${id}/documents/consistency-check`);
            setConsistency(auditRes);
          } catch {
            setConsistency(null);
          }
        } else {
          setConsistency(null);
        }
      } catch {
        setDocumentSet(null);
        setConsistency(null);
      }
    } catch (err) {
      setError(err.message || 'Failed to load deal');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (dealId) loadDeal(dealId);
    else loadDeals();
  }, [dealId]);

  const initEditableFields = (data) => {
    if (!data) return;
    const initial = {};
    Object.keys(data).forEach((k) => {
      initial[k] = data[k]?.value ?? '';
    });
    setEditableFields(initial);
  };

  const runAIExtraction = async () => {
    if (!deal) return;
    setIsExtracting(true);
    setExtractionError('');
    setExtractionSuccess('');
    try {
      const res = await api.post(`/deals/${deal.id}/extract`);
      setExtraction(res);
      initEditableFields(res.extracted_data);
      setExtractionSuccess('AI extraction completed successfully with Qwen.');
    } catch (err) {
      setExtractionError(err.message || 'AI extraction failed');
    } finally {
      setIsExtracting(false);
    }
  };

  const confirmExtraction = async () => {
    if (!deal || !extraction) return;
    setIsExtracting(true);
    setExtractionError('');
    setExtractionSuccess('');
    try {
      const payloadFields = {};
      Object.keys(editableFields).forEach((k) => {
        payloadFields[k] = {
          value: editableFields[k],
          confirmation_status: 'CONFIRMED',
        };
      });

      const updated = await api.post(`/deals/${deal.id}/extraction/confirm`, {
        fields: payloadFields,
        auto_create_line_item: true,
      });
      setExtraction(updated);
      setExtractionSuccess('Confirmed terms & matched product with catalog!');
      await loadDeal(deal.id);
    } catch (err) {
      setExtractionError(err.message || 'Failed to confirm extraction');
    } finally {
      setIsExtracting(false);
    }
  };

  const handleShortfallAction = async (productId, action) => {
    try {
      await api.post(`/deals/${deal.id}/resolve-shortfall`, {
        product_id: productId,
        action: action,
      });
      setActionSuccess(`Shortfall action applied: ${action.replace(/_/g, ' ')}`);
      await loadDeal(deal.id);
    } catch (err) {
      setError(err.message || 'Failed to apply shortfall decision');
    }
  };

  const handleReserveStock = async () => {
    try {
      await api.post(`/deals/${deal.id}/reserve`);
      setActionSuccess('Inventory successfully reserved for this deal!');
      await loadDeal(deal.id);
    } catch (err) {
      setError(err.message || 'Failed to reserve inventory');
    }
  };

  const handleConfirmOrder = async () => {
    try {
      await api.post(`/deals/${deal.id}/confirm`);
      setActionSuccess('Order confirmed! Deal state moved to CONFIRMED & stock reserved.');
      await loadDeal(deal.id);
    } catch (err) {
      setError(err.message || 'Failed to confirm order');
    }
  };

  const handleGenerateDocuments = async () => {
    setIsGeneratingDocs(true);
    try {
      const docSetRes = await api.post(`/deals/${deal.id}/documents/generate`, {
        override_port_of_loading: 'Karachi Port (PKBQM/PKKHI), Pakistan',
        payment_terms: '100% LC at sight',
      });
      setDocumentSet(docSetRes);
      setActionSuccess(`Generated complete export document set (Revision #${docSetRes.revision_number})!`);
      await loadDeal(deal.id);
      setActiveTab('documents');
    } catch (err) {
      setError(err.message || 'Failed to generate document set');
    } finally {
      setIsGeneratingDocs(false);
    }
  };

  const openDocumentPreview = async (doc) => {
    setPreviewDoc(doc);
    setIsPreviewLoading(true);
    try {
      const res = await fetch(`/api/documents/${doc.id}/html`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('exportos_access_token')}`,
        },
      });
      const html = await res.text();
      setPreviewHtml(html);
    } catch (err) {
      setError(err.message || 'Failed to load document preview');
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleApproveDocument = async (docId) => {
    try {
      await api.post(`/documents/${docId}/approve`);
      setActionSuccess('Document officially approved!');
      await loadDeal(deal.id);
    } catch (err) {
      setError(err.message || 'Failed to approve document');
    }
  };

  const handleAddCostComponent = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/deals/${deal.id}/costing`, {
        cost_type: costForm.cost_type,
        description: costForm.description,
        amount: Number(costForm.amount),
        currency: costForm.currency,
      });
      setIsCostModalOpen(false);
      setCostForm({ cost_type: 'PRODUCT_BASE', description: '', amount: '', currency: 'USD' });
      await loadDeal(deal.id);
    } catch (err) {
      setError(err.message || 'Failed to add cost component');
    }
  };

  const handleDeleteCostComponent = async (compId) => {
    try {
      await api.delete(`/deals/${deal.id}/costing/${compId}`);
      await loadDeal(deal.id);
    } catch (err) {
      setError(err.message || 'Failed to delete cost component');
    }
  };

  const handleCalculateQuote = async (e) => {
    e.preventDefault();
    setIsQuoting(true);
    try {
      await api.post(`/deals/${deal.id}/quote`, {
        incoterm: quoteForm.incoterm,
        incoterm_place: quoteForm.incoterm_place,
        margin_percentage: Number(quoteForm.margin_percentage),
        currency: quoteForm.currency,
        notes: quoteForm.notes,
      });
      setActionSuccess('Quotation calculated successfully!');
      await loadDeal(deal.id);
    } catch (err) {
      setError(err.message || 'Failed to calculate quote');
    } finally {
      setIsQuoting(false);
    }
  };

  const handleApproveQuote = async () => {
    try {
      await api.post(`/deals/${deal.id}/quote/approve`, {
        notes: 'Approved by Export Manager',
      });
      setActionSuccess('Quote officially approved! Deal state advanced to QUOTED.');
      await loadDeal(deal.id);
    } catch (err) {
      setError(err.message || 'Failed to approve quote');
    }
  };

  const handleTransitionState = async () => {
    if (!transitionTarget) return;
    try {
      await api.post(`/deals/${deal.id}/transition`, {
        target_state: transitionTarget,
        reason: transitionReason || null,
      });
      setIsTransitionModalOpen(false);
      setTransitionTarget('');
      setTransitionReason('');
      setActionSuccess(`Deal transitioned to ${transitionTarget}!`);
      await loadDeal(deal.id);
    } catch (err) {
      setError(err.message || 'Failed to transition deal state');
    }
  };

  const openCreate = async () => {
    const prods = await api.get('/products');
    setProducts(prods);
    setForm({ buyer_name: '', notes: '', product_id: '', quantity: '' });
    setModalError('');
    setIsModalOpen(true);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setModalError('');
    setIsSubmitting(true);
    try {
      const created = await api.post('/deals', {
        buyer_name: form.buyer_name,
        notes: form.notes || null,
        line_items: form.product_id
          ? [
              {
                product_id: form.product_id,
                quantity: Number(form.quantity),
              },
            ]
          : [],
      });
      setIsModalOpen(false);
      navigate(`/deals/${created.id}`);
    } catch (err) {
      setModalError(err.message || 'Failed to create deal');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Stepper calculations
  const currentStateIdx = DEAL_STATES.findIndex((s) => s.key === deal?.state);

  return (
    <div className="space-y-6">
      {/* ── Detail View ────────────────────────────────────────────── */}
      {dealId && deal ? (
        <div className="space-y-6">
          {/* Header Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 shadow-2xl backdrop-blur-xl">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
              <div>
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <Link to="/deals" className="hover:text-white transition">
                    ← Deals
                  </Link>
                  <span>/</span>
                  <span className="font-mono text-indigo-400 font-semibold">{deal.reference}</span>
                  <span>/</span>
                  <span className="text-slate-300">{deal.buyer_name}</span>
                </div>
                <h1 className="text-3xl font-extrabold text-white tracking-tight mt-1 flex items-center gap-3">
                  {deal.buyer_name}
                  <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                    {deal.state}
                  </span>
                </h1>
                <p className="text-xs text-slate-400 mt-1">
                  Created {new Date(deal.created_at).toLocaleString()} • Deal ID: <span className="font-mono">{deal.id.slice(0, 8)}...</span>
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-3">
                {deal.state === 'QUOTED' && (
                  <button
                    onClick={handleConfirmOrder}
                    className="px-4 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-emerald-600/20 transition flex items-center gap-1.5"
                  >
                    <span>🤝</span> Confirm Order (Phase 9)
                  </button>
                )}

                {canManageDocs && (
                  <button
                    onClick={handleGenerateDocuments}
                    disabled={isGeneratingDocs}
                    className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-600/20 transition flex items-center gap-1.5 disabled:opacity-50"
                  >
                    {isGeneratingDocs ? 'Generating Docs...' : '📄 Generate Export Document Set'}
                  </button>
                )}

                <button
                  onClick={runAIExtraction}
                  disabled={isExtracting}
                  className="px-4 py-2.5 bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-700 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-600/20 transition flex items-center gap-2 disabled:opacity-50"
                >
                  {isExtracting ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                      <span>Extracting (Qwen)...</span>
                    </>
                  ) : (
                    <>
                      <span>🤖</span> Run AI Ingestion
                    </>
                  )}
                </button>

                {canCreate && (
                  <button
                    onClick={() => {
                      setTransitionTarget('');
                      setIsTransitionModalOpen(true);
                    }}
                    className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-xs font-semibold transition flex items-center gap-1.5"
                  >
                    <span>⚡</span> Transition State
                  </button>
                )}
              </div>
            </div>

            {/* Deal State Machine Stepper */}
            <div className="mt-8 pt-6 border-t border-slate-800/80">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-3">
                Lifecycle Progression
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
                {DEAL_STATES.map((st, idx) => {
                  const isCurrent = deal.state === st.key;
                  const isPast = currentStateIdx > idx;
                  return (
                    <div
                      key={st.key}
                      className={`p-2.5 rounded-xl border text-center transition flex flex-col items-center justify-center ${
                        isCurrent
                          ? 'bg-indigo-600/20 border-indigo-500 text-white font-bold ring-2 ring-indigo-500/20 shadow-lg shadow-indigo-600/20'
                          : isPast
                          ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                          : 'bg-slate-950/40 border-slate-800/60 text-slate-500'
                      }`}
                    >
                      <div className="text-sm mb-0.5">{isPast ? '✓' : st.icon}</div>
                      <div className="text-[11px] leading-tight font-medium">{st.label}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Feedback Alerts */}
          {error && (
            <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400 text-xs flex items-center justify-between">
              <span>{error}</span>
              <button onClick={() => setError('')} className="text-rose-400 hover:text-white">✕</button>
            </div>
          )}
          {actionSuccess && (
            <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl text-emerald-400 text-xs flex items-center justify-between">
              <span>{actionSuccess}</span>
              <button onClick={() => setActionSuccess('')} className="text-emerald-400 hover:text-white">✕</button>
            </div>
          )}

          {/* AI Extraction Panel */}
          {extraction && (
            <div className="bg-slate-900/90 border border-indigo-500/30 rounded-3xl p-6 shadow-2xl space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 text-lg">
                    🤖
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white">AI Extraction Review & Grounding</h2>
                    <p className="text-xs text-slate-400 font-mono">
                      Qwen 2.5 32B • Status: <span className="text-indigo-400 font-bold">{extraction.status}</span>
                    </p>
                  </div>
                </div>
                <button
                  onClick={confirmExtraction}
                  disabled={isExtracting}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-emerald-600/20 transition flex items-center gap-1.5"
                >
                  <span>✓</span> Confirm & Match Products
                </button>
              </div>

              {extractionError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs">
                  {extractionError}
                </div>
              )}
              {extractionSuccess && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400 text-xs">
                  {extractionSuccess}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 pt-1">
                {Object.entries(extraction.extracted_data || {}).map(([key, item]) => {
                  const conf = item?.confidence || 0;
                  const percent = Math.round(conf * 100);
                  return (
                    <div key={key} className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-2xl space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-300 capitalize">
                          {key.replace(/_/g, ' ')}
                        </span>
                        {item?.value !== null && item?.value !== undefined && (
                          <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${CONFIDENCE_BADGES(conf)}`}>
                            {percent}% conf
                          </span>
                        )}
                      </div>
                      <input
                        type="text"
                        value={editableFields[key] ?? ''}
                        onChange={(e) => setEditableFields({ ...editableFields, [key]: e.target.value })}
                        placeholder="Not specified"
                        className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700/80 rounded-lg text-slate-100 font-medium text-xs focus:outline-none focus:border-indigo-500"
                      />
                      {item?.evidence && (
                        <div className="text-[11px] text-slate-400 bg-slate-900/60 p-2 rounded-lg border border-slate-800/60 italic truncate" title={item.evidence}>
                          <span className="text-slate-400 not-italic font-semibold block text-[10px]">Evidence:</span>
                          "{item.evidence}"
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Navigation Tabs for Sections */}
          <div className="flex border-b border-slate-800 gap-6 text-sm font-semibold">
            <button
              onClick={() => setActiveTab('inventory')}
              className={`pb-3 px-1 transition relative ${
                activeTab === 'inventory' ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              📦 Inventory & Stock Check
            </button>
            <button
              onClick={() => setActiveTab('costing')}
              className={`pb-3 px-1 transition relative ${
                activeTab === 'costing' ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              💵 Incoterm Costing & Quotation
            </button>
            <button
              onClick={() => setActiveTab('documents')}
              className={`pb-3 px-1 transition relative ${
                activeTab === 'documents' ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              📄 Export Documents & Consistency ({documentSet?.documents?.length || 0})
            </button>
            <button
              onClick={() => setActiveTab('audit')}
              className={`pb-3 px-1 transition relative ${
                activeTab === 'audit' ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              📜 Audit Trail ({auditLog.length})
            </button>
          </div>

          {/* ── TAB 1: Inventory & Shortfall ──────────────────────────── */}
          {activeTab === 'inventory' && (
            <div className="space-y-6">
              {availability?.lines?.some((l) => l.shortfall > 0) && (
                <div className="p-5 bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent border border-amber-500/30 rounded-3xl space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">⚠️</span>
                    <div>
                      <h3 className="text-sm font-bold text-amber-300">Inventory Shortfall Detected</h3>
                      <p className="text-xs text-amber-200/80">
                        Current warehouse stock is insufficient to fulfill the full requested order immediately.
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-3 pt-1">
                    {availability.lines
                      .filter((l) => l.shortfall > 0)
                      .map((l) => (
                        <div key={l.product_id} className="flex flex-wrap items-center gap-2 text-xs bg-slate-950/60 p-2.5 rounded-xl border border-amber-500/20">
                          <span className="font-semibold text-white">{l.sku}:</span>
                          <span className="text-slate-400">Avail: {formatQty(l.available_quantity)} {l.unit_of_measure}</span>
                          <span className="text-rose-400 font-bold">Short: {formatQty(l.shortfall)} {l.unit_of_measure}</span>
                          <button
                            onClick={() => handleShortfallAction(l.product_id, 'REDUCE_TO_AVAILABLE')}
                            className="ml-2 px-2.5 py-1 bg-amber-600 hover:bg-amber-500 text-white rounded-lg font-semibold transition"
                          >
                            Adjust to {formatQty(l.available_quantity)}
                          </button>
                          <button
                            onClick={() => handleShortfallAction(l.product_id, 'ACCEPT_FOR_PRODUCTION')}
                            className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-semibold transition"
                          >
                            Mark for Production
                          </button>
                        </div>
                      ))}
                  </div>
                </div>
              )}

              <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
                    Deal Line Items ({deal.line_items?.length || 0})
                  </h2>
                  {canReserve && availability?.overall_status === 'AVAILABLE' && (
                    <button
                      onClick={handleReserveStock}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-emerald-600/20 transition"
                    >
                      Reserve All Available Stock
                    </button>
                  )}
                </div>

                {deal.line_items?.length === 0 ? (
                  <div className="text-center py-8 text-slate-500 text-sm">
                    No line items attached yet. Run AI extraction above to parse inquiry.
                  </div>
                ) : (
                  <div className="divide-y divide-slate-800">
                    {deal.line_items.map((li) => {
                      const check = availability?.lines?.find((i) => i.product_id === li.product_id);
                      return (
                        <div key={li.id} className="py-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                          <div>
                            <div className="font-bold text-white text-base">{li.product_name || 'Product'}</div>
                            <div className="text-xs text-slate-400 font-mono mt-0.5">
                              SKU: {li.product_sku || '—'} • Requested: <strong className="text-white">{formatQty(li.quantity)}</strong> {check?.unit_of_measure || 'PCS'}
                            </div>
                            {li.description && (
                              <p className="text-xs text-slate-400 mt-1 italic">{li.description}</p>
                            )}
                          </div>

                          {check && (
                            <div className="flex flex-wrap items-center gap-3">
                              <span className={`text-xs px-3 py-1 rounded-xl border font-bold ${STATUS_STYLES[check.status]}`}>
                                {check.status.replace(/_/g, ' ')}
                              </span>
                              <div className="text-xs text-slate-400 bg-slate-950/60 px-3 py-1.5 rounded-xl border border-slate-800">
                                Current: <span className="text-white font-semibold">{formatQty(check.current_quantity)}</span> • Avail: <span className="text-emerald-400 font-bold">{formatQty(check.available_quantity)}</span>
                              </div>
                              {check.shortfall > 0 && (
                                <span className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2.5 py-1 rounded-xl font-bold">
                                  -{formatQty(check.shortfall)} Shortfall
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── TAB 2: Costing & Incoterm Quotation ─────────────────────── */}
          {activeTab === 'costing' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div className="lg:col-span-7 bg-slate-900/80 border border-slate-800 rounded-3xl p-6 space-y-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-bold text-white">Cost Breakdown Sheet</h2>
                    <p className="text-xs text-slate-400">Granular factory, packaging, logistics, and compliance costs</p>
                  </div>
                  {canCreate && (
                    <button
                      onClick={() => setIsCostModalOpen(true)}
                      className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/20 transition flex items-center gap-1.5"
                    >
                      <span>+</span> Add Cost Item
                    </button>
                  )}
                </div>

                {costing?.components?.length === 0 ? (
                  <div className="text-center py-10 text-slate-500 text-sm">
                    No cost components added yet. Click "+ Add Cost Item" to build the quotation sheet.
                  </div>
                ) : (
                  <div className="divide-y divide-slate-800">
                    {costing?.components?.map((c) => (
                      <div key={c.id} className="py-3.5 flex items-center justify-between gap-3">
                        <div>
                          <div className="text-xs font-bold text-indigo-300 font-mono">
                            {c.cost_type.replace(/_/g, ' ')}
                          </div>
                          <div className="text-sm font-semibold text-white">{c.description}</div>
                          {c.notes && <p className="text-xs text-slate-500">{c.notes}</p>}
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-sm font-bold text-white">
                            {formatMoney(c.amount, c.currency)}
                          </span>
                          {canCreate && (
                            <button
                              onClick={() => handleDeleteCostComponent(c.id)}
                              className="text-slate-500 hover:text-rose-400 text-xs p-1 transition"
                              title="Delete component"
                            >
                              ✕
                            </button>
                          )}
                        </div>
                      </div>
                    ))}

                    <div className="pt-4 flex items-center justify-between font-bold text-sm text-slate-200">
                      <span>Total Components Base:</span>
                      <span className="font-mono text-emerald-400 text-base">
                        {formatMoney(costing?.total_components_cost, 'USD')}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              <div className="lg:col-span-5 space-y-6">
                <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 space-y-4">
                  <h2 className="text-base font-bold text-white">Incoterm Quotation Engine</h2>
                  <p className="text-xs text-slate-400">
                    Deterministic Incoterms 2020 calculator with target profit margin.
                  </p>

                  <form onSubmit={handleCalculateQuote} className="space-y-3.5 pt-2">
                    <div>
                      <label className="block text-xs font-semibold text-slate-400 mb-1">
                        Incoterm Rule
                      </label>
                      <select
                        value={quoteForm.incoterm}
                        onChange={(e) => setQuoteForm({ ...quoteForm, incoterm: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs font-semibold focus:outline-none focus:border-indigo-500"
                      >
                        {INCOTERMS.map((inc) => (
                          <option key={inc.code} value={inc.code}>
                            {inc.code} — {inc.name}
                          </option>
                        ))}
                      </select>
                      <p className="text-[11px] text-indigo-400 mt-1">
                        Includes: {INCOTERMS.find((i) => i.code === quoteForm.incoterm)?.desc}
                      </p>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-400 mb-1">
                        Named Destination / Place
                      </label>
                      <input
                        type="text"
                        value={quoteForm.incoterm_place}
                        onChange={(e) => setQuoteForm({ ...quoteForm, incoterm_place: e.target.value })}
                        placeholder="e.g. Hamburg, Germany"
                        required
                        className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-400 mb-1">
                        Target Profit Margin (%)
                      </label>
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min="0"
                          max="50"
                          step="0.5"
                          value={quoteForm.margin_percentage}
                          onChange={(e) => setQuoteForm({ ...quoteForm, margin_percentage: e.target.value })}
                          className="w-full accent-indigo-500"
                        />
                        <span className="font-mono text-xs font-bold text-white w-12 text-right">
                          {quoteForm.margin_percentage}%
                        </span>
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={isQuoting}
                      className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-600/20 transition disabled:opacity-50"
                    >
                      {isQuoting ? 'Calculating...' : 'Recalculate Quotation'}
                    </button>
                  </form>

                  {costing?.active_quote && (
                    <div className="mt-5 p-4 bg-slate-950/80 border border-indigo-500/30 rounded-2xl space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-indigo-400 font-mono">
                          {costing.active_quote.incoterm} {costing.active_quote.incoterm_place}
                        </span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                          costing.active_quote.status === 'APPROVED'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        }`}>
                          {costing.active_quote.status}
                        </span>
                      </div>

                      <div className="space-y-1 text-xs border-y border-slate-800/80 py-2">
                        <div className="flex justify-between text-slate-400">
                          <span>Base Cost:</span>
                          <span className="font-mono text-slate-200">{formatMoney(costing.active_quote.base_cost)}</span>
                        </div>
                        <div className="flex justify-between text-slate-400">
                          <span>Logistics/Clearance:</span>
                          <span className="font-mono text-slate-200">{formatMoney(costing.active_quote.logistics_cost)}</span>
                        </div>
                        <div className="flex justify-between text-slate-400">
                          <span>Margin ({costing.active_quote.margin_percentage}%):</span>
                          <span className="font-mono text-emerald-400">+{formatMoney(costing.active_quote.margin_amount)}</span>
                        </div>
                        <div className="flex justify-between text-white font-bold text-sm pt-1 border-t border-slate-800">
                          <span>Total Quoted:</span>
                          <span className="font-mono text-indigo-300">{formatMoney(costing.active_quote.total_quote_price)}</span>
                        </div>
                        <div className="flex justify-between text-slate-400 font-semibold text-xs">
                          <span>Unit Price:</span>
                          <span className="font-mono text-white">{formatMoney(costing.active_quote.unit_price)} / unit</span>
                        </div>
                      </div>

                      {canApproveQuote && costing.active_quote.status === 'DRAFT' && (
                        <button
                          onClick={handleApproveQuote}
                          className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-emerald-600/20 transition flex items-center justify-center gap-1.5"
                        >
                          <span>✓</span> Approve Official Quotation
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── TAB 3: Export Documents & Consistency Audit ───────────── */}
          {activeTab === 'documents' && (
            <div className="space-y-6">
              {/* Consistency Audit Scorecard */}
              {consistency && (
                <div className={`p-6 rounded-3xl border shadow-xl ${
                  consistency.is_consistent
                    ? 'bg-gradient-to-r from-emerald-500/10 via-emerald-500/5 to-transparent border-emerald-500/30'
                    : 'bg-gradient-to-r from-rose-500/10 via-rose-500/5 to-transparent border-rose-500/30'
                }`}>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                      <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-black ${
                        consistency.is_consistent ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                      }`}>
                        {consistency.score}%
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-white flex items-center gap-2">
                          Cross-Document Consistency Audit
                          <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                            consistency.is_consistent ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                          }`}>
                            {consistency.is_consistent ? 'PASSED — 100% Consistent' : 'DISCREPANCIES FOUND'}
                          </span>
                        </h3>
                        <p className="text-xs text-slate-300 mt-0.5">{consistency.summary_message}</p>
                      </div>
                    </div>

                    <button
                      onClick={handleGenerateDocuments}
                      disabled={isGeneratingDocs}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold border border-slate-700 transition"
                    >
                      Re-generate & Audit
                    </button>
                  </div>

                  {/* Audit Checklist Items */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-5 mt-5 border-t border-slate-800/80">
                    {consistency.checks.map((c, i) => (
                      <div key={i} className="p-3 bg-slate-950/70 border border-slate-800 rounded-2xl flex items-start gap-2.5">
                        <span className="text-sm mt-0.5">{c.is_valid ? '✅' : '❌'}</span>
                        <div className="text-xs">
                          <div className="font-bold text-white">{c.check_name}</div>
                          <p className="text-[11px] text-slate-400 mt-0.5">{c.message}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Generated Documents Cards Grid */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-base font-bold text-white">Authoritative Export Documents</h2>
                    <p className="text-xs text-slate-400">
                      Revision #{documentSet?.revision_number || 1} • Single source of truth for Customs, Shipping & Bank Form-E
                    </p>
                  </div>

                  {canManageDocs && (
                    <button
                      onClick={handleGenerateDocuments}
                      disabled={isGeneratingDocs}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-600/20 transition flex items-center gap-1.5 disabled:opacity-50"
                    >
                      <span>⚡</span> {documentSet ? 'Re-generate Document Set' : 'Generate Export Document Set'}
                    </button>
                  )}
                </div>

                {!documentSet || documentSet.documents?.length === 0 ? (
                  <div className="text-center py-12 text-slate-500 text-sm">
                    No documents generated yet. Click "Generate Export Document Set" to produce Proforma Invoice, Commercial Invoice, Packing List, and Certificate of Origin.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {documentSet.documents.map((doc) => (
                      <div
                        key={doc.id}
                        className="p-5 bg-slate-950/70 border border-slate-800 rounded-2xl hover:border-indigo-500/40 transition space-y-3"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs font-bold text-indigo-400">
                            {doc.document_number}
                          </span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                            doc.status === 'APPROVED'
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                              : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                          }`}>
                            {doc.status}
                          </span>
                        </div>

                        <div className="font-bold text-white text-sm">{doc.title}</div>

                        <div className="text-[11px] text-slate-400 font-mono truncate" title={doc.sha256_hash}>
                          SHA-256: {doc.sha256_hash.slice(0, 16)}...{doc.sha256_hash.slice(-8)}
                        </div>

                        <div className="pt-2 flex items-center justify-between gap-2 border-t border-slate-800/80">
                          <button
                            onClick={() => openDocumentPreview(doc)}
                            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold border border-slate-700 transition flex items-center gap-1"
                          >
                            <span>👁️</span> View & Print
                          </button>

                          {canManageDocs && doc.status === 'DRAFT' && (
                            <button
                              onClick={() => handleApproveDocument(doc.id)}
                              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-emerald-600/20 transition flex items-center gap-1"
                            >
                              <span>✓</span> Approve
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── TAB 4: Audit Trail ────────────────────────────────────── */}
          {activeTab === 'audit' && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 space-y-4">
              <h2 className="text-base font-bold text-white">Immutable Audit Trail</h2>
              <p className="text-xs text-slate-400">Chronological history of commercial decisions and state transitions</p>

              {auditLog.length === 0 ? (
                <div className="text-center py-10 text-slate-500 text-sm">No audit records logged yet.</div>
              ) : (
                <div className="space-y-3 pt-2">
                  {auditLog.map((log) => (
                    <div key={log.id} className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                            {log.action}
                          </span>
                          {log.from_state && log.to_state && (
                            <span className="text-xs font-mono text-slate-400">
                              {log.from_state} → <strong className="text-emerald-400">{log.to_state}</strong>
                            </span>
                          )}
                        </div>
                        {log.notes && <p className="text-xs text-slate-300 mt-1">{log.notes}</p>}
                      </div>
                      <div className="text-right text-xs text-slate-400">
                        <div>{log.user_name || 'System'}</div>
                        <div className="text-[11px] text-slate-400">{new Date(log.created_at).toLocaleString()}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        /* ── Deals List View ───────────────────────────────────────── */
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Deals & Inquiries</h1>
              <p className="text-sm text-slate-400 mt-1">
                Authoritative export opportunities with inventory check and Incoterm costing
              </p>
            </div>
            {canCreate && (
              <button
                onClick={openCreate}
                className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl shadow-lg shadow-indigo-600/20 transition flex items-center gap-2"
              >
                <span>+</span> New Deal
              </button>
            )}
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-3xl overflow-hidden shadow-xl">
            {isLoading ? (
              <div className="p-12 text-center text-slate-500">Loading deals...</div>
            ) : deals.length === 0 ? (
              <div className="p-12 text-center text-slate-500">No deals created yet. Click "+ New Deal" to create one.</div>
            ) : (
              <div className="divide-y divide-slate-800">
                {deals.map((d) => (
                  <Link
                    key={d.id}
                    to={`/deals/${d.id}`}
                    className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-800/40 transition block"
                  >
                    <div>
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-xs text-indigo-400 font-bold">{d.reference}</span>
                        <span className="text-base font-bold text-white">{d.buyer_name}</span>
                      </div>
                      <div className="text-xs text-slate-400 mt-1">
                        {d.line_items?.length || 0} line item(s) • Created {new Date(d.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs px-3 py-1 rounded-xl border border-slate-700 bg-slate-800 text-slate-300 font-mono font-semibold">
                        {d.state}
                      </span>
                      <span className="text-slate-500 text-sm">→</span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Modal: Create Deal ──────────────────────────────────────── */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white">Create New Export Deal</h2>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            {modalError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs">
                {modalError}
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Buyer / Importer Name</label>
                <input
                  type="text"
                  value={form.buyer_name}
                  onChange={(e) => setForm({ ...form, buyer_name: e.target.value })}
                  placeholder="e.g. Sportland Germany GmbH"
                  required
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Product</label>
                <select
                  value={form.product_id}
                  onChange={(e) => setForm({ ...form, product_id: e.target.value })}
                  required
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select a product from catalogue...</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} — {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Requested Quantity</label>
                <input
                  type="number"
                  step="1"
                  min="1"
                  value={form.quantity}
                  onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                  placeholder="e.g. 5000"
                  required
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Inquiry Notes / Specs</label>
                <textarea
                  rows="3"
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  placeholder="e.g. Quote CIF Hamburg with delivery by Nov 15"
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/20 transition disabled:opacity-50"
                >
                  {isSubmitting ? 'Creating...' : 'Create Deal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Modal: Add Cost Component ───────────────────────────────── */}
      {isCostModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white">Add Cost Component</h2>
              <button onClick={() => setIsCostModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <form onSubmit={handleAddCostComponent} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Cost Type</label>
                <select
                  value={costForm.cost_type}
                  onChange={(e) => setCostForm({ ...costForm, cost_type: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                >
                  {COST_TYPES.map((ct) => (
                    <option key={ct.value} value={ct.value}>
                      {ct.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Description</label>
                <input
                  type="text"
                  value={costForm.description}
                  onChange={(e) => setCostForm({ ...costForm, description: e.target.value })}
                  placeholder="e.g. Karachi Port Qasim Trucking"
                  required
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Amount</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={costForm.amount}
                    onChange={(e) => setCostForm({ ...costForm, amount: e.target.value })}
                    placeholder="1200.00"
                    required
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Currency</label>
                  <input
                    type="text"
                    value={costForm.currency}
                    onChange={(e) => setCostForm({ ...costForm, currency: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCostModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/20 transition"
                >
                  Add Component
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Modal: Transition State ────────────────────────────────── */}
      {isTransitionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white">Transition Deal Lifecycle</h2>
              <button onClick={() => setIsTransitionModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="text-xs text-slate-400">
              Current state: <strong className="text-indigo-400 font-mono">{deal?.state}</strong>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Target State</label>
                <select
                  value={transitionTarget}
                  onChange={(e) => setTransitionTarget(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select target state...</option>
                  {DEAL_STATES.filter((s) => s.key !== deal?.state).map((s) => (
                    <option key={s.key} value={s.key}>
                      {s.key} ({s.label})
                    </option>
                  ))}
                  <option value="CANCELLED">CANCELLED (Dead Deal)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Reason / Notes</label>
                <textarea
                  rows="2"
                  value={transitionReason}
                  onChange={(e) => setTransitionReason(e.target.value)}
                  placeholder="e.g. Buyer signed proforma invoice, starting production"
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsTransitionModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  onClick={handleTransitionState}
                  disabled={!transitionTarget}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/20 transition disabled:opacity-50"
                >
                  Confirm Transition
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Modal: Document Printable Preview ───────────────────────── */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-4xl w-full h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950">
              <div>
                <h3 className="text-sm font-bold text-white">{previewDoc.title}</h3>
                <p className="text-xs text-slate-400 font-mono">
                  {previewDoc.document_number} • SHA-256: {previewDoc.sha256_hash.slice(0, 16)}...
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    const printWin = window.open('', '_blank');
                    printWin.document.write(previewHtml);
                    printWin.document.close();
                    printWin.print();
                  }}
                  className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition flex items-center gap-1.5"
                >
                  <span>🖨️</span> Print / Save PDF
                </button>
                <button
                  onClick={() => setPreviewDoc(null)}
                  className="p-2 text-slate-400 hover:text-white rounded-lg"
                >
                  ✕
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-auto p-4 bg-slate-900">
              {isPreviewLoading ? (
                <div className="h-full flex items-center justify-center text-slate-400 text-sm">
                  Loading document view...
                </div>
              ) : (
                <iframe
                  title="Document Preview"
                  srcDoc={previewHtml}
                  className="w-full h-full rounded-2xl bg-white border-0 shadow-lg"
                />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
