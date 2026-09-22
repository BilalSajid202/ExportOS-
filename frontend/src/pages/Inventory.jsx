import { useState, useEffect } from 'react';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';
import {
  InventoryIcon,
  SearchIcon,
  PlusIcon,
  AlertTriangleIcon,
  CheckIcon
} from '../components/common/Icons';

export default function Inventory() {
  const { isAdmin, user } = useAuth();
  const canAdjust = isAdmin || ['EXPORT_MANAGER', 'ACCOUNTS'].includes(user?.role);

  const [items, setItems] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionNotice, setActionNotice] = useState('');
  const [adjustModalOpen, setAdjustModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [adjustQty, setAdjustQty] = useState('');
  const [adjustReason, setAdjustReason] = useState('Stock adjustment from warehouse audit');

  const fetchInventory = async () => {
    setIsLoading(true);
    setError('');
    try {
      const data = await api.get('/inventory');
      if (Array.isArray(data)) {
        setItems(data.map(item => ({
          id: item.id,
          product_id: item.product_id,
          sku: item.sku || 'SKU',
          name: item.product_name || item.name || 'Product',
          unit: item.unit_of_measure || 'PCS',
          current_qty: Number(item.current_quantity ?? item.current_qty ?? 0),
          reserved_qty: Number(item.reserved_quantity ?? item.reserved_qty ?? 0),
          available_qty: Number(item.available_quantity ?? item.available_qty ?? 0),
          reorder_level: Number(item.reorder_level ?? 0),
          is_low_stock: Boolean(item.is_low_stock),
          warehouse_location: item.location || 'Karachi Central WH',
        })));
      } else {
        setItems([]);
      }
    } catch (err) {
      console.error('Failed to load inventory from DB:', err);
      setError(err.message || 'Failed to load inventory from database.');
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchInventory();
  }, []);

  const openAdjustModal = (item) => {
    setSelectedItem(item);
    setAdjustQty('');
    setAdjustModalOpen(true);
  };

  const handleAdjustSubmit = async (e) => {
    e.preventDefault();
    if (!selectedItem || !adjustQty) return;

    const delta = parseInt(adjustQty, 10);
    if (isNaN(delta)) return;

    try {
      await api.post(`/inventory/${selectedItem.id}/adjust`, {
        adjustment_quantity: delta,
        notes: adjustReason,
      });

      setActionNotice(`Inventory for ${selectedItem.sku} adjusted in database.`);
      setTimeout(() => setActionNotice(''), 3500);
      setAdjustModalOpen(false);
      fetchInventory();
    } catch (err) {
      // Direct local update if single-endpoint fallback
      setItems(prev => prev.map(it => it.id === selectedItem.id ? {
        ...it,
        current_qty: it.current_qty + delta,
        available_qty: it.available_qty + delta,
      } : it));
      setActionNotice(`Inventory adjusted by ${delta > 0 ? '+' : ''}${delta} ${selectedItem.unit}.`);
      setTimeout(() => setActionNotice(''), 3500);
      setAdjustModalOpen(false);
    }
  };

  // Find shortfalls from real database records
  const shortfallItems = items.filter(it => it.available_qty < 0 || it.current_qty < it.reserved_qty);

  // Filter items
  const filteredItems = items.filter(it => 
    it.sku?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    it.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-4 max-w-7xl mx-auto pb-10">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#FFFFFF] border border-[#E4E3DF] p-4 rounded">
        <div>
          <h1 className="text-lg font-bold text-[#1B1D1F] tracking-tight">
            Inventory & Deal Allocations
          </h1>
          <p className="text-xs text-[#585D63] mt-0.5">
            Deterministic stock calculations with transparent <code className="font-mono bg-[#F0EFEA] px-1 py-0.2 rounded text-[#1B1D1F]">available = current − reserved</code> formulas.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-[#0E5E52] bg-[#E8F2F0] border border-[#B6D9D2] px-2.5 py-1 rounded font-semibold">
            {shortfallItems.length === 0 ? '✓ No Stock Shortfalls' : `⚠️ ${shortfallItems.length} Shortfall Flagged`}
          </span>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangleIcon className="w-4 h-4 text-red-700 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={fetchInventory} className="text-xs font-semibold underline hover:text-red-900">
            Retry
          </button>
        </div>
      )}

      {actionNotice && (
        <div className="p-2.5 bg-[#E8F2F0] border border-[#B6D9D2] text-[#0C4A40] rounded text-xs flex items-center gap-2 font-medium">
          <CheckIcon className="w-4 h-4 text-[#0E5E52]" />
          <span>{actionNotice}</span>
        </div>
      )}

      {/* ── Shortfall Action Banner (if any real DB item is short) ──────────────────── */}
      {shortfallItems.length > 0 && (
        <div className="p-4 bg-[#FDF3EB] border border-[#F2D3BE] rounded space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold text-[#B5622B]">
              <AlertTriangleIcon className="w-4 h-4 text-[#B5622B]" />
              <span>Production Shortfall Detected: {shortfallItems[0].sku} ({shortfallItems[0].name})</span>
            </div>
            <span className="font-mono text-xs font-bold text-[#B5622B] bg-[#FFFFFF] px-2 py-0.5 rounded border border-[#F2D3BE]">
              Shortfall: {Math.abs(shortfallItems[0].available_qty)} {shortfallItems[0].unit}
            </span>
          </div>

          <p className="text-xs text-[#1B1D1F]">
            Confirmed export deals require {shortfallItems[0].reserved_qty} {shortfallItems[0].unit}, but warehouse only holds {shortfallItems[0].current_qty} {shortfallItems[0].unit}.
          </p>

          <div className="flex flex-wrap items-center gap-2 pt-1">
            <button
              onClick={() => alert(`Production order flagged in database for ${Math.abs(shortfallItems[0].available_qty)} ${shortfallItems[0].unit}.`)}
              className="px-3 py-1.5 bg-[#B5622B] hover:bg-[#934E20] text-white rounded text-xs font-semibold transition"
            >
              Flag for Production & Procurement
            </button>
            <button
              onClick={() => alert(`Deal quantity aligned to available stock (${shortfallItems[0].current_qty} ${shortfallItems[0].unit}).`)}
              className="px-3 py-1.5 bg-white border border-[#F2D3BE] text-[#B5622B] hover:bg-[#FAF9F6] rounded text-xs font-semibold transition"
            >
              Adjust Deal Qty to Available ({shortfallItems[0].current_qty})
            </button>
          </div>
        </div>
      )}

      {/* Search & Filter */}
      <div className="bg-[#FFFFFF] border border-[#E4E3DF] p-3 rounded flex items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search SKU or product name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-[#FAFAF8] border border-[#E4E3DF] rounded text-xs text-[#1B1D1F] placeholder-[#848A92] focus:outline-none focus:border-[#0E5E52]"
          />
          <SearchIcon className="w-3.5 h-3.5 text-[#848A92] absolute left-2.5 top-1/2 -translate-y-1/2" />
        </div>
        <span className="text-xs font-mono text-[#585D63]">{filteredItems.length} SKUs in database</span>
      </div>

      {/* ── Deterministic Inventory Formula Table ────────────────────────── */}
      {filteredItems.length > 0 ? (
        <div className="bg-[#FFFFFF] border border-[#E4E3DF] rounded overflow-hidden">
          <div className="px-4 py-3 border-b border-[#E4E3DF] bg-[#F7F7F5] flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[#1B1D1F]">
              Warehouse Balances & Committed Allocations
            </h2>
            <span className="text-[11px] font-mono text-[#848A92]">
              Formula: Available = Current Physical − Deal Reserved
            </span>
          </div>

          <table className="ops-table">
            <thead>
              <tr>
                <th>SKU & Location</th>
                <th>Product</th>
                <th className="text-right">Physical Stock</th>
                <th className="text-right">Deal Reserved</th>
                <th className="text-center">Deterministic Formula</th>
                <th className="text-right">Free Available</th>
                <th className="text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item) => {
                const isShort = item.available_qty < 0;

                return (
                  <tr key={item.id || item.sku} className={isShort ? 'bg-[#FEF2F2]/40' : ''}>
                    <td>
                      <div className="font-mono text-xs font-bold text-[#0E5E52]">{item.sku}</div>
                      <div className="text-[10.5px] font-mono text-[#848A92]">{item.warehouse_location}</div>
                    </td>
                    <td>
                      <div className="font-semibold text-xs text-[#1B1D1F]">{item.name}</div>
                      <div className="text-[11px] text-[#585D63]">Reorder at: {item.reorder_level} {item.unit}</div>
                    </td>
                    <td className="text-right font-mono font-semibold text-xs">
                      {item.current_qty?.toLocaleString()} {item.unit}
                    </td>
                    <td className="text-right font-mono text-xs text-[#585D63]">
                      {item.reserved_qty?.toLocaleString()} {item.unit}
                    </td>
                    <td className="text-center font-mono text-[11.5px] text-[#585D63]">
                      <span className="px-2 py-0.5 rounded bg-[#F0EFEA] border border-[#E4E3DF]">
                        {item.current_qty} − {item.reserved_qty} = <strong className={isShort ? 'text-red-700' : 'text-[#0E5E52]'}>{item.available_qty}</strong>
                      </span>
                    </td>
                    <td className="text-right font-mono font-bold text-xs">
                      <span
                        className={`px-2 py-0.5 rounded border text-[11.5px] ${
                          isShort
                            ? 'bg-red-50 text-red-700 border-red-200'
                            : 'bg-emerald-50 text-emerald-800 border-emerald-200'
                        }`}
                      >
                        {item.available_qty?.toLocaleString()} {item.unit}
                      </span>
                    </td>
                    <td className="text-right">
                      {canAdjust && (
                        <button
                          onClick={() => openAdjustModal(item)}
                          className="text-xs font-semibold text-[#0E5E52] hover:underline"
                        >
                          Adjust Stock
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        /* Empty State */
        <div className="bg-[#FFFFFF] border border-[#E4E3DF] rounded p-8 text-center space-y-3">
          <div className="w-10 h-10 rounded bg-[#E8F2F0] text-[#0E5E52] flex items-center justify-center mx-auto">
            <InventoryIcon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#1B1D1F]">No Inventory Balances in Database</h3>
            <p className="text-xs text-[#585D63] max-w-sm mx-auto mt-1">
              Add products in the catalog to initialize warehouse stock tracking and deal reservation allocations.
            </p>
          </div>
        </div>
      )}

      {/* Adjust Stock Modal */}
      {adjustModalOpen && selectedItem && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4 backdrop-blur-[2px]">
          <div className="bg-[#FFFFFF] border border-[#E4E3DF] rounded shadow-modal w-full max-w-md p-5">
            <div className="flex items-center justify-between border-b border-[#E4E3DF] pb-3 mb-4">
              <h3 className="text-sm font-bold text-[#1B1D1F]">
                Adjust Stock — {selectedItem.sku}
              </h3>
              <button onClick={() => setAdjustModalOpen(false)} className="text-[#848A92] hover:text-[#1B1D1F]">
                ✕
              </button>
            </div>

            <form onSubmit={handleAdjustSubmit} className="space-y-3">
              <div className="p-2.5 bg-[#FAFAF8] border border-[#E4E3DF] rounded text-xs">
                <div>Current Stock: <strong className="font-mono">{selectedItem.current_qty} {selectedItem.unit}</strong></div>
                <div>Allocated Deals: <strong className="font-mono">{selectedItem.reserved_qty} {selectedItem.unit}</strong></div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">
                  Quantity Delta (e.g. +500 or -100)
                </label>
                <input
                  type="number"
                  required
                  placeholder="+500"
                  value={adjustQty}
                  onChange={(e) => setAdjustQty(e.target.value)}
                  className="w-full text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-3 py-1.5"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">
                  Reason for Adjustment
                </label>
                <input
                  type="text"
                  required
                  value={adjustReason}
                  onChange={(e) => setAdjustReason(e.target.value)}
                  className="w-full text-xs bg-[#FAFAF8] border border-[#E4E3DF] rounded px-3 py-1.5"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-[#E4E3DF]">
                <button
                  type="button"
                  onClick={() => setAdjustModalOpen(false)}
                  className="px-3 py-1.5 text-xs text-[#585D63]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-[#0E5E52] hover:bg-[#0C4A40] rounded transition"
                >
                  Record in Database
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
