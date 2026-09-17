import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';

const EMPTY_FORM = {
  sku: '',
  name: '',
  description: '',
  unit_of_measure: 'PCS',
  selling_currency: 'USD',
  default_hs_code: '',
  weight_kg: '',
  carton_capacity: '',
  base_cost: '',
};

export default function Products() {
  const { isAdmin, user } = useAuth();
  const canEdit = isAdmin || ['EXPORT_MANAGER', 'SALES'].includes(user?.role);
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [modalError, setModalError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchProducts = async (q = search) => {
    setIsLoading(true);
    try {
      const query = q.trim() ? `?q=${encodeURIComponent(q.trim())}` : '';
      const data = await api.get(`/products${query}`);
      setProducts(data);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load products');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  const openCreate = () => {
    setEditing(null);
    setFormData(EMPTY_FORM);
    setModalError('');
    setIsModalOpen(true);
  };

  const openEdit = (product) => {
    setEditing(product);
    setFormData({
      sku: product.sku || '',
      name: product.name || '',
      description: product.description || '',
      unit_of_measure: product.unit_of_measure || 'PCS',
      selling_currency: product.selling_currency || 'USD',
      default_hs_code: product.default_hs_code || '',
      weight_kg: product.weight_kg ?? '',
      carton_capacity: product.carton_capacity ?? '',
      base_cost: product.base_cost ?? '',
    });
    setModalError('');
    setIsModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setModalError('');
    setIsSubmitting(true);

    const payload = {
      sku: formData.sku,
      name: formData.name,
      description: formData.description || null,
      unit_of_measure: formData.unit_of_measure,
      selling_currency: formData.selling_currency,
      default_hs_code: formData.default_hs_code || null,
      weight_kg: formData.weight_kg === '' ? null : Number(formData.weight_kg),
      carton_capacity: formData.carton_capacity === '' ? null : Number(formData.carton_capacity),
      base_cost: formData.base_cost === '' ? null : Number(formData.base_cost),
    };

    try {
      if (editing) {
        await api.put(`/products/${editing.id}`, payload);
      } else {
        await api.post('/products', payload);
      }
      setIsModalOpen(false);
      fetchProducts();
    } catch (err) {
      setModalError(err.message || 'Failed to save product');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (product) => {
    if (!window.confirm(`Delete product ${product.sku}?`)) return;
    try {
      await api.delete(`/products/${product.id}`);
      fetchProducts();
    } catch (err) {
      setError(err.message || 'Failed to delete product');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Product Catalogue</h1>
          <p className="text-sm text-slate-400 mt-1">
            SKUs, packing data, and HS codes for inventory and deals
          </p>
        </div>
        {canEdit && (
          <button
            onClick={openCreate}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl shadow-lg shadow-indigo-600/20 transition"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Product
          </button>
        )}
      </div>

      <div className="flex gap-3">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && fetchProducts()}
          placeholder="Search by SKU or name..."
          className="flex-1 px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500"
        />
        <button
          onClick={() => fetchProducts()}
          className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-sm font-medium transition"
        >
          Search
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-sm">
          {error}
        </div>
      )}

      <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
            Products ({products.length})
          </h2>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-500">Loading products...</div>
        ) : products.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No products yet. Create your first SKU to enable inventory.
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {products.map((product) => (
              <div
                key={product.id}
                className="px-6 py-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4 hover:bg-slate-800/30 transition"
              >
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-indigo-300 border border-slate-700">
                      {product.sku}
                    </span>
                    <span className="text-sm font-semibold text-white">{product.name}</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    {product.unit_of_measure} · {product.selling_currency}
                    {product.weight_kg != null ? ` · ${product.weight_kg} kg` : ''}
                    {product.carton_capacity != null ? ` · ${product.carton_capacity}/carton` : ''}
                    {product.default_hs_code ? ` · HS ${product.default_hs_code}` : ''}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Link
                    to={`/inventory/${product.id}`}
                    className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 text-slate-300 hover:text-white transition"
                  >
                    Inventory
                  </Link>
                  {canEdit && (
                    <button
                      onClick={() => openEdit(product)}
                      className="px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30 transition"
                    >
                      Edit
                    </button>
                  )}
                  {(isAdmin || user?.role === 'EXPORT_MANAGER') && (
                    <button
                      onClick={() => handleDelete(product)}
                      className="px-3 py-1.5 text-xs font-medium rounded-lg bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 transition"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl my-8">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-bold text-white">
                {editing ? 'Edit Product' : 'Add Product'}
              </h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white">
                ✕
              </button>
            </div>

            {modalError && (
              <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs">
                {modalError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    SKU
                  </label>
                  <input
                    required
                    value={formData.sku}
                    onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
                    placeholder="FB-S5-001"
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    UOM
                  </label>
                  <input
                    required
                    value={formData.unit_of_measure}
                    onChange={(e) => setFormData({ ...formData, unit_of_measure: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Name
                </label>
                <input
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Size-5 Football"
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Description
                </label>
                <textarea
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Currency
                  </label>
                  <input
                    required
                    maxLength={3}
                    value={formData.selling_currency}
                    onChange={(e) => setFormData({ ...formData, selling_currency: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    HS Code
                  </label>
                  <input
                    value={formData.default_hs_code}
                    onChange={(e) => setFormData({ ...formData, default_hs_code: e.target.value })}
                    placeholder="9506.62"
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Weight (kg)
                  </label>
                  <input
                    type="number"
                    step="0.0001"
                    min="0"
                    value={formData.weight_kg}
                    onChange={(e) => setFormData({ ...formData, weight_kg: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Carton Capacity
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={formData.carton_capacity}
                    onChange={(e) => setFormData({ ...formData, carton_capacity: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Base Cost
                  </label>
                  <input
                    type="number"
                    step="0.0001"
                    min="0"
                    value={formData.base_cost}
                    onChange={(e) => setFormData({ ...formData, base_cost: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-medium transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition disabled:opacity-50"
                >
                  {isSubmitting ? 'Saving...' : editing ? 'Save Changes' : 'Create Product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
