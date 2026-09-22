import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';

/* ── Incoterm Visual Badge Helper ─────────────────────────── */
const INCOTERM_COLORS = {
  FOB: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  CIF: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  CFR: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
  EXW: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  DAP: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  DDP: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
};

export default function Dashboard() {
  const { user, organisation } = useAuth();

  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Currency view toggle: 'USD' | 'PKR'
  const [currencyMode, setCurrencyMode] = useState('USD');
  const [exportNotice, setExportNotice] = useState('');

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const data = await api.get('/analytics/executive-summary');
      setAnalytics(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load executive analytics:', err);
      setError(err.message || 'Failed to load executive analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 45000); // 45s refresh
    return () => clearInterval(interval);
  }, []);

  const handleDownloadReport = () => {
    if (!analytics) return;
    const reportData = {
      organisation: organisation?.name || 'ExportOS Enterprise',
      generated_at: new Date().toISOString(),
      executive_kpis: analytics.kpis,
      profitability_by_incoterm: analytics.profitability_by_incoterm,
      profitability_by_product: analytics.profitability_by_product,
      destination_markets: analytics.destination_markets,
      pipeline_funnel: analytics.pipeline_funnel,
      sbp_exposure: analytics.sbp_exposure,
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ExportOS_Executive_Report_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setExportNotice('✓ Executive compliance and commercial report exported successfully!');
    setTimeout(() => setExportNotice(''), 4000);
  };

  const kpis = analytics?.kpis;
  const sbp = analytics?.sbp_exposure;

  return (
    <div className="space-y-6 pb-12">
      {/* ── Executive Header Banner ─────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-slate-900/80 border border-slate-800 p-6 rounded-2xl backdrop-blur relative overflow-hidden">
        <div className="space-y-1 relative z-10">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              Executive Cockpit
            </span>
            <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Live Data Engine Connected
            </span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            {organisation?.name || 'ExportOS'} — Operational & Profitability Intelligence
          </h1>
          <p className="text-xs text-slate-400">
            Real-time export contract pipeline, SBP Foreign Exchange Chapter XII compliance radar, and gross margin realization.
          </p>
        </div>

        {/* Header Actions */}
        <div className="flex flex-wrap items-center gap-2.5 relative z-10">
          {/* Currency Toggle */}
          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-xl p-1 text-xs">
            <button
              onClick={() => setCurrencyMode('USD')}
              className={`px-3 py-1 rounded-lg font-semibold transition ${
                currencyMode === 'USD'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              $ USD
            </button>
            <button
              onClick={() => setCurrencyMode('PKR')}
              className={`px-3 py-1 rounded-lg font-semibold transition ${
                currencyMode === 'PKR'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              ₨ PKR
            </button>
          </div>

          <button
            onClick={handleDownloadReport}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition shadow-sm"
            title="Download structured JSON report for audit and executive presentation"
          >
            <span>📥</span>
            <span>Export Report</span>
          </button>

          <Link
            to="/copilot"
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-indigo-600 to-emerald-600 hover:from-indigo-500 hover:to-emerald-500 text-white shadow-md shadow-indigo-500/20 transition"
          >
            <span>🤖</span>
            <span>Launch Copilot</span>
          </Link>
        </div>

        {/* Subtle Decorative Background Glow */}
        <div className="absolute -right-10 -bottom-10 w-64 h-64 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none"></div>
      </div>

      {/* Export Toast Notification */}
      {exportNotice && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 rounded-xl text-xs font-semibold text-center animate-fadeIn">
          {exportNotice}
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-xs">
          {error}
        </div>
      )}

      {/* ── Top Financial KPI Ribbon (4 Big Cards) ────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* KPI 1: Gross Export Pipeline */}
        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-2xl space-y-2 relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Gross Export Pipeline</span>
            <span className="text-lg">📊</span>
          </div>
          <div className="text-2xl font-black text-white">
            {loading ? (
              <div className="h-8 w-24 bg-slate-800 animate-pulse rounded"></div>
            ) : (
              `$ ${Number(kpis?.total_pipeline_value_usd || 0).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}`
            )}
          </div>
          <div className="flex items-center justify-between pt-1 border-t border-slate-800/80 text-[11px] text-slate-400">
            <span>Active Contracts</span>
            <span className="font-semibold text-indigo-400">
              {kpis?.total_active_deals || 0} Deals
            </span>
          </div>
        </div>

        {/* KPI 2: Realized Export Remittances */}
        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-2xl space-y-2 relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Settled Realized Revenue</span>
            <span className="text-lg">💵</span>
          </div>
          <div className="text-2xl font-black text-emerald-400">
            {loading ? (
              <div className="h-8 w-28 bg-slate-800 animate-pulse rounded"></div>
            ) : currencyMode === 'USD' ? (
              `$ ${Number(kpis?.total_realized_revenue_usd || 0).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}`
            ) : (
              `PKR ${Number(kpis?.total_realized_revenue_pkr || 0).toLocaleString(undefined, {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0,
              })}`
            )}
          </div>
          <div className="flex items-center justify-between pt-1 border-t border-slate-800/80 text-[11px] text-slate-400">
            <span>Reconciled Deals</span>
            <span className="font-semibold text-emerald-400">
              {kpis?.total_completed_deals || 0} Closed
            </span>
          </div>
        </div>

        {/* KPI 3: Average Gross Margin */}
        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-2xl space-y-2 relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Average Gross Margin</span>
            <span className="text-lg">📈</span>
          </div>
          <div className="text-2xl font-black text-indigo-400">
            {loading ? (
              <div className="h-8 w-20 bg-slate-800 animate-pulse rounded"></div>
            ) : (
              `${kpis?.average_gross_margin_pct || 0}%`
            )}
          </div>
          <div className="flex items-center justify-between pt-1 border-t border-slate-800/80 text-[11px] text-slate-400">
            <span>Doc Audit Pass Rate</span>
            <span className="font-semibold text-indigo-300">
              {kpis?.doc_consistency_pass_rate_pct || 100}% Passed
            </span>
          </div>
        </div>

        {/* KPI 4: SBP 120-Day Exposure */}
        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-2xl space-y-2 relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>SBP 120-Day Exposure</span>
            <span className="text-lg">⚖️</span>
          </div>
          <div
            className={`text-2xl font-black ${
              Number(kpis?.sbp_at_risk_exposure_usd || 0) > 0 ? 'text-rose-400' : 'text-slate-200'
            }`}
          >
            {loading ? (
              <div className="h-8 w-24 bg-slate-800 animate-pulse rounded"></div>
            ) : (
              `$ ${Number(kpis?.sbp_at_risk_exposure_usd || 0).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}`
            )}
          </div>
          <div className="flex items-center justify-between pt-1 border-t border-slate-800/80 text-[11px]">
            <span className="text-slate-400">Urgent Attention</span>
            <span
              className={`font-semibold ${
                sbp?.at_risk_deals_count > 0 ? 'text-rose-400' : 'text-emerald-400'
              }`}
            >
              {sbp?.at_risk_deals_count || 0} At Risk
            </span>
          </div>
        </div>
      </div>

      {/* ── Middle Grid: Pipeline Waterfall & Profitability (Left) + SBP Radar & Markets (Right) ─ */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* ── Left Column (7/12 width): Funnel & Profitability Breakdowns ─ */}
        <div className="lg:col-span-7 space-y-6">
          {/* Deal Pipeline Progression Waterfall */}
          <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white tracking-tight">
                  Deal Progression Funnel & Velocity
                </h3>
                <p className="text-xs text-slate-400">
                  Distribution of active contracts across export state machine stages
                </p>
              </div>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {analytics?.pipeline_funnel?.length || 0} Active Stages
              </span>
            </div>

            {loading ? (
              <div className="space-y-2 py-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-7 bg-slate-800/60 rounded-xl animate-pulse"></div>
                ))}
              </div>
            ) : !analytics?.pipeline_funnel || analytics.pipeline_funnel.length === 0 ? (
              <div className="text-center py-6 text-xs text-slate-500">
                No deal state progression records available.
              </div>
            ) : (
              <div className="space-y-2.5">
                {analytics.pipeline_funnel.map((stage) => {
                  const totalPipe = Number(kpis?.total_pipeline_value_usd) || 1;
                  const pct = Math.min(
                    Math.round((Number(stage.total_value_usd) / totalPipe) * 100),
                    100
                  );
                  return (
                    <div key={stage.state} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                          <span>{stage.state}</span>
                        </span>
                        <div className="flex items-center gap-2 font-mono">
                          <span className="text-slate-400">
                            {stage.deal_count} {stage.deal_count === 1 ? 'deal' : 'deals'}
                          </span>
                          <span className="font-semibold text-slate-200">
                            ${Number(stage.total_value_usd).toLocaleString()}
                          </span>
                        </div>
                      </div>
                      <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                        <div
                          className="h-full bg-gradient-to-r from-indigo-600 to-emerald-500 rounded-full transition-all duration-500"
                          style={{ width: `${Math.max(pct, 5)}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Profitability by Incoterm */}
          <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white tracking-tight">
                  Commercial Profitability by Incoterm
                </h3>
                <p className="text-xs text-slate-400">
                  Gross profit contribution and margin % across trade delivery terms
                </p>
              </div>
              <span className="text-xs font-mono text-slate-400">Incoterms 2020</span>
            </div>

            {loading ? (
              <div className="space-y-2 py-4">
                {[1, 2].map((i) => (
                  <div key={i} className="h-10 bg-slate-800/60 rounded-xl animate-pulse"></div>
                ))}
              </div>
            ) : !analytics?.profitability_by_incoterm || analytics.profitability_by_incoterm.length === 0 ? (
              <div className="text-center py-6 text-xs text-slate-500">
                No quotation records available for Incoterm breakdown.
              </div>
            ) : (
              <div className="space-y-3">
                {analytics.profitability_by_incoterm.map((item) => (
                  <div
                    key={item.incoterm}
                    className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-xl flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
                  >
                    <div className="flex items-center gap-2.5">
                      <span
                        className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${
                          INCOTERM_COLORS[item.incoterm] || 'bg-slate-800 text-slate-300 border-slate-700'
                        }`}
                      >
                        {item.incoterm}
                      </span>
                      <div>
                        <div className="text-xs font-semibold text-slate-200">
                          ${Number(item.total_revenue_usd).toLocaleString()} Revenue
                        </div>
                        <div className="text-[11px] text-slate-400">
                          {item.deal_count} {item.deal_count === 1 ? 'quote' : 'quotes'} · Base Cost: $
                          {Number(item.total_cost_usd).toLocaleString()}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 self-end sm:self-auto">
                      <div className="text-right">
                        <div className="text-xs font-bold text-emerald-400">
                          +${Number(item.total_margin_usd).toLocaleString()} Margin
                        </div>
                        <div className="text-[11px] font-semibold text-slate-400">
                          Avg: {item.average_margin_pct}%
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Product SKU Sales & Profit Margin Matrix */}
          <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white tracking-tight">
                  Master SKU Sales & Margin Matrix
                </h3>
                <p className="text-xs text-slate-400">
                  Performance and gross margin contribution per Master Catalogue SKU
                </p>
              </div>
              <Link
                to="/products"
                className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold transition"
              >
                Catalogue →
              </Link>
            </div>

            {loading ? (
              <div className="space-y-2 py-4">
                {[1, 2].map((i) => (
                  <div key={i} className="h-8 bg-slate-800/60 rounded-xl animate-pulse"></div>
                ))}
              </div>
            ) : !analytics?.profitability_by_product || analytics.profitability_by_product.length === 0 ? (
              <div className="text-center py-6 text-xs text-slate-500">
                No product sales records yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Product / SKU</th>
                      <th className="py-2.5 px-3">Units Sold</th>
                      <th className="py-2.5 px-3">Gross Revenue</th>
                      <th className="py-2.5 px-3 text-right">Margin %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {analytics.profitability_by_product.map((prod) => (
                      <tr key={prod.product_id} className="hover:bg-slate-800/30 transition">
                        <td className="py-2.5 px-3">
                          <span className="font-semibold text-slate-200 block truncate max-w-[180px]">
                            {prod.product_name}
                          </span>
                          <span className="font-mono text-[10px] text-slate-500">{prod.sku}</span>
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-300">
                          {Number(prod.units_sold).toLocaleString()}
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-slate-200">
                          ${Number(prod.total_revenue_usd).toLocaleString()}
                        </td>
                        <td className="py-2.5 px-3 text-right font-bold text-emerald-400">
                          {prod.gross_margin_pct}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* ── Right Column (5/12 width): SBP Realization Exposure & Markets ─ */}
        <div className="lg:col-span-5 space-y-6">
          {/* SBP Chapter XII 120-Day Realization Aging Radar */}
          <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-1.5">
                  <h3 className="text-sm font-bold text-white tracking-tight">
                    SBP 120-Day FX Realization Radar
                  </h3>
                </div>
                <p className="text-xs text-slate-400">
                  Statutory Foreign Exchange Manual Chapter XII receivables aging
                </p>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                120-Day Rule
              </span>
            </div>

            {loading ? (
              <div className="space-y-2 py-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-6 bg-slate-800/60 rounded-xl animate-pulse"></div>
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {/* Total Outstanding Receivables */}
                <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-xl flex items-center justify-between">
                  <span className="text-xs text-slate-400">Total Outstanding Balance:</span>
                  <span className="text-sm font-black text-white">
                    ${Number(sbp?.total_outstanding_usd || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                </div>

                {/* Aging Buckets */}
                <div className="space-y-1.5 text-xs">
                  <div className="flex items-center justify-between p-2 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                    <span className="text-emerald-400 font-medium">0 – 30 Days (Current Safe):</span>
                    <span className="font-mono font-bold text-slate-200">
                      ${Number(sbp?.current_bucket_usd || 0).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-950/60 border border-slate-800">
                    <span className="text-slate-300 font-medium">31 – 60 Days:</span>
                    <span className="font-mono font-bold text-slate-200">
                      ${Number(sbp?.aging_31_60_usd || 0).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-950/60 border border-slate-800">
                    <span className="text-slate-300 font-medium">61 – 90 Days:</span>
                    <span className="font-mono font-bold text-slate-200">
                      ${Number(sbp?.aging_61_90_usd || 0).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                    <span className="text-amber-400 font-medium">91 – 120 Days (SBP Warning):</span>
                    <span className="font-mono font-bold text-amber-300">
                      ${Number(sbp?.aging_91_120_sbp_warning_usd || 0).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2 rounded-lg bg-rose-500/10 border border-rose-500/20">
                    <span className="text-rose-400 font-medium">&gt; 120 Days (Overdue Violation):</span>
                    <span className="font-mono font-bold text-rose-300">
                      ${Number(sbp?.overdue_120_plus_violation_usd || 0).toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* At-Risk Deal Warning List */}
                {sbp?.at_risk_deals && sbp.at_risk_deals.length > 0 && (
                  <div className="pt-2 border-t border-slate-800 space-y-2">
                    <span className="text-[11px] font-bold text-rose-400 uppercase tracking-wider block">
                      ⚠️ Urgent Realization Required ({sbp.at_risk_deals.length} Contracts)
                    </span>
                    <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                      {sbp.at_risk_deals.map((item) => (
                        <div
                          key={item.deal_id}
                          className="p-2.5 bg-rose-500/5 border border-rose-500/20 rounded-xl flex items-center justify-between text-xs"
                        >
                          <div>
                            <Link
                              to={`/deals/${item.deal_id}`}
                              className="font-bold text-slate-200 hover:text-indigo-400 block transition"
                            >
                              {item.reference}
                            </Link>
                            <span className="text-[10px] text-slate-400 truncate block max-w-[140px]">
                              {item.buyer_name}
                            </span>
                          </div>
                          <div className="text-right">
                            <span className="font-mono font-bold text-rose-400 block">
                              ${Number(item.outstanding_balance_usd).toLocaleString()}
                            </span>
                            <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300">
                              {item.days_remaining_sbp < 0
                                ? `${Math.abs(item.days_remaining_sbp)}d Overdue`
                                : `${item.days_remaining_sbp}d Left`}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Destination Export Markets */}
          <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white tracking-tight">
                  Destination Export Markets
                </h3>
                <p className="text-xs text-slate-400">
                  Geographic distribution of export pipeline value
                </p>
              </div>
              <span className="text-xs text-slate-400 font-mono">Global Reach</span>
            </div>

            {loading ? (
              <div className="space-y-2 py-4">
                {[1, 2].map((i) => (
                  <div key={i} className="h-8 bg-slate-800/60 rounded-xl animate-pulse"></div>
                ))}
              </div>
            ) : !analytics?.destination_markets || analytics.destination_markets.length === 0 ? (
              <div className="text-center py-6 text-xs text-slate-500">
                No destination market data available.
              </div>
            ) : (
              <div className="space-y-2.5">
                {analytics.destination_markets.map((market) => (
                  <div
                    key={market.destination_country}
                    className="p-2.5 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-1"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-200">
                        🌍 {market.destination_country}
                      </span>
                      <span className="font-mono font-bold text-indigo-400">
                        ${Number(market.total_value_usd).toLocaleString()} ({market.percentage_of_pipeline}%)
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span>{market.deal_count} export contracts</span>
                      <span>{market.buyer_count} verified buyers</span>
                    </div>
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
