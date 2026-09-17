import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';

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

export default function Deals() {
  const { dealId } = useParams();
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();
  const canCreate = isAdmin || ['EXPORT_MANAGER', 'SALES'].includes(user?.role);
  const canReserve = isAdmin || ['EXPORT_MANAGER', 'ACCOUNTS'].includes(user?.role);

  const [deals, setDeals] = useState([]);
  const [deal, setDeal] = useState(null);
  const [availability, setAvailability] = useState(null);
  const [products, setProducts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
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
      const [d, avail] = await Promise.all([
        api.get(`/deals/${id}`),
        api.get(`/deals/${id}/availability`),
      ]);
      setDeal(d);
      setAvailability(avail);
      setError('');

      // Try loading existing extraction
      try {
        const ext = await api.get(`/deals/${id}/extraction`);
        setExtraction(ext);
        initEditableFields(ext.extracted_data);
      } catch {
        setExtraction(null);
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
      setExtractionSuccess('AI extraction completed with Qwen model.');
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
      setExtractionSuccess('Extracted terms confirmed and applied to deal line items!');
      // Reload deal to reflect updated line items & availability
      loadDeal(deal.id);
    } catch (err) {
      setExtractionError(err.message || 'Failed to confirm extraction');
    } finally {
      setIsExtracting(false);
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
        line_items: form.product_id ? [
          {
            product_id: form.product_id,
            quantity: Number(form.quantity),
          },
        ] : [],
      });
      setIsModalOpen(false);
      navigate(`/deals/${created.id}`);
    } catch (err) {
      setModalError(err.message || 'Failed to create deal');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReserve = async (productId, quantity) => {
    try {
      await api.post(`/inventory/${productId}/reserve`, {
        deal_id: deal.id,
        quantity: Number(quantity),
      });
      await loadDeal(deal.id);
    } catch (err) {
      setError(err.message || 'Reservation failed');
    }
  };

  const handleRelease = async (reservationId) => {
    try {
      await api.post(`/inventory/reservations/${reservationId}/release`);
      await loadDeal(deal.id);
    } catch (err) {
      setError(err.message || 'Release failed');
    }
  };

  return (
    <div className="space-y-6">
      {/* Detail View */}
      {dealId && deal ? (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <Link to="/deals" className="text-slate-400 hover:text-white text-sm">
                  ← Back to Deals
                </Link>
                <span className="text-slate-600">/</span>
                <span className="font-mono text-xs text-indigo-400 font-semibold">{deal.reference}</span>
              </div>
              <h1 className="text-2xl font-bold text-white tracking-tight mt-1">
                {deal.buyer_name}
              </h1>
              <p className="text-xs text-slate-400">
                Created {new Date(deal.created_at).toLocaleString()} by {deal.creator?.full_name || 'System'}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="px-3 py-1.5 rounded-xl border border-slate-700 bg-slate-800 text-xs font-mono font-medium text-slate-200">
                State: {deal.state}
              </span>
              <button
                onClick={runAIExtraction}
                disabled={isExtracting}
                className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-emerald-600 hover:from-indigo-500 hover:to-emerald-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/20 transition flex items-center gap-2 disabled:opacity-50"
              >
                {isExtracting ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                    <span>Extracting...</span>
                  </>
                ) : (
                  <>
                    <span>🤖</span> Run AI Extraction (Qwen)
                  </>
                )}
              </button>
            </div>
          </div>

          {deal.notes && (
            <div className="p-4 bg-slate-900/60 border border-slate-800/80 rounded-2xl">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Inquiry / Order Notes
              </div>
              <p className="text-sm text-slate-200 whitespace-pre-wrap">{deal.notes}</p>
            </div>
          )}

          {/* AI Extraction Panel */}
          {extraction && (
            <div className="bg-slate-900/80 border border-indigo-500/30 rounded-2xl p-6 shadow-2xl space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 text-sm">
                    🤖
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-white">AI Extraction Review & Evidence</h2>
                    <p className="text-[11px] text-slate-400 font-mono">
                      Model: {extraction.model_name} • Status: <span className="text-indigo-300 font-semibold">{extraction.status}</span>
                    </p>
                  </div>
                </div>
                <button
                  onClick={confirmExtraction}
                  disabled={isExtracting}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-emerald-600/20 transition disabled:opacity-50 flex items-center gap-1.5"
                >
                  <span>✓</span> Confirm & Apply to Deal
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

              {/* Extraction Fields Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5 pt-1">
                {Object.entries(extraction.extracted_data || {}).map(([key, item]) => {
                  const conf = item?.confidence || 0;
                  const percent = Math.round(conf * 100);

                  return (
                    <div key={key} className="p-3.5 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-300 capitalize">
                          {key.replace(/_/g, ' ')}
                        </span>
                        {item?.value !== null && item?.value !== undefined && (
                          <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${CONFIDENCE_BADGES(conf)}`}>
                            {percent}% match
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
                          <span className="text-slate-400 not-italic font-semibold block text-[10px]">Evidence quote:</span>
                          "{item.evidence}"
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Line Items & Real-time Inventory */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 space-y-4">
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
              Deal Line Items & Stock Availability
            </h2>

            {deal.line_items?.length === 0 ? (
              <p className="text-sm text-slate-500">No line items attached yet. Run AI extraction above or add manually.</p>
            ) : (
              <div className="divide-y divide-slate-800/60">
                {deal.line_items.map((li) => {
                  const check = availability?.items?.find((i) => i.product_id === li.product_id);
                  const isAvailable = check?.status === 'AVAILABLE';
                  const isPartial = check?.status === 'PARTIALLY_AVAILABLE';

                  return (
                    <div key={li.id} className="py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div>
                        <div className="font-semibold text-white text-base">{li.product?.name}</div>
                        <div className="text-xs text-slate-400 font-mono">
                          SKU: {li.product?.sku} • Requested: {formatQty(li.quantity)} {li.product?.unit_of_measure}
                        </div>
                      </div>

                      {check && (
                        <div className="flex flex-wrap items-center gap-3">
                          <span className={`text-xs px-3 py-1 rounded-lg border font-medium ${STATUS_STYLES[check.status]}`}>
                            {check.status.replace(/_/g, ' ')}
                          </span>
                          <span className="text-xs text-slate-400">
                            Current: <strong className="text-white">{formatQty(check.current_stock)}</strong>
                          </span>
                          <span className="text-xs text-slate-400">
                            Available: <strong className="text-emerald-400">{formatQty(check.available_stock)}</strong>
                          </span>
                          {check.shortfall > 0 && (
                            <span className="text-xs text-rose-400 font-semibold">
                              Shortfall: {formatQty(check.shortfall)}
                            </span>
                          )}
                          {canReserve && (isAvailable || isPartial) && (
                            <button
                              onClick={() => handleReserve(li.product_id, check.available_stock)}
                              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition"
                            >
                              Reserve {formatQty(check.available_stock)}
                            </button>
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
      ) : (
        /* Deals List Board */
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Deals Board</h1>
              <p className="text-sm text-slate-400 mt-1">
                Commercial pipeline with automated inventory checking and AI interpretation
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

          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden shadow-xl">
            {isLoading ? (
              <div className="p-12 text-center text-slate-500">Loading deals...</div>
            ) : deals.length === 0 ? (
              <div className="p-12 text-center text-slate-500">No deals created yet.</div>
            ) : (
              <div className="divide-y divide-slate-800/60">
                {deals.map((d) => (
                  <Link
                    key={d.id}
                    to={`/deals/${d.id}`}
                    className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-800/30 transition block"
                  >
                    <div>
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-xs text-indigo-400 font-semibold">{d.reference}</span>
                        <span className="text-base font-bold text-white">{d.buyer_name}</span>
                      </div>
                      <div className="text-xs text-slate-400 mt-1">
                        {d.line_items?.length || 0} line item(s) • Created {new Date(d.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs px-3 py-1 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 font-mono">
                        {d.state}
                      </span>
                      <span className="text-slate-400 text-sm">→</span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
