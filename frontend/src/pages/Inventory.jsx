import { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';

const STATUS_STYLES = {
  AVAILABLE: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  PARTIALLY_AVAILABLE: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  UNAVAILABLE: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
};

function formatQty(value) {
  if (value == null) return '—';
  const n = Number(value);
  return Number.isInteger(n) ? String(n) : n.toLocaleString();
}

export default function Inventory() {
  const { productId } = useParams();
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();
  const canAdjust = isAdmin || ['EXPORT_MANAGER', 'ACCOUNTS'].includes(user?.role);

  const [items, setItems] = useState([]);
  const [products, setProducts] = useState([]);
  const [detail, setDetail] = useState(null);
  const [availability, setAvailability] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const [adjustOpen, setAdjustOpen] = useState(false);
  const [adjustForm, setAdjustForm] = useState({
    product_id: '',
    quantity_delta: '',
    notes: '',
    reorder_level: '',
  });
  const [checkQty, setCheckQty] = useState('50');
  const [reserveQty, setReserveQty] = useState('');
  const [modalError, setModalError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadDashboard = async () => {
    setIsLoading(true);
    try {
      const [inv, prods] = await Promise.all([
        api.get('/inventory'),
        api.get('/products'),
      ]);
      setItems(inv);
      setProducts(prods);
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
      if (productId) loadProductDetail(productId);
      else loadDashboard();
    } catch (err) {
      setModalError(err.message || 'Adjustment failed');
    } finally {
      setIsSubmitting(false);
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
      loadProductDetail(productId);
    } catch (err) {
      setError(err.message || 'Reservation failed');
    }
  };

  // ── Product detail view ────────────────────────────────────
  if (productId) {
    return (
      <div className="space-y-6 max-w-4xl">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/inventory')}
            className="text-slate-400 hover:text-white text-sm"
          >
            ← Inventory
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
              className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl shadow-lg shadow-indigo-600/20 transition"
            >
              Adjust Stock
            </button>
          )}
        </div>

        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-sm">
            {error}
          </div>
        )}

        {isLoading || !detail ? (
          <div className="p-12 text-center text-slate-500">Loading...</div>
        ) : (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: 'Current', value: detail.current_quantity },
                { label: 'Reserved', value: detail.reserved_quantity },
                { label: 'Available', value: detail.available_quantity },
                { label: 'Reorder Level', value: detail.reorder_level },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4"
                >
                  <div className="text-xs text-slate-400 uppercase tracking-wider">{stat.label}</div>
                  <div className="text-2xl font-bold text-white mt-1">
                    {formatQty(stat.value)}
                    <span className="text-xs text-slate-500 ml-1 font-normal">
                      {detail.unit_of_measure}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {detail.is_low_stock && (
              <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-400 text-sm">
                Low stock — available quantity is at or below reorder level.
              </div>
            )}

            {/* Availability checker */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 space-y-4">
              <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
                Availability Check
              </h2>
              <div className="flex flex-wrap gap-3 items-end">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Requested quantity</label>
                  <input
                    type="number"
                    min="1"
                    value={checkQty}
                    onChange={(e) => setCheckQty(e.target.value)}
                    className="w-40 px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <button
                  onClick={runAvailabilityCheck}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-sm font-medium"
                >
                  Check
                </button>
              </div>

              {availability && (
                <div className="space-y-3">
                  <span
                    className={`inline-block text-xs font-semibold px-3 py-1 rounded-lg border ${
                      STATUS_STYLES[availability.status] || ''
                    }`}
                  >
                    {availability.status}
                  </span>
                  <p className="text-sm text-slate-300">{availability.message}</p>
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
                    <div>
                      <div className="text-slate-500">Requested</div>
                      <div className="text-white font-semibold">
                        {formatQty(availability.requested_quantity)}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500">Current</div>
                      <div className="text-white font-semibold">
                        {formatQty(availability.current_quantity)}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500">Reserved</div>
                      <div className="text-white font-semibold">
                        {formatQty(availability.reserved_quantity)}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500">Available</div>
                      <div className="text-white font-semibold">
                        {formatQty(availability.available_quantity)}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500">Shortfall</div>
                      <div className="text-white font-semibold">
                        {formatQty(availability.shortfall)}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {canAdjust && (
                <div className="flex flex-wrap gap-3 items-end pt-2 border-t border-slate-800">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Reserve quantity</label>
                    <input
                      type="number"
                      min="1"
                      value={reserveQty}
                      onChange={(e) => setReserveQty(e.target.value)}
                      className="w-40 px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <button
                    onClick={handleReserve}
                    disabled={!reserveQty}
                    className="px-4 py-2 bg-emerald-600/80 hover:bg-emerald-500 text-white rounded-xl text-sm font-medium disabled:opacity-50"
                  >
                    Reserve Stock
                  </button>
                </div>
              )}
            </div>

            {/* Transactions */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-800/80">
                <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
                  Transactions
                </h2>
              </div>
              {transactions.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-sm">No movements yet</div>
              ) : (
                <div className="divide-y divide-slate-800/60">
                  {transactions.map((tx) => (
                    <div
                      key={tx.id}
                      className="px-6 py-3 flex items-center justify-between text-sm"
                    >
                      <div>
                        <span className="font-mono text-xs text-indigo-300">{tx.transaction_type}</span>
                        <span className="text-slate-400 ml-3 text-xs">
                          {new Date(tx.created_at).toLocaleString()}
                        </span>
                        {tx.notes && (
                          <p className="text-xs text-slate-500 mt-0.5">{tx.notes}</p>
                        )}
                      </div>
                      <span
                        className={`font-semibold ${
                          Number(tx.quantity) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                        }`}
                      >
                        {Number(tx.quantity) > 0 ? '+' : ''}
                        {formatQty(tx.quantity)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {adjustOpen && (
          <AdjustModal
            form={adjustForm}
            setForm={setAdjustForm}
            products={products.length ? products : [{ id: productId, sku: detail?.sku, name: detail?.product_name }]}
            error={modalError}
            isSubmitting={isSubmitting}
            onClose={() => setAdjustOpen(false)}
            onSubmit={handleAdjust}
            lockProduct
          />
        )}
      </div>
    );
  }

  // ── Dashboard list ─────────────────────────────────────────
  const lowStockCount = items.filter((i) => i.is_low_stock).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Inventory</h1>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic stock levels — available = current − reserved
          </p>
        </div>
        {canAdjust && (
          <button
            onClick={async () => {
              if (!products.length) {
                const prods = await api.get('/products');
                setProducts(prods);
              }
              setAdjustForm({
                product_id: '',
                quantity_delta: '',
                notes: '',
                reorder_level: '',
              });
              setModalError('');
              setAdjustOpen(true);
            }}
            className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl shadow-lg shadow-indigo-600/20 transition"
          >
            Adjust Stock
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4">
          <div className="text-xs text-slate-400 uppercase tracking-wider">SKU Stocked</div>
          <div className="text-2xl font-bold text-white mt-1">{items.length}</div>
        </div>
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4">
          <div className="text-xs text-slate-400 uppercase tracking-wider">Low Stock</div>
          <div className="text-2xl font-bold text-amber-400 mt-1">{lowStockCount}</div>
        </div>
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4">
          <div className="text-xs text-slate-400 uppercase tracking-wider">Total Available</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            {formatQty(items.reduce((sum, i) => sum + Number(i.available_quantity || 0), 0))}
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-sm">
          {error}
        </div>
      )}

      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800/80">
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
            Stock Levels
          </h2>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-500">Loading inventory...</div>
        ) : items.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm space-y-2">
            <p>No inventory records yet.</p>
            <p>
              <Link to="/products" className="text-indigo-400 hover:underline">
                Create a product
              </Link>{' '}
              then adjust stock to get started.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 uppercase tracking-wider border-b border-slate-800">
                  <th className="px-6 py-3">SKU / Product</th>
                  <th className="px-4 py-3">Current</th>
                  <th className="px-4 py-3">Reserved</th>
                  <th className="px-4 py-3">Available</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-800/30">
                    <td className="px-6 py-3">
                      <div className="font-mono text-xs text-indigo-300">{item.sku}</div>
                      <div className="text-white text-sm">{item.product_name}</div>
                    </td>
                    <td className="px-4 py-3 text-slate-200">{formatQty(item.current_quantity)}</td>
                    <td className="px-4 py-3 text-slate-200">{formatQty(item.reserved_quantity)}</td>
                    <td className="px-4 py-3 font-semibold text-white">
                      {formatQty(item.available_quantity)}
                    </td>
                    <td className="px-4 py-3">
                      {item.is_low_stock ? (
                        <span className="text-xs px-2 py-0.5 rounded-lg border bg-amber-500/10 text-amber-400 border-amber-500/20">
                          Low stock
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded-lg border bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                          OK
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/inventory/${item.product_id}`}
                        className="text-xs text-indigo-400 hover:text-indigo-300"
                      >
                        Details →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {adjustOpen && (
        <AdjustModal
          form={adjustForm}
          setForm={setAdjustForm}
          products={products}
          error={modalError}
          isSubmitting={isSubmitting}
          onClose={() => setAdjustOpen(false)}
          onSubmit={handleAdjust}
        />
      )}
    </div>
  );
}

function AdjustModal({ form, setForm, products, error, isSubmitting, onClose, onSubmit, lockProduct }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-bold text-white">Adjust Stock</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            ✕
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={onSubmit} className="space-y-4">
          {!lockProduct && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Product
              </label>
              <select
                required
                value={form.product_id}
                onChange={(e) => setForm({ ...form, product_id: e.target.value })}
                className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
              >
                <option value="">Select product...</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.sku} — {p.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Quantity Delta
            </label>
            <input
              type="number"
              required
              step="any"
              value={form.quantity_delta}
              onChange={(e) => setForm({ ...form, quantity_delta: e.target.value })}
              placeholder="+5000 or -100"
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
            />
            <p className="text-[11px] text-slate-500 mt-1">
              Positive adds stock (receipt). Negative writes down stock.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Reorder Level (optional)
            </label>
            <input
              type="number"
              min="0"
              value={form.reorder_level}
              onChange={(e) => setForm({ ...form, reorder_level: e.target.value })}
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Notes
            </label>
            <input
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium disabled:opacity-50"
            >
              {isSubmitting ? 'Saving...' : 'Apply Adjustment'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
