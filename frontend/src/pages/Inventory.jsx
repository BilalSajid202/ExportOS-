import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';

const STATUS_STYLES = {
  AVAILABLE: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  PARTIALLY_AVAILABLE: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  UNAVAILABLE: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
};

const DEAL_STATE_STYLES = {
  CONFIRMED: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  IN_PRODUCTION: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  DOCS_READY: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  SHIPPED: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
  PAID: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  CLOSED: 'bg-slate-700 text-slate-300 border-slate-600',
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

export default function Inventory() {
  const { productId } = useParams();
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();
  const canAdjust = isAdmin || ['EXPORT_MANAGER', 'ACCOUNTS'].includes(user?.role);

  const [activeTab, setActiveTab] = useState('inventory'); // 'inventory', 'dispatch_history', 'low_stock'
  const [items, setItems] = useState([]);
  const [products, setProducts] = useState([]);
  const [dispatchHistory, setDispatchHistory] = useState([]);
  const [detail, setDetail] = useState(null);
  const [availability, setAvailability] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  // Modals
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [adjustOpen, setAdjustOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);

  // Forms
  const [addForm, setAddForm] = useState({
    product_id: '',
    initial_quantity: '0',
    reorder_level: '100',
    notes: 'Initial warehouse stock load',
  });

  const [adjustForm, setAdjustForm] = useState({
    product_id: '',
    quantity_delta: '',
    notes: '',
    reorder_level: '',
  });

  const [editForm, setEditForm] = useState({
    reorder_level: '',
    unit_of_measure: '',
  });

  const [checkQty, setCheckQty] = useState('50');
  const [reserveQty, setReserveQty] = useState('');
  const [modalError, setModalError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadDashboard = async () => {
    setIsLoading(true);
    try {
      const [inv, prods, dispatch] = await Promise.all([
        api.get('/inventory'),
        api.get('/products'),
        api.get('/inventory/dispatch-history'),
      ]);
      setItems(inv);
      setProducts(prods);
      setDispatchHistory(dispatch);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load inventory');
    } finally {
      setIsLoading(false);
    }
  };

  const loadProductDetail = async (id) => {
    setIsLoading(true);
    try {
      const [inv, avail, txs] = await Promise.all([
        api.get(`/inventory/${id}`),
        api.get(`/inventory/${id}/availability?requested_quantity=${checkQty || 1}`),
        api.get(`/inventory/${id}/transactions`),
      ]);
      setDetail(inv);
      setAvailability(avail);
      setTransactions(txs);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load product inventory');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (productId) {
      loadProductDetail(productId);
    } else {
      loadDashboard();
    }
  }, [productId]);

  // Handle Add to Inventory
  const handleAddInventory = async (e) => {
    e.preventDefault();
    setModalError('');
    setIsSubmitting(true);
    try {
      await api.post('/inventory', {
        product_id: addForm.product_id,
        initial_quantity: Number(addForm.initial_quantity),
        reorder_level: Number(addForm.reorder_level),
        notes: addForm.notes || null,
      });
      setAddModalOpen(false);
      setActionSuccess('Inventory initialized successfully!');
      loadDashboard();
    } catch (err) {
      setModalError(err.message || 'Failed to add inventory');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Adjust Stock (+ / -)
  const handleAdjust = async (e) => {
    e.preventDefault();
    setModalError('');
    setIsSubmitting(true);
    try {
      await api.post('/inventory/adjust', {
        product_id: adjustForm.product_id || productId,
        quantity_delta: Number(adjustForm.quantity_delta),
        notes: adjustForm.notes || null,
        reorder_level:
          adjustForm.reorder_level === '' ? null : Number(adjustForm.reorder_level),
      });
      setAdjustOpen(false);
      setAdjustForm({ product_id: '', quantity_delta: '', notes: '', reorder_level: '' });
      setActionSuccess('Inventory stock adjusted successfully!');
      if (productId) loadProductDetail(productId);
      else loadDashboard();
    } catch (err) {
      setModalError(err.message || 'Adjustment failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Edit Inventory Settings
  const handleEditInventory = async (e) => {
    e.preventDefault();
    setModalError('');
    setIsSubmitting(true);
    try {
      await api.put(`/inventory/${selectedItem.product_id}`, {
        reorder_level: Number(editForm.reorder_level),
        unit_of_measure: editForm.unit_of_measure || null,
      });
      setEditModalOpen(false);
      setActionSuccess('Inventory settings updated!');
      if (productId) loadProductDetail(productId);
      else loadDashboard();
    } catch (err) {
      setModalError(err.message || 'Update failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Delete Inventory Item
  const handleDeleteInventory = async (item) => {
    if (!window.confirm(`Are you sure you want to remove inventory tracking for SKU: ${item.sku}?`)) {
      return;
    }
    try {
      await api.delete(`/inventory/${item.product_id}`);
      setActionSuccess(`Removed inventory tracking for ${item.sku}.`);
      loadDashboard();
    } catch (err) {
      setError(err.message || 'Failed to delete inventory');
    }
  };

  const runAvailabilityCheck = async () => {
    if (!productId) return;
    try {
      const data = await api.get(
        `/inventory/${productId}/availability?requested_quantity=${checkQty}`
      );
      setAvailability(data);
    } catch (err) {
      setError(err.message || 'Availability check failed');
    }
  };

  const handleReserve = async () => {
    if (!productId || !reserveQty) return;
    try {
      await api.post(`/inventory/${productId}/reserve`, {
        quantity: Number(reserveQty),
      });
      setReserveQty('');
      setActionSuccess('Stock reserved successfully!');
      loadProductDetail(productId);
    } catch (err) {
      setError(err.message || 'Reservation failed');
    }
  };

  const uncataloguedProducts = products.filter(
    (p) => !items.some((i) => i.product_id === p.id)
  );

  return (
    <div className="space-y-6">
      {productId ? (
        <div className="space-y-6 max-w-4xl">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/inventory')}
              className="text-slate-400 hover:text-white text-sm"
            >
              ← Back to Inventory
            </button>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">
                {detail?.product_name || 'Product Inventory'}
              </h1>
              <p className="text-sm text-slate-400 mt-1 font-mono">{detail?.sku}</p>
            </div>
            {canAdjust && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setSelectedItem(detail);
                    setEditForm({
                      reorder_level: String(detail?.reorder_level ?? 0),
                      unit_of_measure: detail?.unit_of_measure ?? 'PCS',
                    });
                    setModalError('');
                    setEditModalOpen(true);
                  }}
                  className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold rounded-xl transition"
                >
                  ✏️ Edit Thresholds
                </button>
                <button
                  onClick={() => {
                    setAdjustForm({
                      product_id: productId,
                      quantity_delta: '',
                      notes: '',
                      reorder_level: detail?.reorder_level ?? '',
                    });
                    setModalError('');
                    setAdjustOpen(true);
                  }}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-indigo-600/20 transition"
                >
                  ± Adjust Stock
                </button>
              </div>
            )}
          </div>

          {error && (
            <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-sm">
              {error}
            </div>
          )}
          {actionSuccess && (
            <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400 text-sm">
              {actionSuccess}
            </div>
          )}

          {/* Stock Numbers Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl">
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Current Stock</div>
              <div className="text-3xl font-bold text-white font-mono mt-1">
                {formatQty(detail?.current_quantity)}
              </div>
              <div className="text-xs text-slate-500 mt-1">{detail?.unit_of_measure}</div>
            </div>
            <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl">
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Reserved Stock</div>
              <div className="text-3xl font-bold text-amber-400 font-mono mt-1">
                {formatQty(detail?.reserved_quantity)}
              </div>
              <div className="text-xs text-slate-500 mt-1">Committed to active deals</div>
            </div>
            <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl">
              <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Available Stock</div>
              <div className="text-3xl font-bold text-emerald-400 font-mono mt-1">
                {formatQty(detail?.available_quantity)}
              </div>
              <div className="text-xs text-slate-500 mt-1">Current - Reserved</div>
            </div>
          </div>

          {/* Availability Calculator */}
          <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
            <h2 className="text-base font-bold text-white">Live Stock Availability Calculator</h2>
            <div className="flex gap-3">
              <input
                type="number"
                value={checkQty}
                onChange={(e) => setCheckQty(e.target.value)}
                placeholder="Requested qty"
                className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs w-48 focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={runAvailabilityCheck}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition"
              >
                Check Availability
              </button>
            </div>
            {availability && (
              <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2">
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${STATUS_STYLES[availability.status]}`}>
                    {availability.status.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs text-slate-300 font-medium">{availability.message}</span>
                </div>
                {availability.shortfall > 0 && (
                  <div className="text-xs text-rose-400 font-semibold">
                    ⚠️ Shortfall: {formatQty(availability.shortfall)} {availability.unit_of_measure} needed.
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Transactions Ledger */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 space-y-4">
            <h2 className="text-base font-bold text-white">Stock Movement Ledger</h2>
            {transactions.length === 0 ? (
              <div className="text-center py-6 text-slate-500 text-xs">No transactions recorded yet.</div>
            ) : (
              <div className="divide-y divide-slate-800">
                {transactions.map((t) => (
                  <div key={t.id} className="py-3 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-bold text-indigo-400 font-mono mr-2">
                        {t.transaction_type}
                      </span>
                      <span className="text-slate-300">{t.notes || 'Stock adjustment'}</span>
                    </div>
                    <div className="text-right">
                      <div className="font-mono font-bold text-white">
                        {t.quantity > 0 ? `+${formatQty(t.quantity)}` : formatQty(t.quantity)} {t.sku}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        {new Date(t.created_at).toLocaleString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <>
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Warehouse & Inventory</h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time deterministic stock tracking and buyer dispatch history
          </p>
        </div>

        {canAdjust && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setAdjustForm({ product_id: items[0]?.product_id || '', quantity_delta: '', notes: '', reorder_level: '' });
                setModalError('');
                setAdjustOpen(true);
              }}
              className="px-3.5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold rounded-xl transition"
            >
              ± Quick Stock Adjust
            </button>
            <button
              onClick={() => {
                setAddForm({ product_id: uncataloguedProducts[0]?.id || '', initial_quantity: '0', reorder_level: '100', notes: '' });
                setModalError('');
                setAddModalOpen(true);
              }}
              className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-indigo-600/20 transition flex items-center gap-1.5"
            >
              <span>+</span> Add to Inventory
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400 text-xs">
          {error}
        </div>
      )}
      {actionSuccess && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl text-emerald-400 text-xs">
          {actionSuccess}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-6 text-sm font-semibold">
        <button
          onClick={() => setActiveTab('inventory')}
          className={`pb-3 px-1 transition relative ${
            activeTab === 'inventory' ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          📦 Warehouse Inventory ({items.length})
        </button>
        <button
          onClick={() => setActiveTab('dispatch_history')}
          className={`pb-3 px-1 transition relative ${
            activeTab === 'dispatch_history' ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          🚚 Dispatch & Deal History ("Who Received What") ({dispatchHistory.length})
        </button>
        <button
          onClick={() => setActiveTab('low_stock')}
          className={`pb-3 px-1 transition relative ${
            activeTab === 'low_stock' ? 'text-indigo-400 border-b-2 border-indigo-500' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          ⚠️ Low Stock Alerts ({items.filter((i) => i.is_low_stock).length})
        </button>
      </div>

      {/* ── TAB 1: Warehouse Inventory List ─────────────────────────── */}
      {activeTab === 'inventory' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-3xl overflow-hidden shadow-xl">
          {isLoading ? (
            <div className="p-12 text-center text-slate-500">Loading inventory items...</div>
          ) : items.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-sm">
              No inventory tracked yet. Click "+ Add to Inventory" to initialize stock.
            </div>
          ) : (
            <div className="divide-y divide-slate-800">
              {items.map((item) => (
                <div
                  key={item.id}
                  className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-800/30 transition"
                >
                  <div>
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs text-indigo-400 font-bold">{item.sku}</span>
                      <span className="text-base font-bold text-white">{item.product_name || 'Product'}</span>
                      {item.is_low_stock && (
                        <span className="text-[10px] px-2 py-0.5 rounded font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          Low Stock
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      Reorder Threshold: {formatQty(item.reorder_level)} {item.unit_of_measure}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <div className="text-xs bg-slate-950/60 px-3 py-1.5 rounded-xl border border-slate-800">
                      Stock: <strong className="text-white">{formatQty(item.current_quantity)}</strong> • Reserved:{' '}
                      <strong className="text-amber-400">{formatQty(item.reserved_quantity)}</strong> • Available:{' '}
                      <strong className="text-emerald-400">{formatQty(item.available_quantity)}</strong> {item.unit_of_measure}
                    </div>

                    <Link
                      to={`/inventory/${item.product_id}`}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold border border-slate-700 transition"
                    >
                      Ledger & Detail →
                    </Link>

                    {canAdjust && (
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => {
                            setAdjustForm({
                              product_id: item.product_id,
                              quantity_delta: '',
                              notes: '',
                              reorder_level: item.reorder_level,
                            });
                            setModalError('');
                            setAdjustOpen(true);
                          }}
                          className="px-2.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition"
                          title="Add / Remove Stock"
                        >
                          ± Adjust
                        </button>
                        <button
                          onClick={() => {
                            setSelectedItem(item);
                            setEditForm({
                              reorder_level: String(item.reorder_level),
                              unit_of_measure: item.unit_of_measure,
                            });
                            setModalError('');
                            setEditModalOpen(true);
                          }}
                          className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold border border-slate-700 transition"
                          title="Edit settings"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={() => handleDeleteInventory(item)}
                          className="px-2.5 py-1.5 bg-slate-800 hover:bg-rose-600 text-slate-400 hover:text-white rounded-xl text-xs font-semibold border border-slate-700 transition"
                          title="Remove item"
                        >
                          🗑️
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── TAB 2: Dispatch & Deal History ("Who Received What") ─────── */}
      {activeTab === 'dispatch_history' && (
        <div className="space-y-4">
          <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-2xl text-xs text-slate-400">
            Authoritative history of all confirmed and fulfilled export shipments showing exact buyers, items dispatched, quantities, and trade terms.
          </div>

          {dispatchHistory.length === 0 ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-12 text-center text-slate-500 text-sm">
              No completed or confirmed deal shipments found.
            </div>
          ) : (
            <div className="space-y-4">
              {dispatchHistory.map((d) => (
                <div
                  key={d.deal_id}
                  className="p-6 bg-slate-900/80 border border-slate-800 rounded-3xl space-y-4 shadow-xl hover:border-indigo-500/30 transition"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-indigo-400 font-bold">{d.reference}</span>
                        <span className="text-slate-600">•</span>
                        <span className="text-xs text-slate-400">
                          {new Date(d.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <h3 className="text-lg font-extrabold text-white mt-0.5">
                        Consignee: <span className="text-indigo-300">{d.buyer_name}</span>
                      </h3>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className={`text-xs px-3 py-1 rounded-xl font-bold border ${DEAL_STATE_STYLES[d.state] || 'bg-slate-800 text-slate-300'}`}>
                        {d.state}
                      </span>
                      {d.total_amount && (
                        <span className="font-mono font-bold text-sm text-emerald-400">
                          {formatMoney(d.total_amount, d.currency)}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Dispatched Products List */}
                  <div className="space-y-2">
                    <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      Dispatched Products & Materials
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {d.items_sent.map((item, idx) => (
                        <div key={idx} className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl flex items-center justify-between text-xs">
                          <div>
                            <div className="font-bold text-white">{item.product_name}</div>
                            <div className="text-[11px] text-slate-400 font-mono">SKU: {item.sku}</div>
                          </div>
                          <div className="text-right font-mono font-bold text-indigo-300">
                            {formatQty(item.quantity)} {item.unit_of_measure}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {d.incoterm && (
                    <div className="pt-2 flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/60">
                      <div>
                        Incoterm & Destination: <strong className="text-slate-200">{d.incoterm} {d.incoterm_place}</strong>
                      </div>
                      <Link to={`/deals/${d.deal_id}`} className="text-indigo-400 hover:text-white font-semibold">
                        View Complete Deal →
                      </Link>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── TAB 3: Low Stock Alerts ─────────────────────────────────── */}
      {activeTab === 'low_stock' && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-3xl overflow-hidden shadow-xl">
          {items.filter((i) => i.is_low_stock).length === 0 ? (
            <div className="p-12 text-center text-emerald-400 text-sm">
              ✓ All products are above their reorder thresholds. No stock warnings!
            </div>
          ) : (
            <div className="divide-y divide-slate-800">
              {items
                .filter((i) => i.is_low_stock)
                .map((item) => (
                  <div key={item.id} className="p-5 flex items-center justify-between gap-4">
                    <div>
                      <div className="font-bold text-white text-base">{item.product_name}</div>
                      <div className="text-xs text-rose-400 font-mono mt-0.5">
                        SKU: {item.sku} • Available: {formatQty(item.available_quantity)} {item.unit_of_measure} (Reorder at: {formatQty(item.reorder_level)})
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        setAdjustForm({ product_id: item.product_id, quantity_delta: '', notes: 'Reorder batch receipt', reorder_level: item.reorder_level });
                        setModalError('');
                        setAdjustOpen(true);
                      }}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition"
                    >
                      + Stock In Receipt
                    </button>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}
    </>
  )}

      {/* ── Modal: Add to Inventory ─────────────────────────────────── */}
      {addModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white">Add Product to Inventory</h2>
              <button onClick={() => setAddModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            {modalError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs">
                {modalError}
              </div>
            )}

            <form onSubmit={handleAddInventory} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Select Product</label>
                <select
                  value={addForm.product_id}
                  onChange={(e) => setAddForm({ ...addForm, product_id: e.target.value })}
                  required
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select catalogue product...</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} — {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Initial Stock</label>
                  <input
                    type="number"
                    min="0"
                    value={addForm.initial_quantity}
                    onChange={(e) => setAddForm({ ...addForm, initial_quantity: e.target.value })}
                    required
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Reorder Level</label>
                  <input
                    type="number"
                    min="0"
                    value={addForm.reorder_level}
                    onChange={(e) => setAddForm({ ...addForm, reorder_level: e.target.value })}
                    required
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Notes / Ledger Reference</label>
                <textarea
                  rows="2"
                  value={addForm.notes}
                  onChange={(e) => setAddForm({ ...addForm, notes: e.target.value })}
                  placeholder="e.g. Initial warehouse baseline inventory"
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setAddModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-600/20 transition disabled:opacity-50"
                >
                  {isSubmitting ? 'Saving...' : 'Add to Inventory'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Modal: Adjust Stock (+ / -) ─────────────────────────────── */}
      {adjustOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white">Adjust Stock (In / Out)</h2>
              <button onClick={() => setAdjustOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            {modalError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs">
                {modalError}
              </div>
            )}

            <form onSubmit={handleAdjust} className="space-y-4">
              {!productId && (
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1">Target Product</label>
                  <select
                    value={adjustForm.product_id}
                    onChange={(e) => setAdjustForm({ ...adjustForm, product_id: e.target.value })}
                    required
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                  >
                    <option value="">Select product...</option>
                    {items.map((i) => (
                      <option key={i.product_id} value={i.product_id}>
                        {i.sku} — {i.product_name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">
                  Quantity Change (+ to Add, - to Deduct)
                </label>
                <input
                  type="number"
                  step="1"
                  value={adjustForm.quantity_delta}
                  onChange={(e) => setAdjustForm({ ...adjustForm, quantity_delta: e.target.value })}
                  placeholder="e.g. +500 for receipt, -50 for write-down"
                  required
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs font-mono focus:outline-none focus:border-indigo-500"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Enter positive number (e.g. 500) to add stock or negative (-50) to remove.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Reason / Notes</label>
                <input
                  type="text"
                  value={adjustForm.notes}
                  onChange={(e) => setAdjustForm({ ...adjustForm, notes: e.target.value })}
                  placeholder="e.g. Production batch #402 arrived from Sialkot factory"
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setAdjustOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-600/20 transition disabled:opacity-50"
                >
                  {isSubmitting ? 'Adjusting...' : 'Save Stock Adjustment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Modal: Edit Inventory Thresholds ────────────────────────── */}
      {editModalOpen && selectedItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white">Edit Inventory Settings</h2>
              <button onClick={() => setEditModalOpen(false)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="text-xs text-slate-400">
              SKU: <strong className="text-indigo-400 font-mono">{selectedItem.sku}</strong> — {selectedItem.product_name}
            </div>

            {modalError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs">
                {modalError}
              </div>
            )}

            <form onSubmit={handleEditInventory} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Reorder Level Threshold</label>
                <input
                  type="number"
                  min="0"
                  value={editForm.reorder_level}
                  onChange={(e) => setEditForm({ ...editForm, reorder_level: e.target.value })}
                  required
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Unit of Measure</label>
                <input
                  type="text"
                  value={editForm.unit_of_measure}
                  onChange={(e) => setEditForm({ ...editForm, unit_of_measure: e.target.value })}
                  placeholder="e.g. PCS, PAIRS, SETS"
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setEditModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-600/20 transition disabled:opacity-50"
                >
                  {isSubmitting ? 'Updating...' : 'Update Settings'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
