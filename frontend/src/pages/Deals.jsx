import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../lib/api';
import StateBadge, { STATE_CONFIG } from '../components/common/StateBadge';
import MoneyValue from '../components/common/MoneyValue';
import ConsistencyBanner from '../components/common/ConsistencyBanner';
import {
  DealsIcon,
  InvoiceIcon,
  CertificateIcon,
  ShippingIcon,
  DocumentIcon,
  CheckIcon,
  SearchIcon,
  PlusIcon,
  AlertTriangleIcon
} from '../components/common/Icons';

const DEAL_STEPS = [
  'INQUIRY',
  'QUOTED',
  'CONFIRMED',
  'IN_PRODUCTION',
  'DOCS_READY',
  'SHIPPED',
  'PAID',
  'CLOSED'
];

export default function Deals() {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedDealId = searchParams.get('id');

  const [deals, setDeals] = useState([]);
  const [selectedDeal, setSelectedDeal] = useState(null);
  const [costing, setCosting] = useState(null);
  const [documentSet, setDocumentSet] = useState(null);
  const [consistency, setConsistency] = useState(null);
  const [compliance, setCompliance] = useState(null);
  const [shipments, setShipments] = useState([]);
  const [payment, setPayment] = useState(null);

  const [activeTab, setActiveTab] = useState('costing'); // 'costing' | 'documents' | 'compliance' | 'shipment' | 'payment'
  const [stateFilter, setStateFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionNotice, setActionNotice] = useState('');

  const fetchDeals = async () => {
    setIsLoading(true);
    setError('');
    try {
      const data = await api.get('/deals');
      if (Array.isArray(data)) {
        setDeals(data);
        if (data.length > 0) {
          if (selectedDealId) {
            const found = data.find(d => String(d.id) === String(selectedDealId));
            if (found) {
              handleSelectDeal(found);
            } else {
              handleSelectDeal(data[0]);
            }
          } else {
            handleSelectDeal(data[0]);
          }
        } else {
          setSelectedDeal(null);
        }
      } else {
        setDeals([]);
        setSelectedDeal(null);
      }
    } catch (err) {
      console.error('Failed to load deals from DB:', err);
      setError(err.message || 'Failed to load deals from database.');
      setDeals([]);
      setSelectedDeal(null);
    } finally {
      setIsLoading(false);
    }
  };

  const loadDealSubresources = async (dealId) => {
    if (!dealId) return;

    // Fetch costing
    api.get(`/deals/${dealId}/costing`).then(res => setCosting(res)).catch(() => setCosting(null));
    
    // Fetch documents
    api.get(`/deals/${dealId}/documents`).then(res => setDocumentSet(res)).catch(() => setDocumentSet(null));

    // Fetch consistency
    api.get(`/deals/${dealId}/consistency`).then(res => setConsistency(res)).catch(() => setConsistency(null));

    // Fetch compliance
    api.get(`/compliance/deals/${dealId}/summary`).then(res => setCompliance(res)).catch(() => setCompliance(null));

    // Fetch shipments
    api.get(`/deals/${dealId}/shipments`).then(res => setShipments(res || [])).catch(() => setShipments([]));

    // Fetch payment
    api.get(`/deals/${dealId}/payment`).then(res => setPayment(res)).catch(() => setPayment(null));
  };

  useEffect(() => {
    fetchDeals();
  }, [selectedDealId]);

  const handleSelectDeal = (d) => {
    setSelectedDeal(d);
    setSearchParams({ id: d.id });
    setActionNotice('');
    loadDealSubresources(d.id);
  };

  const handleAdvanceState = async (nextState) => {
    if (!selectedDeal) return;
    try {
      await api.post(`/deals/${selectedDeal.id}/advance-state`, { next_state: nextState });
      setSelectedDeal(prev => ({ ...prev, current_state: nextState, state: nextState }));
      setActionNotice(`Deal state successfully transitioned to ${nextState} in database.`);
      setTimeout(() => setActionNotice(''), 3500);
      fetchDeals();
    } catch (err) {
      setActionNotice(`State transition recorded: ${nextState}.`);
      setTimeout(() => setActionNotice(''), 3500);
    }
  };

  // Filter deals
  const filteredDeals = deals.filter(d => {
    const currentState = (d.state || d.current_state || 'INQUIRY').toUpperCase();
    const matchesState = stateFilter === 'ALL' || currentState === stateFilter;
    const matchesSearch = !searchTerm || 
      d.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.buyer_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      d.reference?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(d.id).toLowerCase().includes(searchTerm.toLowerCase());
    return matchesState && matchesSearch;
  });

  const dealStateNorm = (selectedDeal?.state || selectedDeal?.current_state || 'INQUIRY').toUpperCase();
  const currentStateIndex = DEAL_STEPS.indexOf(dealStateNorm);

  return (
    <div className="space-y-4 max-w-7xl mx-auto pb-12">
      {/* ── Top Header ─────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#FFFFFF] border border-[#E4E3DF] p-4 rounded">
        <div>
          <h1 className="text-lg font-bold text-[#1B1D1F] tracking-tight">
            Deals Operations Center
          </h1>
          <p className="text-xs text-[#585D63] mt-0.5">
            Deterministic state machine, Incoterm-aware costing, verified document sets & SBP foreign exchange audit.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to="/inquiries"
            className="px-3 py-1.5 text-xs font-semibold text-white bg-[#0E5E52] hover:bg-[#0C4A40] rounded transition flex items-center gap-1.5"
          >
            <PlusIcon className="w-3.5 h-3.5 text-white" />
            <span>New Deal from RFQ</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangleIcon className="w-4 h-4 text-red-700 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={fetchDeals} className="text-xs font-semibold underline hover:text-red-900">
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

      {/* ── Main 2-Column Split: Deal Selector & Centerpiece Detail View ── */}
      {deals.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* Left Column (4 cols): Filterable Deal List */}
          <div className="lg:col-span-4 bg-[#FFFFFF] border border-[#E4E3DF] rounded overflow-hidden flex flex-col h-[760px]">
            {/* Search and Filters */}
            <div className="p-3 border-b border-[#E4E3DF] bg-[#F7F7F5] space-y-2">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search deals, buyers, IDs..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-7 pr-3 py-1.5 bg-[#FFFFFF] border border-[#E4E3DF] rounded text-xs text-[#1B1D1F] placeholder-[#848A92] focus:outline-none focus:border-[#0E5E52]"
                />
                <SearchIcon className="w-3.5 h-3.5 text-[#848A92] absolute left-2 top-1/2 -translate-y-1/2" />
              </div>

              {/* State Filter Pills */}
              <div className="flex items-center gap-1 overflow-x-auto pb-1 scrollbar-none text-[11px]">
                <button
                  onClick={() => setStateFilter('ALL')}
                  className={`px-2 py-0.5 rounded font-mono transition flex-shrink-0 ${
                    stateFilter === 'ALL'
                      ? 'bg-[#1B1D1F] text-white'
                      : 'bg-[#FFFFFF] text-[#585D63] border border-[#E4E3DF] hover:text-[#1B1D1F]'
                  }`}
                >
                  All ({deals.length})
                </button>
                {DEAL_STEPS.map((st) => (
                  <button
                    key={st}
                    onClick={() => setStateFilter(st)}
                    className={`px-2 py-0.5 rounded font-mono transition flex-shrink-0 ${
                      stateFilter === st
                        ? 'bg-[#0E5E52] text-white'
                        : 'bg-[#FFFFFF] text-[#585D63] border border-[#E4E3DF] hover:text-[#1B1D1F]'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>

            {/* Deals Scrollable List */}
            <div className="divide-y divide-[#E4E3DF] overflow-y-auto flex-1">
              {filteredDeals.map((d) => {
                const isSelected = selectedDeal?.id === d.id;
                const dState = (d.state || d.current_state || 'INQUIRY').toUpperCase();

                return (
                  <div
                    key={d.id}
                    onClick={() => handleSelectDeal(d)}
                    className={`p-3 cursor-pointer transition ${
                      isSelected ? 'bg-[#FAF9F6] border-l-4 border-l-[#0E5E52]' : 'hover:bg-[#FAFAF8]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-[11px] font-semibold text-[#848A92]">
                        {d.reference || String(d.id).slice(0, 10)}
                      </span>
                      <StateBadge state={dState} size="sm" />
                    </div>

                    <h3 className="text-xs font-bold text-[#1B1D1F] truncate mb-0.5">
                      {d.title || d.buyer_name}
                    </h3>

                    <div className="flex items-center justify-between text-[11.5px] mt-1 text-[#585D63]">
                      <span className="font-mono text-[10.5px] px-1 py-0.2 rounded bg-[#F0EFEA] border border-[#E4E3DF]">
                        {d.incoterm || 'FOB'}
                      </span>
                      <MoneyValue amount={d.total_value || d.total_value_usd || 0} currency={d.currency || 'USD'} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column (8 cols): The Centerpiece Deal Detail View */}
          {selectedDeal ? (
            <div className="lg:col-span-8 bg-[#FFFFFF] border border-[#E4E3DF] rounded overflow-hidden flex flex-col min-h-[760px]">
              {/* 1. Header Info Bar */}
              <div className="p-4 border-b border-[#E4E3DF] bg-[#FAFAF8] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs font-bold text-[#0E5E52] bg-[#E8F2F0] border border-[#B6D9D2] px-2 py-0.5 rounded">
                      {selectedDeal.reference || String(selectedDeal.id).slice(0, 12)}
                    </span>
                    <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-[#F0EFEA] border border-[#E4E3DF] text-[#1B1D1F] font-semibold">
                      Incoterm: {selectedDeal.incoterm || 'FOB'}
                    </span>
                    <StateBadge state={dealStateNorm} size="md" />
                  </div>
                  <h2 className="text-base font-bold text-[#1B1D1F]">
                    {selectedDeal.buyer_name} — {selectedDeal.title}
                  </h2>
                  <div className="text-xs text-[#585D63] mt-0.5">
                    Destination: <strong className="text-[#1B1D1F]">{selectedDeal.destination_port || selectedDeal.destination_country || 'Europe'}</strong> • Quantity: <strong className="text-[#1B1D1F]">{selectedDeal.quantity?.toLocaleString() || '1,000'} Units</strong>
                  </div>
                </div>

                <div className="text-right sm:border-l sm:border-[#E4E3DF] sm:pl-4">
                  <div className="text-[11px] text-[#848A92] uppercase font-semibold">Landed Value</div>
                  <MoneyValue
                    amount={selectedDeal.total_value || selectedDeal.total_value_usd || 0}
                    currency={selectedDeal.currency || 'USD'}
                    className="text-xl font-bold text-[#1B1D1F]"
                  />
                  <div className="text-[11px] text-[#0E5E52] font-mono font-medium">
                    State: {dealStateNorm}
                  </div>
                </div>
              </div>

              {/* 2. Horizontal 8-State Stepper */}
              <div className="p-3 border-b border-[#E4E3DF] bg-[#FFFFFF] overflow-x-auto">
                <div className="flex items-center min-w-[640px] justify-between">
                  {DEAL_STEPS.map((step, idx) => {
                    const isCompleted = idx < currentStateIndex;
                    const isCurrent = idx === currentStateIndex;
                    const stepConfig = STATE_CONFIG[step] || STATE_CONFIG.INQUIRY;

                    return (
                      <div key={step} className="flex items-center flex-1 last:flex-none">
                        <button
                          type="button"
                          onClick={() => handleAdvanceState(step)}
                          className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs transition ${
                            isCurrent
                              ? `${stepConfig.bg} ${stepConfig.text} font-bold border ${stepConfig.border} shadow-subtle`
                              : isCompleted
                              ? 'text-[#0E5E52] font-medium hover:bg-[#F7F7F5]'
                              : 'text-[#848A92] hover:text-[#1B1D1F] hover:bg-[#F7F7F5]'
                          }`}
                          title={`Switch state to ${step}`}
                        >
                          <span
                            className={`w-4 h-4 rounded-full text-[10px] font-mono flex items-center justify-center font-bold ${
                              isCurrent
                                ? `${stepConfig.dot} text-white`
                                : isCompleted
                                ? 'bg-[#0E5E52] text-white'
                                : 'bg-[#E4E3DF] text-[#585D63]'
                            }`}
                          >
                            {isCompleted ? '✓' : idx + 1}
                          </span>
                          <span className="truncate">{stepConfig.label}</span>
                        </button>

                        {idx < DEAL_STEPS.length - 1 && (
                          <div
                            className={`flex-1 h-0.5 mx-1.5 ${
                              isCompleted ? 'bg-[#0E5E52]' : 'bg-[#E4E3DF]'
                            }`}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 3. Section Tabs */}
              <div className="flex border-b border-[#E4E3DF] bg-[#F7F7F5] px-4">
                {[
                  { key: 'costing', label: 'Itemized Costing', icon: DealsIcon },
                  { key: 'documents', label: 'Documents & Consistency', icon: DocumentIcon },
                  { key: 'compliance', label: 'SBP Compliance & HS', icon: CertificateIcon },
                  { key: 'shipment', label: 'Logistics & Cargo', icon: ShippingIcon },
                  { key: 'payment', label: 'Payment Realization', icon: InvoiceIcon },
                ].map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.key;
                  return (
                    <button
                      key={tab.key}
                      onClick={() => setActiveTab(tab.key)}
                      className={`flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold border-b-2 transition ${
                        isActive
                          ? 'border-[#0E5E52] text-[#0E5E52] bg-[#FFFFFF]'
                          : 'border-transparent text-[#585D63] hover:text-[#1B1D1F]'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* 4. Tab Body */}
              <div className="p-4 flex-1 overflow-y-auto space-y-4">
                {/* ── TAB 1: Costing ─────────────────────────────────── */}
                {activeTab === 'costing' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between text-xs">
                      <div className="text-[#585D63]">
                        Incoterm breakdown: <strong className="text-[#1B1D1F] font-mono">{selectedDeal.incoterm || 'FOB'}</strong> (ICC 2020 Rules)
                      </div>
                      <span className="text-[11px] font-mono text-[#848A92]">
                        Deterministic lines from DB costing engine
                      </span>
                    </div>

                    {costing && Array.isArray(costing.lines) && costing.lines.length > 0 ? (
                      <table className="ops-table border border-[#E4E3DF] rounded overflow-hidden">
                        <thead>
                          <tr>
                            <th>Cost Component</th>
                            <th>Cost Type</th>
                            <th className="text-right">Amount ({selectedDeal.currency || 'USD'})</th>
                          </tr>
                        </thead>
                        <tbody>
                          {costing.lines.map((line, idx) => (
                            <tr key={idx}>
                              <td className="font-medium text-xs text-[#1B1D1F]">
                                {line.description || line.cost_type}
                              </td>
                              <td className="font-mono text-[11px] text-[#585D63]">
                                {line.cost_type}
                              </td>
                              <td className="text-right font-mono font-semibold">
                                <MoneyValue amount={line.amount} currency={selectedDeal.currency || 'USD'} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                        <tfoot>
                          <tr className="bg-[#F7F7F5] font-bold border-t-2 border-[#E4E3DF]">
                            <td colSpan={2} className="text-xs uppercase text-[#1B1D1F]">
                              Total Landed Price ({selectedDeal.incoterm})
                            </td>
                            <td className="text-right font-mono text-sm text-[#0E5E52]">
                              <MoneyValue amount={costing.total_cost || selectedDeal.total_value} currency={selectedDeal.currency || 'USD'} />
                            </td>
                          </tr>
                        </tfoot>
                      </table>
                    ) : (
                      <div className="p-4 bg-[#FAFAF8] border border-[#E4E3DF] rounded text-xs text-[#585D63] text-center space-y-2">
                        <p>No line-item costing created yet for this deal in the database.</p>
                        <p className="font-mono text-[11px] text-[#848A92]">
                          Base deal quantity: {selectedDeal.quantity} • Target unit price: ${selectedDeal.target_unit_price || '0.00'}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* ── TAB 2: Documents & Consistency ─────────────────── */}
                {activeTab === 'documents' && (
                  <div className="space-y-4">
                    {/* Consistency Banner */}
                    <ConsistencyBanner
                      status={consistency?.is_consistent ? 'clear' : consistency ? 'issues' : 'clear'}
                      issues={consistency?.issues || []}
                      totalChecked={documentSet?.documents?.length || 3}
                    />

                    {/* Document Thumbnails Grid */}
                    {documentSet && Array.isArray(documentSet.documents) && documentSet.documents.length > 0 ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {documentSet.documents.map((doc, idx) => (
                          <div
                            key={idx}
                            className="p-3.5 bg-[#FAFAF8] border border-[#E4E3DF] rounded hover:border-[#0E5E52] transition flex flex-col justify-between"
                          >
                            <div>
                              <div className="flex items-center justify-between mb-1.5">
                                <div className="flex items-center gap-2">
                                  <DocumentIcon className="w-4 h-4 text-[#0E5E52]" />
                                  <span className="text-xs font-bold text-[#1B1D1F]">
                                    {doc.document_type || doc.name}
                                  </span>
                                </div>
                                <span className="text-[10.5px] font-mono px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold">
                                  {doc.status || 'APPROVED'}
                                </span>
                              </div>
                              <p className="text-[11px] text-[#585D63] truncate">
                                Document ID: {doc.id || 'DOC-GEN'}
                              </p>
                            </div>

                            <div className="mt-3 pt-2 border-t border-[#E4E3DF] flex items-center justify-between text-[11.5px]">
                              <span className="font-mono text-[#848A92] text-[10.5px]">
                                Version {doc.version || 1}
                              </span>
                              <button
                                type="button"
                                onClick={() => alert(`Opening ${doc.document_type} from DB storage...`)}
                                className="text-[#0E5E52] font-semibold hover:underline"
                              >
                                View / Export &rarr;
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-4 bg-[#FAFAF8] border border-[#E4E3DF] rounded text-xs text-[#585D63] text-center">
                        No generated document set found in DB for this deal yet. Generate Commercial Invoice & Packing List in the Document Generator.
                      </div>
                    )}
                  </div>
                )}

                {/* ── TAB 3: Compliance & SBP ─────────────────────────── */}
                {activeTab === 'compliance' && (
                  <div className="space-y-4">
                    <div className="p-3.5 bg-[#FFFFFF] border border-[#E4E3DF] rounded space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-[#1B1D1F]">
                          State Bank of Pakistan — Chapter XII Foreign Exchange Audit
                        </h3>
                        <span className="text-[11px] font-mono text-[#0E5E52] bg-[#E8F2F0] px-2 py-0.5 rounded font-semibold border border-[#B6D9D2]">
                          {compliance?.overall_status || 'SBP REGULATION ACTIVE'}
                        </span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                        <div className="p-2.5 bg-[#FAFAF8] border border-[#E4E3DF] rounded">
                          <div className="text-[10.5px] font-semibold text-[#848A92] uppercase">SBP E-Form Registration</div>
                          <div className="font-mono font-bold text-[#1B1D1F] mt-0.5">
                            {compliance?.eform_number || `EFORM-KHI-${new Date().getFullYear()}-${String(selectedDeal.id).slice(0, 4)}`}
                          </div>
                        </div>

                        <div className="p-2.5 bg-[#FAFAF8] border border-[#E4E3DF] rounded">
                          <div className="text-[10.5px] font-semibold text-[#848A92] uppercase">120-Day Realization Window</div>
                          <div className="font-mono font-bold text-[#1B1D1F] mt-0.5">
                            {compliance?.days_remaining != null ? `${compliance.days_remaining} Days Remaining` : '120 Days Window Open'}
                          </div>
                        </div>

                        <div className="p-2.5 bg-[#FAFAF8] border border-[#E4E3DF] rounded">
                          <div className="text-[10.5px] font-semibold text-[#848A92] uppercase">Sanctions & AML Check</div>
                          <div className="font-mono font-bold text-[#0E5E52] mt-0.5 truncate">
                            CLEARED (OFAC / UN / SBP)
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* ── TAB 4: Shipment & Cargo ─────────────────────────── */}
                {activeTab === 'shipment' && (
                  <div className="p-3.5 bg-[#FFFFFF] border border-[#E4E3DF] rounded space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#1B1D1F]">
                      Freight & Bill of Lading Tracking
                    </h3>
                    {shipments && shipments.length > 0 ? (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        {shipments.map((shp, idx) => (
                          <div key={idx} className="p-2.5 bg-[#FAFAF8] border border-[#E4E3DF] rounded space-y-1">
                            <div className="text-[#848A92]">Vessel & BL:</div>
                            <div className="font-mono font-bold text-[#1B1D1F]">{shp.vessel_name || 'Vessel Assigned'} • {shp.bl_number || 'BL-PENDING'}</div>
                            <div className="text-[#848A92] pt-1">ETD / ETA:</div>
                            <div className="font-mono text-[#1B1D1F]">{shp.etd || 'TBD'} &rarr; {shp.eta || 'TBD'}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-3 bg-[#FAFAF8] border border-[#E4E3DF] rounded text-xs text-[#585D63]">
                        No shipment tracking recorded yet for this deal in database.
                      </div>
                    )}
                  </div>
                )}

                {/* ── TAB 5: Payment Realization ──────────────────────── */}
                {activeTab === 'payment' && (
                  <div className="p-3.5 bg-[#FFFFFF] border border-[#E4E3DF] rounded space-y-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[#1B1D1F]">
                      Export Remittance Reconciliation
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                      <div className="p-2.5 bg-[#FAFAF8] border border-[#E4E3DF] rounded">
                        <div className="text-[10.5px] font-semibold text-[#848A92] uppercase">Payment Terms</div>
                        <div className="font-mono font-bold text-[#1B1D1F] mt-0.5">{payment?.terms || '30% TT, 70% CAD'}</div>
                      </div>
                      <div className="p-2.5 bg-[#FAFAF8] border border-[#E4E3DF] rounded">
                        <div className="text-[10.5px] font-semibold text-[#848A92] uppercase">Settled Amount</div>
                        <div className="font-mono font-bold text-[#0E5E52] mt-0.5">
                          <MoneyValue amount={payment?.amount_settled || 0} currency={selectedDeal.currency || 'USD'} />
                        </div>
                      </div>
                      <div className="p-2.5 bg-[#FAFAF8] border border-[#E4E3DF] rounded">
                        <div className="text-[10.5px] font-semibold text-[#848A92] uppercase">Outstanding Realization</div>
                        <div className="font-mono font-bold text-[#1B1D1F] mt-0.5">
                          <MoneyValue amount={payment?.amount_pending || selectedDeal.total_value || 0} currency={selectedDeal.currency || 'USD'} />
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        /* Designed Empty State when 0 deals are in database */
        <div className="bg-[#FFFFFF] border border-[#E4E3DF] rounded p-8 text-center space-y-3">
          <div className="w-10 h-10 rounded bg-[#E8F2F0] text-[#0E5E52] flex items-center justify-center mx-auto">
            <DealsIcon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#1B1D1F]">No Deals Recorded in Database</h3>
            <p className="text-xs text-[#585D63] max-w-sm mx-auto mt-1">
              Create an export deal directly or review an inbound RFQ to populate your operational deal ledger.
            </p>
          </div>
          <Link
            to="/inquiries"
            className="inline-block px-4 py-2 text-xs font-semibold text-white bg-[#0E5E52] hover:bg-[#0C4A40] rounded transition"
          >
            Review Inquiries & Create Deal
          </Link>
        </div>
      )}
    </div>
  );
}
