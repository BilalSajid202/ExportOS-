import { useState, useEffect } from 'react';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';
import MoneyValue from '../components/common/MoneyValue';
import {
  ProductsIcon,
  SearchIcon,
  PlusIcon,
  AlertTriangleIcon
} from '../components/common/Icons';

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
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'grid'
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [modalError, setModalError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchProducts = async (q = search) => {
    setIsLoading(true);
    setError('');
    try {
      const query = q.trim() ? `?q=${encodeURIComponent(q.trim())}` : '';
      const data = await api.get(`/products${query}`);
      setProducts(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load products from DB:', err);
      setError(err.message || 'Failed to load products from database.');
      setProducts([]);
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
      weight_kg: product.weight_kg != null ? String(product.weight_kg) : '',
      carton_capacity: product.carton_capacity != null ? String(product.carton_capacity) : '',
      base_cost: product.base_cost != null ? String(product.base_cost) : '',
    });
    setModalError('');
    setIsModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setModalError('');
    setIsSubmitting(true);

    const payload = {
      ...formData,
      weight_kg: formData.weight_kg ? parseFloat(formData.weight_kg) : null,
      carton_capacity: formData.carton_capacity ? parseInt(formData.carton_capacity, 10) : null,
      base_cost: formData.base_cost ? parseFloat(formData.base_cost) : null,
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
      setModalError(err.message || 'Failed to save product in database');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4 max-w-7xl mx-auto pb-10">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#FFFFFF] border border-[#E4E3DF] p-4 rounded">
        <div>
          <h1 className="text-lg font-bold text-[#1B1D1F] tracking-tight">
            Product Master & HS Catalog
          </h1>
          <p className="text-xs text-[#585D63] mt-0.5">
            Standardized SKUs, international HS codes, baseline factory costing, and volumetric packing specs.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {canEdit && (
            <button
              onClick={openCreate}
              className="px-3 py-1.5 text-xs font-semibold text-white bg-[#0E5E52] hover:bg-[#0C4A40] rounded transition flex items-center gap-1.5"
            >
              <PlusIcon className="w-3.5 h-3.5 text-white" />
              <span>Add Product</span>
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangleIcon className="w-4 h-4 text-red-700 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => fetchProducts()} className="text-xs font-semibold underline hover:text-red-900">
            Retry
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-[#FFFFFF] border border-[#E4E3DF] p-3 rounded flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search by SKU, product name, or HS code..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchProducts(search)}
            className="w-full pl-8 pr-3 py-1.5 bg-[#FAFAF8] border border-[#E4E3DF] rounded text-xs text-[#1B1D1F] placeholder-[#848A92] focus:outline-none focus:border-[#0E5E52]"
          />
          <SearchIcon className="w-3.5 h-3.5 text-[#848A92] absolute left-2.5 top-1/2 -translate-y-1/2" />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-[#585D63] font-mono">{products.length} products in DB</span>
          <div className="inline-flex rounded border border-[#E4E3DF] bg-[#FAFAF8] p-0.5 text-xs font-mono">
            <button
              onClick={() => setViewMode('table')}
              className={`px-2 py-0.5 rounded transition ${viewMode === 'table' ? 'bg-white shadow-subtle text-[#0E5E52] font-semibold' : 'text-[#848A92]'}`}
            >
              Table
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`px-2 py-0.5 rounded transition ${viewMode === 'grid' ? 'bg-white shadow-subtle text-[#0E5E52] font-semibold' : 'text-[#848A92]'}`}
            >
              Grid
            </button>
          </div>
        </div>
      </div>

      {/* Products Data View */}
      {products.length > 0 ? (
        viewMode === 'table' ? (
          <div className="bg-[#FFFFFF] border border-[#E4E3DF] rounded overflow-hidden">
            <table className="ops-table">
              <thead>
                <tr>
                  <th>SKU Code</th>
                  <th>Product Description</th>
                  <th>HS Code</th>
                  <th>UoM</th>
                  <th className="text-right">Factory Base Cost</th>
                  <th className="text-right">Unit Weight</th>
                  <th className="text-right">Carton Qty</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id || p.sku}>
                    <td className="font-mono text-xs font-bold text-[#0E5E52]">
                      {p.sku}
                    </td>
                    <td>
                      <div className="font-semibold text-xs text-[#1B1D1F]">{p.name}</div>
                      <div className="text-[11px] text-[#585D63] truncate max-w-sm">{p.description}</div>
                    </td>
                    <td className="font-mono text-xs text-[#1B1D1F]">
                      <span className="px-1.5 py-0.5 rounded bg-[#F0EFEA] border border-[#E4E3DF]">
                        {p.default_hs_code || '—'}
                      </span>
                    </td>
                    <td className="font-mono text-xs text-[#585D63]">
                      {p.unit_of_measure || 'PCS'}
                    </td>
                    <td className="text-right font-mono font-semibold">
                      <MoneyValue amount={p.base_cost || 0} currency={p.selling_currency || 'USD'} />
                    </td>
                    <td className="text-right font-mono text-xs text-[#585D63]">
                      {p.weight_kg ? `${p.weight_kg} kg` : '—'}
                    </td>
                    <td className="text-right font-mono text-xs text-[#585D63]">
                      {p.carton_capacity ? `${p.carton_capacity} / ctn` : '—'}
                    </td>
                    <td className="text-right">
                      {canEdit && (
                        <button
                          onClick={() => openEdit(p)}
                          className="text-xs font-semibold text-[#0E5E52] hover:underline"
                        >
                          Edit
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {products.map((p) => (
              <div key={p.id || p.sku} className="p-4 bg-[#FFFFFF] border border-[#E4E3DF] rounded space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-[#0E5E52] bg-[#E8F2F0] px-1.5 py-0.2 rounded border border-[#B6D9D2]">
                    {p.sku}
                  </span>
                  <span className="font-mono text-[11px] text-[#848A92]">{p.default_hs_code}</span>
                </div>
                <h3 className="font-bold text-xs text-[#1B1D1F]">{p.name}</h3>
                <p className="text-[11px] text-[#585D63] line-clamp-2">{p.description}</p>
                <div className="pt-2 border-t border-[#E4E3DF] flex items-center justify-between text-xs">
                  <MoneyValue amount={p.base_cost || 0} currency={p.selling_currency || 'USD'} />
                  {canEdit && (
                    <button onClick={() => openEdit(p)} className="text-[#0E5E52] font-semibold hover:underline">
                      Edit &rarr;
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        /* Empty State */
        <div className="bg-[#FFFFFF] border border-[#E4E3DF] rounded p-8 text-center space-y-3">
          <div className="w-10 h-10 rounded bg-[#E8F2F0] text-[#0E5E52] flex items-center justify-center mx-auto">
            <ProductsIcon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#1B1D1F]">No Products in Database Catalog</h3>
            <p className="text-xs text-[#585D63] max-w-sm mx-auto mt-1">
              Add master SKUs, factory base costs, and default HS codes to enable automated deal costing and quotation.
            </p>
          </div>
          {canEdit && (
            <button
              onClick={openCreate}
              className="px-4 py-2 text-xs font-semibold text-white bg-[#0E5E52] hover:bg-[#0C4A40] rounded transition"
            >
              + Add First Product
            </button>
          )}
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4 backdrop-blur-[2px]">
          <div className="bg-[#FFFFFF] border border-[#E4E3DF] rounded shadow-modal w-full max-w-lg p-5">
            <div className="flex items-center justify-between border-b border-[#E4E3DF] pb-3 mb-4">
              <h3 className="text-sm font-bold text-[#1B1D1F]">
                {editing ? 'Edit Product' : 'Add New Export Product'}
              </h3>
              <button onClick={() => setIsModalOpen(false)} className="text-[#848A92] hover:text-[#1B1D1F]">
                ✕
              </button>
            </div>

            {modalError && (
              <div className="mb-3 p-2 bg-red-50 border border-red-200 text-red-700 rounded text-xs">
                {modalError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">SKU Code *</label>
                  <input
                    type="text"
                    required
                    value={formData.sku}
                    onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
                    className="w-full text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-2.5 py-1.5"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">Default HS Code *</label>
                  <input
                    type="text"
                    required
                    value={formData.default_hs_code}
                    onChange={(e) => setFormData({ ...formData, default_hs_code: e.target.value })}
                    className="w-full text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-2.5 py-1.5"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">Product Name *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full text-xs bg-[#FAFAF8] border border-[#E4E3DF] rounded px-2.5 py-1.5"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">Description / Spec</label>
                <textarea
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full text-xs bg-[#FAFAF8] border border-[#E4E3DF] rounded px-2.5 py-1.5"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">Base Cost (USD)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.base_cost}
                    onChange={(e) => setFormData({ ...formData, base_cost: e.target.value })}
                    className="w-full text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-2.5 py-1.5"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">Unit Weight (kg)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.weight_kg}
                    onChange={(e) => setFormData({ ...formData, weight_kg: e.target.value })}
                    className="w-full text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-2.5 py-1.5"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">Carton Cap</label>
                  <input
                    type="number"
                    value={formData.carton_capacity}
                    onChange={(e) => setFormData({ ...formData, carton_capacity: e.target.value })}
                    className="w-full text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-2.5 py-1.5"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-[#E4E3DF]">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3 py-1.5 text-xs text-[#585D63]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-[#0E5E52] hover:bg-[#0C4A40] rounded transition"
                >
                  {isSubmitting ? 'Saving to DB...' : 'Save Product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
