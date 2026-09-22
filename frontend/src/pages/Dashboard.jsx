import { useState, useEffect } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';
import StateBadge, { STATE_CONFIG } from '../components/common/StateBadge';
import MoneyValue from '../components/common/MoneyValue';
import {
  CopilotIcon,
  ArrowTrendingUpIcon,
  AlertTriangleIcon,
  CheckIcon
} from '../components/common/Icons';

export default function Dashboard() {
  const { user, organisation } = useAuth();
  const outletContext = useOutletContext() || {};
  const currencyMode = outletContext.currency || 'USD';

  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [exportNotice, setExportNotice] = useState('');

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const data = await api.get('/analytics/executive-summary');
      setAnalytics(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load executive analytics from DB:', err);
      setError(err.message || 'Failed to load executive summary from database.');
      setAnalytics(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 45000);
    return () => clearInterval(interval);
  }, []);

  const handleDownloadReport = () => {
    if (!analytics) return;
    const blob = new Blob([JSON.stringify(analytics, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Tradeloop_Executive_Report_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setExportNotice('Executive analytics report downloaded successfully.');
    setTimeout(() => setExportNotice(''), 3500);
  };

  const kpis = analytics?.kpis || {};
  const funnel = analytics?.pipeline_funnel || [];
  const totalFunnelVal = funnel.reduce((acc, curr) => acc + (curr.value_usd || 0), 0) || 1;

  return (
    <div className="space-y-5 pb-8 max-w-7xl mx-auto">
      {/* ── Top Header Context Bar ─────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#FFFFFF] border border-[#E4E3DF] p-4 rounded">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-[#1B1D1F] tracking-tight">
              {organisation?.name || 'Pakistani SME Exporter'} — Operations Overview
            </h1>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#E8F2F0] text-[#0C4A40] border border-[#B6D9D2] font-semibold">
              LIVE DATABASE
            </span>
          </div>
          <p className="text-xs text-[#585D63] mt-0.5">
            Deterministic deal tracking, SBP 120-day foreign exchange realization, and Incoterm margin analysis.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadReport}
            disabled={!analytics}
            className="px-3 py-1.5 text-xs font-medium text-[#1B1D1F] bg-[#FFFFFF] hover:bg-[#F7F7F5] border border-[#E4E3DF] rounded transition disabled:opacity-40"
          >
            Export JSON
          </button>
          <Link
            to="/copilot"
            className="px-3 py-1.5 text-xs font-semibold text-white bg-[#0E5E52] hover:bg-[#0C4A40] rounded transition flex items-center gap-1.5"
          >
            <CopilotIcon className="w-3.5 h-3.5 text-white" />
            <span>Open Copilot</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangleIcon className="w-4 h-4 text-red-700 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={fetchAnalytics} className="text-xs font-semibold underline hover:text-red-900">
            Retry
          </button>
        </div>
      )}

      {exportNotice && (
        <div className="p-2.5 bg-[#E8F2F0] border border-[#B6D9D2] text-[#0C4A40] rounded text-xs flex items-center gap-2">
          <CheckIcon className="w-4 h-4" />
          <span>{exportNotice}</span>
        </div>
      )}

      {/* ── KPI Ribbon (5 Compact Stat Cards) ──────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {/* Stat 1: Open Deals */}
        <div className="bg-[#FFFFFF] border border-[#E4E3DF] p-3.5 rounded">
          <div className="text-[11px] font-semibold text-[#848A92] uppercase tracking-wider">
            Open Pipeline Deals
          </div>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-[#1B1D1F]">
              {loading ? '—' : kpis.total_active_deals ?? 0}
            </span>
            <span className="text-[11px] font-medium text-[#0E5E52] flex items-center">
              Active
            </span>
          </div>
          <div className="mt-1 text-[11px] text-[#848A92]">
            Across current contracts
          </div>
        </div>

        {/* Stat 2: Pipeline Value */}
        <div className="bg-[#FFFFFF] border border-[#E4E3DF] p-3.5 rounded">
          <div className="text-[11px] font-semibold text-[#848A92] uppercase tracking-wider">
            Gross Pipeline Value
          </div>
          <div className="mt-1 flex items-baseline justify-between">
            <MoneyValue
              amount={kpis.total_pipeline_value_usd ?? 0}
              currency={currencyMode}
              className="text-lg font-bold"
            />
          </div>
          <div className="mt-1 text-[11px] text-[#848A92]">
            Unsettled export contracts
          </div>
        </div>

        {/* Stat 3: Realized Revenue */}
        <div className="bg-[#FFFFFF] border border-[#E4E3DF] p-3.5 rounded">
          <div className="text-[11px] font-semibold text-[#848A92] uppercase tracking-wider">
            Realized Remittances
          </div>
          <div className="mt-1 flex items-baseline justify-between">
            <MoneyValue
              amount={kpis.total_realized_revenue_usd ?? 0}
              currency={currencyMode}
              className="text-lg font-bold text-[#0E5E52]"
            />
          </div>
          <div className="mt-1 text-[11px] text-[#848A92]">
            {kpis.total_completed_deals ?? 0} closed contracts
          </div>
        </div>

        {/* Stat 4: SBP 120-Day Exposure */}
        <div className="bg-[#FFFFFF] border border-[#E4E3DF] p-3.5 rounded">
          <div className="text-[11px] font-semibold text-[#848A92] uppercase tracking-wider">
            SBP Exposure At Risk
          </div>
          <div className="mt-1 flex items-baseline justify-between">
            <MoneyValue
              amount={kpis.sbp_at_risk_exposure_usd ?? 0}
              currency={currencyMode}
              className={`text-lg font-bold ${(kpis.sbp_at_risk_exposure_usd || 0) > 0 ? 'text-[#B5622B]' : 'text-[#1B1D1F]'}`}
            />
            {(kpis.sbp_at_risk_exposure_usd || 0) > 0 && (
              <span className="text-[11px] font-mono text-[#B5622B] bg-[#FDF3EB] px-1 py-0.2 rounded">
                &gt;90d
              </span>
            )}
          </div>
          <div className="mt-1 text-[11px] text-[#848A92]">
            120-day statutory window
          </div>
        </div>

        {/* Stat 5: Doc Audit Pass Rate */}
        <div className="bg-[#FFFFFF] border border-[#E4E3DF] p-3.5 rounded col-span-2 sm:col-span-1">
          <div className="text-[11px] font-semibold text-[#848A92] uppercase tracking-wider">
            Doc Consistency Rate
          </div>
          <div className="mt-1 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-[#0E5E52]">
              {loading ? '—' : `${kpis.doc_consistency_pass_rate_pct ?? 100}%`}
            </span>
            <span className="text-[11px] font-mono text-[#585D63]">
              Margin {kpis.average_gross_margin_pct ?? 0}%
            </span>
          </div>
          <div className="mt-1 text-[11px] text-[#848A92]">
            Across current shipments
          </div>
        </div>
      </div>

      {/* ── 8-State Pipeline Waterfall ─────────────────────────── */}
      <div className="bg-[#FFFFFF] border border-[#E4E3DF] p-4 rounded">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[#1B1D1F]">
              Deal Pipeline Distribution (8 State Lifecycle)
            </h2>
            <p className="text-[11px] text-[#585D63]">
              Live state distribution of tenant deals in database
            </p>
          </div>
          <Link to="/deals" className="text-xs font-semibold text-[#0E5E52] hover:underline">
            View all deals &rarr;
          </Link>
        </div>

        {/* Horizontal Pipeline Waterfall */}
        {funnel.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
            {funnel.map((item) => {
              const state = item.state.toUpperCase();
              const config = STATE_CONFIG[state] || STATE_CONFIG.INQUIRY;
              const pct = Math.max(4, Math.round(((item.value_usd || 0) / totalFunnelVal) * 100));

              return (
                <div
                  key={state}
                  className="p-2.5 rounded border border-[#E4E3DF] bg-[#FAFAF8] flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10.5px] font-medium text-[#585D63] truncate">
                        {config.label}
                      </span>
                      <span className="font-mono text-xs font-bold text-[#1B1D1F]">
                        {item.count}
                      </span>
                    </div>
                    <div className="font-mono text-[11.5px] font-semibold text-[#1B1D1F]">
                      ${((item.value_usd || 0) / 1000).toFixed(0)}k
                    </div>
                  </div>

                  <div className="mt-2 w-full bg-[#E4E3DF] h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${config.dot}`}
                      style={{ width: `${Math.min(100, pct * 2)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-4 bg-[#FAFAF8] border border-[#E4E3DF] rounded text-center text-xs text-[#848A92]">
            {loading ? 'Calculating pipeline distribution...' : 'No active deal records in database.'}
          </div>
        )}
      </div>

      {/* ── Bottom 2 Columns: Profitability by Incoterm / SKU & Destination Markets ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Table 1: Incoterm & SKU Profitability */}
        <div className="bg-[#FFFFFF] border border-[#E4E3DF] rounded overflow-hidden">
          <div className="px-4 py-3 border-b border-[#E4E3DF] flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[#1B1D1F]">
              Incoterm Realization & Margins
            </h2>
            <span className="text-[11px] font-mono text-[#848A92]">
              ICC Incoterms 2020 Rules
            </span>
          </div>

          {(analytics?.profitability_by_incoterm || []).length > 0 ? (
            <table className="ops-table">
              <thead>
                <tr>
                  <th>Incoterm</th>
                  <th className="text-right">Deals</th>
                  <th className="text-right">Volume</th>
                  <th className="text-right">Gross Margin</th>
                </tr>
              </thead>
              <tbody>
                {analytics.profitability_by_incoterm.map((row) => (
                  <tr key={row.incoterm}>
                    <td className="font-mono font-semibold text-[#1B1D1F]">
                      <span className="px-1.5 py-0.5 rounded bg-[#F0EFEA] border border-[#E4E3DF] text-[11px]">
                        {row.incoterm}
                      </span>
                    </td>
                    <td className="text-right font-mono text-[#585D63]">{row.deal_count}</td>
                    <td className="text-right font-mono">
                      <MoneyValue amount={row.total_revenue_usd} currency={currencyMode} />
                    </td>
                    <td className="text-right">
                      <div className="inline-flex items-center gap-2">
                        <span className="font-mono font-semibold text-[#0E5E52] text-xs">
                          {row.margin_pct}%
                        </span>
                        <div className="w-12 bg-[#E4E3DF] h-1.5 rounded-full overflow-hidden hidden sm:block">
                          <div
                            className="bg-[#0E5E52] h-full rounded-full"
                            style={{ width: `${Math.min(100, row.margin_pct * 3)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-6 text-center text-xs text-[#848A92]">
              {loading ? 'Loading Incoterm metrics...' : 'No Incoterm deal volume recorded in database yet.'}
            </div>
          )}
        </div>

        {/* Table 2: Destination Markets View */}
        <div className="bg-[#FFFFFF] border border-[#E4E3DF] rounded overflow-hidden">
          <div className="px-4 py-3 border-b border-[#E4E3DF] flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[#1B1D1F]">
              Top Export Destinations
            </h2>
            <span className="text-[11px] font-mono text-[#848A92]">
              Ranked by Remittance Value
            </span>
          </div>

          {(analytics?.destination_markets || []).length > 0 ? (
            <table className="ops-table">
              <thead>
                <tr>
                  <th>Market</th>
                  <th className="text-right">Deals</th>
                  <th className="text-right">Volume</th>
                  <th className="text-right">Realization</th>
                </tr>
              </thead>
              <tbody>
                {analytics.destination_markets.map((dest) => (
                  <tr key={dest.country_code}>
                    <td>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-[#F7F7F5] border border-[#E4E3DF] font-semibold text-[#1B1D1F]">
                          {dest.country_code}
                        </span>
                        <span className="font-medium text-[#1B1D1F] text-xs truncate">
                          {dest.name}
                        </span>
                      </div>
                    </td>
                    <td className="text-right font-mono text-[#585D63]">{dest.deals}</td>
                    <td className="text-right font-mono">
                      <MoneyValue amount={dest.volume_usd} currency={currencyMode} />
                    </td>
                    <td className="text-right font-mono text-xs text-[#585D63]">
                      {dest.avg_realization_days} days
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-6 text-center text-xs text-[#848A92]">
              {loading ? 'Loading destination data...' : 'No destination shipments recorded in database yet.'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
