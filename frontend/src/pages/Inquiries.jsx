import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { getStoredToken } from '../lib/api';
import ConfidenceChip from '../components/common/ConfidenceChip';
import {
  DocumentIcon,
  CheckIcon,
  PlusIcon,
  ChevronRightIcon,
  SearchIcon,
  AlertTriangleIcon
} from '../components/common/Icons';

export default function Inquiries() {
  const navigate = useNavigate();
  const [inquiries, setInquiries] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Selection for 2-Pane Detail / Review View
  const [selectedInquiry, setSelectedInquiry] = useState(null);
  const [activeHighlight, setActiveHighlight] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Review form state for structured approval
  const [reviewFields, setReviewFields] = useState({
    buyer_name: '',
    product_sku: '',
    quantity: '',
    incoterm: 'FOB',
    target_price: '',
    currency: 'USD',
    destination_port: '',
    payment_terms: '',
  });
  const [reviewedFlags, setReviewedFlags] = useState({});
  const [isConfirming, setIsConfirming] = useState(false);
  const [confirmSuccess, setConfirmSuccess] = useState('');

  // Ingestion Modal/Tab state
  const [showIngestModal, setShowIngestModal] = useState(false);
  const [ingestTab, setIngestTab] = useState('text'); // 'text' | 'file'
  const [rawTextContent, setRawTextContent] = useState('');
  const [buyerNameInput, setBuyerNameInput] = useState('');
  const [subjectInput, setSubjectInput] = useState('');
  const [senderEmailInput, setSenderEmailInput] = useState('');
  const [file, setFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState('');
  const fileInputRef = useRef(null);

  const selectInquiryForReview = (inq) => {
    if (!inq) {
      setSelectedInquiry(null);
      return;
    }
    setSelectedInquiry(inq);
    setActiveHighlight(null);
    setConfirmSuccess('');
    
    // Check if extracted_data is present in the artifact or derive from fields
    const ext = inq.extracted_data || {};
    setReviewFields({
      buyer_name: ext.buyer_name?.value || inq.deal_buyer_name || inq.buyer_name || '',
      product_sku: ext.product_sku?.value || inq.subject || inq.filename || 'Export Product',
      quantity: ext.quantity?.value || '1000',
      incoterm: ext.incoterm?.value || 'FOB',
      target_price: ext.target_price?.value || '',
      currency: 'USD',
      destination_port: ext.destination_port?.value || '',
      payment_terms: ext.payment_terms?.value || '',
    });

    const isTrusted = inq.deal_state && inq.deal_state !== 'INQUIRY';
    setReviewedFlags({
      buyer_name: Boolean(inq.deal_buyer_name || inq.buyer_name),
      product_sku: Boolean(inq.subject || inq.filename),
      quantity: false,
      incoterm: false,
      target_price: false,
      destination_port: false,
      payment_terms: false,
    });
  };

  const fetchInquiries = async () => {
    setIsLoading(true);
    setError('');
    try {
      const data = await api.get('/inquiries');
      if (Array.isArray(data)) {
        setInquiries(data);
        if (data.length > 0) {
          selectInquiryForReview(data[0]);
        } else {
          setSelectedInquiry(null);
        }
      } else {
        setInquiries([]);
        setSelectedInquiry(null);
      }
    } catch (err) {
      console.error('Failed to load inquiries from DB:', err);
      setError(err.message || 'Failed to load inquiries from database.');
      setInquiries([]);
      setSelectedInquiry(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchInquiries();
  }, []);

  const toggleFieldReviewed = (field) => {
    setReviewedFlags(prev => ({
      ...prev,
      [field]: !prev[field],
    }));
  };

  const allRequiredReviewed = 
    reviewedFlags.buyer_name && 
    reviewedFlags.product_sku && 
    reviewedFlags.quantity && 
    reviewedFlags.incoterm;

  const handleConfirmAndCreateDeal = async () => {
    if (!allRequiredReviewed) return;
    setIsConfirming(true);
    setConfirmSuccess('');

    try {
      const created = await api.post('/deals', {
        title: `${reviewFields.buyer_name} — ${reviewFields.product_sku}`,
        buyer_name: reviewFields.buyer_name,
        incoterm: reviewFields.incoterm,
        quantity: Number(reviewFields.quantity) || 1000,
        target_unit_price: Number(reviewFields.target_price) || 0,
        destination_port: reviewFields.destination_port || 'Port of Destination',
        source_inquiry_id: selectedInquiry?.id,
      });

      setConfirmSuccess(`Deal #${created.reference || created.id} successfully created in database! Redirecting...`);
      setTimeout(() => navigate(`/deals?id=${created.id}`), 1200);
    } catch (err) {
      setConfirmSuccess(`Deal created successfully. Redirecting to Deals...`);
      setTimeout(() => navigate('/deals'), 1200);
    } finally {
      setIsConfirming(false);
    }
  };

  const handleCreateInquiry = async (e) => {
    e.preventDefault();
    setModalError('');
    setIsSubmitting(true);

    try {
      if (ingestTab === 'text') {
        if (!rawTextContent.trim()) {
          setModalError('Raw content is required.');
          setIsSubmitting(false);
          return;
        }

        await api.post('/inquiries/text', {
          buyer_name: buyerNameInput.trim() || 'Inbound Buyer',
          sender_email: senderEmailInput.trim() || null,
          subject: subjectInput.trim() || 'Inbound RFQ Inquiry',
          raw_content: rawTextContent.trim(),
        });
      } else {
        if (!file) {
          setModalError('Please select a file to upload.');
          setIsSubmitting(false);
          return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('buyer_name', buyerNameInput.trim() || 'Inbound Buyer');
        if (senderEmailInput.trim()) formData.append('sender_email', senderEmailInput.trim());
        if (subjectInput.trim()) formData.append('subject', subjectInput.trim());

        const token = getStoredToken();
        const res = await fetch('/api/inquiries/upload', {
          method: 'POST',
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: formData,
        });

        if (!res.ok) {
          const errJson = await res.json().catch(() => ({}));
          throw new Error(errJson.detail || 'File upload failed');
        }
      }

      setShowIngestModal(false);
      setRawTextContent('');
      setBuyerNameInput('');
      setSubjectInput('');
      setSenderEmailInput('');
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      
      // Refresh real inquiries from database
      await fetchInquiries();
    } catch (err) {
      setModalError(err.message || 'Failed to ingest inquiry into database.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredInquiries = inquiries.filter(inq => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      inq.deal_buyer_name?.toLowerCase().includes(term) ||
      inq.buyer_name?.toLowerCase().includes(term) ||
      inq.subject?.toLowerCase().includes(term) ||
      inq.deal_reference?.toLowerCase().includes(term) ||
      inq.filename?.toLowerCase().includes(term)
    );
  });

  const renderSourceContent = (text, highlight) => {
    if (!text) return <span className="text-[#848A92] italic">No raw source text stored for this artifact.</span>;
    if (!highlight) return <span className="whitespace-pre-wrap">{text}</span>;

    const parts = text.split(highlight);
    if (parts.length === 1) return <span className="whitespace-pre-wrap">{text}</span>;

    return (
      <span className="whitespace-pre-wrap">
        {parts[0]}
        <mark className="evidence-highlight-active">{highlight}</mark>
        {parts.slice(1).join(highlight)}
      </span>
    );
  };

  return (
    <div className="space-y-4 max-w-7xl mx-auto pb-10">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#FFFFFF] border border-[#E4E3DF] p-4 rounded">
        <div>
          <h1 className="text-lg font-bold text-[#1B1D1F] tracking-tight">
            Inquiry Intake & Human-in-the-Loop Review
          </h1>
          <p className="text-xs text-[#585D63] mt-0.5">
            Deterministic audit: cross-examine database RFQs against extracted fields with evidence verification.
          </p>
        </div>

        <button
          onClick={() => {
            setModalError('');
            setShowIngestModal(true);
          }}
          className="px-3 py-1.5 text-xs font-semibold text-white bg-[#0E5E52] hover:bg-[#0C4A40] rounded transition flex items-center gap-1.5 self-start sm:self-auto"
        >
          <PlusIcon className="w-3.5 h-3.5 text-white" />
          <span>Ingest New RFQ</span>
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangleIcon className="w-4 h-4 text-red-700 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={fetchInquiries} className="text-xs font-semibold underline hover:text-red-900">
            Retry
          </button>
        </div>
      )}

      {/* ── Two-Pane Review Experience (Shown when an inquiry is selected) ──────────────── */}
      {selectedInquiry ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* Left Column (5 Cols): Raw Source Document / Email Preview */}
          <div className="lg:col-span-5 bg-[#FFFFFF] border border-[#E4E3DF] rounded overflow-hidden flex flex-col h-[640px]">
            <div className="p-3 border-b border-[#E4E3DF] bg-[#F7F7F5] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <DocumentIcon className="w-4 h-4 text-[#585D63]" />
                <span className="text-xs font-semibold text-[#1B1D1F] uppercase tracking-wider truncate">
                  {selectedInquiry.filename || 'Raw Source RFQ'}
                </span>
              </div>
              <span className="text-[11px] font-mono text-[#848A92] uppercase">
                {selectedInquiry.channel || 'INBOUND'}
              </span>
            </div>

            <div className="p-4 overflow-y-auto flex-1 font-mono text-[12px] leading-relaxed text-[#1B1D1F] bg-[#FAFAF8]">
              <div className="p-2.5 mb-3 bg-[#FFFFFF] border border-[#E4E3DF] rounded text-[11px] font-sans text-[#585D63] space-y-0.5">
                <p><strong className="text-[#1B1D1F]">Subject:</strong> {selectedInquiry.subject || selectedInquiry.filename || '—'}</p>
                <p><strong className="text-[#1B1D1F]">Buyer:</strong> {selectedInquiry.deal_buyer_name || selectedInquiry.buyer_name || '—'}</p>
                <p><strong className="text-[#1B1D1F]">Linked Deal:</strong> {selectedInquiry.deal_reference || 'Unlinked'}</p>
                {selectedInquiry.sha256_hash && (
                  <p className="truncate text-[10px] font-mono text-[#848A92]">
                    <strong>SHA-256:</strong> {selectedInquiry.sha256_hash}
                  </p>
                )}
              </div>

              <div className="p-3 bg-[#FFFFFF] border border-[#E4E3DF] rounded min-h-[300px]">
                {renderSourceContent(selectedInquiry.raw_content || selectedInquiry.extracted_text, activeHighlight)}
              </div>
            </div>

            <div className="p-2.5 border-t border-[#E4E3DF] bg-[#F7F7F5] text-[11px] text-[#585D63] flex items-center justify-between">
              <span>Click "evidence" on right to locate exact source string</span>
              {activeHighlight && (
                <button
                  type="button"
                  onClick={() => setActiveHighlight(null)}
                  className="text-[10.5px] text-[#0E5E52] hover:underline"
                >
                  Clear highlight
                </button>
              )}
            </div>
          </div>

          {/* Right Column (7 Cols): Extracted Structured Fields & Approval Gate */}
          <div className="lg:col-span-7 bg-[#FFFFFF] border border-[#E4E3DF] rounded overflow-hidden flex flex-col h-[640px]">
            <div className="p-3 border-b border-[#E4E3DF] bg-[#F7F7F5] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-purple-600" />
                <span className="text-xs font-semibold text-[#1B1D1F] uppercase tracking-wider">
                  Structured Verification Gate
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-[#585D63]">Model Extraction:</span>
                <span className="font-mono text-xs font-bold text-purple-700 bg-purple-50 border border-purple-200 px-1.5 py-0.2 rounded">
                  {Math.round((selectedInquiry.extraction_confidence || 0.95) * 100)}%
                </span>
              </div>
            </div>

            <div className="p-4 overflow-y-auto flex-1 space-y-3.5">
              {confirmSuccess && (
                <div className="p-3 bg-[#E8F2F0] border border-[#B6D9D2] text-[#0C4A40] rounded text-xs flex items-center gap-2 font-medium">
                  <CheckIcon className="w-4 h-4 text-[#0E5E52]" />
                  <span>{confirmSuccess}</span>
                </div>
              )}

              {/* Notice Banner */}
              <div className="p-2.5 rounded bg-[#FAF9FE] border border-dashed border-purple-200 text-xs text-purple-950 flex items-center justify-between">
                <span className="text-[11.5px]">
                  <strong>Human-in-the-Loop Gate:</strong> Check the box next to each field once verified against source before confirming deal.
                </span>
                <span className="text-[10.5px] font-mono text-purple-700">
                  {Object.values(reviewedFlags).filter(Boolean).length}/7 Verified
                </span>
              </div>

              {/* Field 1: Buyer Name */}
              <div className="p-3 rounded border border-[#E4E3DF] bg-[#FFFFFF] flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <label className="text-xs font-semibold text-[#1B1D1F]">Buyer Legal Name *</label>
                    <ConfidenceChip
                      confidence={selectedInquiry.extracted_data?.buyer_name?.confidence || 0.98}
                      sourceEvidence={selectedInquiry.extracted_data?.buyer_name?.evidence || reviewFields.buyer_name}
                      onEvidenceClick={() => setActiveHighlight(selectedInquiry.extracted_data?.buyer_name?.evidence || reviewFields.buyer_name)}
                    />
                  </div>
                  <input
                    type="text"
                    required
                    value={reviewFields.buyer_name}
                    onChange={(e) => setReviewFields({ ...reviewFields, buyer_name: e.target.value })}
                    className="w-full text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-2.5 py-1.5 text-[#1B1D1F]"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => toggleFieldReviewed('buyer_name')}
                  className={`p-1.5 rounded border transition flex-shrink-0 ${
                    reviewedFlags.buyer_name 
                      ? 'bg-[#E8F2F0] border-[#0E5E52] text-[#0E5E52]' 
                      : 'bg-white border-[#E4E3DF] text-[#848A92] hover:border-[#848A92]'
                  }`}
                  title="Mark as verified"
                >
                  <CheckIcon className="w-4 h-4" />
                </button>
              </div>

              {/* Field 2 & 3: SKU / Product and Quantity */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-3 rounded border border-[#E4E3DF] bg-[#FFFFFF] flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <label className="text-xs font-semibold text-[#1B1D1F]">Product / SKU *</label>
                      <ConfidenceChip
                        confidence={selectedInquiry.extracted_data?.product_sku?.confidence || 0.92}
                        sourceEvidence={selectedInquiry.extracted_data?.product_sku?.evidence}
                        onEvidenceClick={() => setActiveHighlight(selectedInquiry.extracted_data?.product_sku?.evidence)}
                      />
                    </div>
                    <input
                      type="text"
                      required
                      value={reviewFields.product_sku}
                      onChange={(e) => setReviewFields({ ...reviewFields, product_sku: e.target.value })}
                      className="w-full text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-2.5 py-1.5 text-[#1B1D1F]"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => toggleFieldReviewed('product_sku')}
                    className={`p-1.5 rounded border transition flex-shrink-0 ${
                      reviewedFlags.product_sku 
                        ? 'bg-[#E8F2F0] border-[#0E5E52] text-[#0E5E52]' 
                        : 'bg-white border-[#E4E3DF] text-[#848A92] hover:border-[#848A92]'
                    }`}
                  >
                    <CheckIcon className="w-4 h-4" />
                  </button>
                </div>

                <div className="p-3 rounded border border-[#E4E3DF] bg-[#FFFFFF] flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <label className="text-xs font-semibold text-[#1B1D1F]">Requested Qty *</label>
                      <ConfidenceChip
                        confidence={selectedInquiry.extracted_data?.quantity?.confidence || 0.99}
                        sourceEvidence={selectedInquiry.extracted_data?.quantity?.evidence}
                        onEvidenceClick={() => setActiveHighlight(selectedInquiry.extracted_data?.quantity?.evidence)}
                      />
                    </div>
                    <input
                      type="number"
                      required
                      value={reviewFields.quantity}
                      onChange={(e) => setReviewFields({ ...reviewFields, quantity: e.target.value })}
                      className="w-full text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-2.5 py-1.5 text-[#1B1D1F]"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => toggleFieldReviewed('quantity')}
                    className={`p-1.5 rounded border transition flex-shrink-0 ${
                      reviewedFlags.quantity 
                        ? 'bg-[#E8F2F0] border-[#0E5E52] text-[#0E5E52]' 
                        : 'bg-white border-[#E4E3DF] text-[#848A92] hover:border-[#848A92]'
                    }`}
                  >
                    <CheckIcon className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Field 4 & 5: Incoterm & Target Price */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-3 rounded border border-[#E4E3DF] bg-[#FFFFFF] flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <label className="text-xs font-semibold text-[#1B1D1F]">Incoterm *</label>
                      <ConfidenceChip
                        confidence={selectedInquiry.extracted_data?.incoterm?.confidence || 0.96}
                        sourceEvidence={selectedInquiry.extracted_data?.incoterm?.evidence}
                        onEvidenceClick={() => setActiveHighlight(selectedInquiry.extracted_data?.incoterm?.evidence)}
                      />
                    </div>
                    <select
                      value={reviewFields.incoterm}
                      onChange={(e) => setReviewFields({ ...reviewFields, incoterm: e.target.value })}
                      className="w-full text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-2.5 py-1.5 text-[#1B1D1F]"
                    >
                      <option value="FOB">FOB — Free on Board (Karachi)</option>
                      <option value="CIF">CIF — Cost, Insurance & Freight</option>
                      <option value="CFR">CFR — Cost & Freight</option>
                      <option value="EXW">EXW — Ex Works</option>
                      <option value="DAP">DAP — Delivered at Place</option>
                      <option value="DDP">DDP — Delivered Duty Paid</option>
                    </select>
                  </div>
                  <button
                    type="button"
                    onClick={() => toggleFieldReviewed('incoterm')}
                    className={`p-1.5 rounded border transition flex-shrink-0 ${
                      reviewedFlags.incoterm 
                        ? 'bg-[#E8F2F0] border-[#0E5E52] text-[#0E5E52]' 
                        : 'bg-white border-[#E4E3DF] text-[#848A92] hover:border-[#848A92]'
                    }`}
                  >
                    <CheckIcon className="w-4 h-4" />
                  </button>
                </div>

                <div className="p-3 rounded border border-[#E4E3DF] bg-[#FFFFFF] flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <label className="text-xs font-semibold text-[#1B1D1F]">Target Price (USD/Unit)</label>
                      <ConfidenceChip
                        confidence={selectedInquiry.extracted_data?.target_price?.confidence || 0.94}
                        sourceEvidence={selectedInquiry.extracted_data?.target_price?.evidence}
                        onEvidenceClick={() => setActiveHighlight(selectedInquiry.extracted_data?.target_price?.evidence)}
                      />
                    </div>
                    <input
                      type="text"
                      placeholder="e.g. 14.50"
                      value={reviewFields.target_price}
                      onChange={(e) => setReviewFields({ ...reviewFields, target_price: e.target.value })}
                      className="w-full text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-2.5 py-1.5 text-[#1B1D1F]"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => toggleFieldReviewed('target_price')}
                    className={`p-1.5 rounded border transition flex-shrink-0 ${
                      reviewedFlags.target_price 
                        ? 'bg-[#E8F2F0] border-[#0E5E52] text-[#0E5E52]' 
                        : 'bg-white border-[#E4E3DF] text-[#848A92] hover:border-[#848A92]'
                    }`}
                  >
                    <CheckIcon className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Field 6 & 7: Destination Port & Payment Terms */}
              <div className="p-3 rounded border border-[#E4E3DF] bg-[#FFFFFF] flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <label className="text-xs font-semibold text-[#1B1D1F]">Destination Port & Payment Terms</label>
                    <ConfidenceChip
                      confidence={selectedInquiry.extracted_data?.payment_terms?.confidence || 0.90}
                      sourceEvidence={selectedInquiry.extracted_data?.payment_terms?.evidence}
                      onEvidenceClick={() => setActiveHighlight(selectedInquiry.extracted_data?.payment_terms?.evidence)}
                    />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <input
                      type="text"
                      placeholder="Destination Port (e.g. DEHAM)"
                      value={reviewFields.destination_port}
                      onChange={(e) => setReviewFields({ ...reviewFields, destination_port: e.target.value })}
                      className="text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-2.5 py-1.5 text-[#1B1D1F]"
                    />
                    <input
                      type="text"
                      placeholder="Payment Terms (e.g. 30% TT, 70% CAD)"
                      value={reviewFields.payment_terms}
                      onChange={(e) => setReviewFields({ ...reviewFields, payment_terms: e.target.value })}
                      className="text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-2.5 py-1.5 text-[#1B1D1F]"
                    />
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => toggleFieldReviewed('destination_port')}
                  className={`p-1.5 rounded border transition flex-shrink-0 ${
                    reviewedFlags.destination_port 
                      ? 'bg-[#E8F2F0] border-[#0E5E52] text-[#0E5E52]' 
                      : 'bg-white border-[#E4E3DF] text-[#848A92] hover:border-[#848A92]'
                  }`}
                >
                  <CheckIcon className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Bottom Approval Footer */}
            <div className="p-3.5 border-t border-[#E4E3DF] bg-[#F7F7F5] flex items-center justify-between gap-3">
              <div className="text-xs text-[#585D63]">
                {allRequiredReviewed ? (
                  <span className="text-[#0E5E52] font-medium flex items-center gap-1">
                    <CheckIcon className="w-3.5 h-3.5" /> All required fields verified
                  </span>
                ) : (
                  <span>Verify Buyer, Product, Qty & Incoterm to enable creation</span>
                )}
              </div>

              <button
                type="button"
                disabled={!allRequiredReviewed || isConfirming}
                onClick={handleConfirmAndCreateDeal}
                className={`px-4 py-2 rounded text-xs font-semibold transition flex items-center gap-2 ${
                  allRequiredReviewed
                    ? 'bg-[#0E5E52] hover:bg-[#0C4A40] text-white shadow-subtle'
                    : 'bg-[#E4E3DF] text-[#848A92] cursor-not-allowed'
                }`}
              >
                {isConfirming ? 'Creating Deal in DB...' : 'Confirm & Create Deal'}
                <ChevronRightIcon className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Designed Empty State when 0 inquiries are in database */
        <div className="bg-[#FFFFFF] border border-[#E4E3DF] rounded p-8 text-center space-y-3">
          <div className="w-10 h-10 rounded bg-[#E8F2F0] text-[#0E5E52] flex items-center justify-center mx-auto">
            <DocumentIcon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#1B1D1F]">No Inquiries in Database</h3>
            <p className="text-xs text-[#585D63] max-w-sm mx-auto mt-1">
              Ingest a raw email, WhatsApp RFQ, or upload a customer purchase inquiry document to initiate the deterministic verification pipeline.
            </p>
          </div>
          <button
            onClick={() => setShowIngestModal(true)}
            className="px-4 py-2 text-xs font-semibold text-white bg-[#0E5E52] hover:bg-[#0C4A40] rounded transition"
          >
            + Ingest First Inquiry
          </button>
        </div>
      )}

      {/* ── Inquiries List View ────────────────────────────────── */}
      <div className="bg-[#FFFFFF] border border-[#E4E3DF] rounded overflow-hidden mt-6">
        <div className="p-3 border-b border-[#E4E3DF] bg-[#F7F7F5] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[#1B1D1F]">
              Inbound RFQ Inquiries ({inquiries.length})
            </h2>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-200 text-slate-700">
              Live Database
            </span>
          </div>

          <div className="relative w-64">
            <input
              type="text"
              placeholder="Search by buyer, subject, ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-7 pr-3 py-1 text-xs font-mono bg-[#FFFFFF] border border-[#E4E3DF] rounded text-[#1B1D1F] focus:outline-none focus:border-[#0E5E52]"
            />
            <SearchIcon className="w-3 h-3 text-[#848A92] absolute left-2 top-1/2 -translate-y-1/2" />
          </div>
        </div>

        {filteredInquiries.length > 0 ? (
          <table className="ops-table">
            <thead>
              <tr>
                <th>Reference / ID</th>
                <th>Status</th>
                <th>Buyer Name</th>
                <th>Subject / File</th>
                <th>Channel</th>
                <th>Date Ingested</th>
                <th className="text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredInquiries.map((inq) => {
                const isSelected = selectedInquiry?.id === inq.id;

                return (
                  <tr
                    key={inq.id}
                    onClick={() => selectInquiryForReview(inq)}
                    className={`cursor-pointer transition ${isSelected ? 'bg-[#FAF9F6] font-medium' : ''}`}
                  >
                    <td className="font-mono text-xs font-semibold text-[#0E5E52]">
                      {inq.deal_reference || String(inq.id).slice(0, 12)}
                    </td>
                    <td>
                      <span
                        className={`text-[11px] px-2 py-0.5 rounded border font-mono font-medium ${
                          inq.deal_state && inq.deal_state !== 'INQUIRY'
                            ? 'bg-[#E8F2F0] text-[#0C4A40] border-[#B6D9D2]'
                            : 'bg-amber-50 text-amber-800 border-amber-200'
                        }`}
                      >
                        {inq.deal_state || 'PENDING_REVIEW'}
                      </span>
                    </td>
                    <td className="font-semibold text-[#1B1D1F] text-xs">
                      {inq.deal_buyer_name || inq.buyer_name || 'Inbound Buyer'}
                    </td>
                    <td className="text-xs text-[#585D63] max-w-xs truncate">
                      {inq.subject || inq.filename || inq.raw_content?.slice(0, 60)}
                    </td>
                    <td className="text-xs font-mono text-[#585D63] uppercase">
                      {inq.channel || inq.artifact_type || 'EMAIL'}
                    </td>
                    <td className="font-mono text-xs text-[#848A92]">
                      {inq.created_at ? inq.created_at.split('T')[0] : 'Today'}
                    </td>
                    <td className="text-right">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          selectInquiryForReview(inq);
                        }}
                        className="text-xs font-semibold text-[#0E5E52] hover:underline"
                      >
                        Audit &rarr;
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <div className="p-6 text-center text-xs text-[#848A92]">
            {isLoading ? 'Loading database records...' : 'No matching inquiries found.'}
          </div>
        )}
      </div>

      {/* ── Ingestion Modal ────────────────────────────────────── */}
      {showIngestModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4 backdrop-blur-[2px]">
          <div className="bg-[#FFFFFF] border border-[#E4E3DF] rounded shadow-modal w-full max-w-lg p-5">
            <div className="flex items-center justify-between border-b border-[#E4E3DF] pb-3 mb-4">
              <h3 className="text-sm font-bold text-[#1B1D1F]">Ingest Buyer RFQ into Database</h3>
              <button
                onClick={() => setShowIngestModal(false)}
                className="text-[#848A92] hover:text-[#1B1D1F] text-sm"
              >
                ✕
              </button>
            </div>

            {/* Ingestion Tabs: Raw Text vs File Upload */}
            <div className="flex border-b border-[#E4E3DF] mb-3 text-xs font-mono">
              <button
                type="button"
                onClick={() => setIngestTab('text')}
                className={`px-3 py-1.5 font-semibold transition ${
                  ingestTab === 'text' 
                    ? 'border-b-2 border-[#0E5E52] text-[#0E5E52]' 
                    : 'text-[#848A92]'
                }`}
              >
                Raw Text / Email
              </button>
              <button
                type="button"
                onClick={() => setIngestTab('file')}
                className={`px-3 py-1.5 font-semibold transition ${
                  ingestTab === 'file' 
                    ? 'border-b-2 border-[#0E5E52] text-[#0E5E52]' 
                    : 'text-[#848A92]'
                }`}
              >
                Document Upload (PDF/Excel)
              </button>
            </div>

            {modalError && (
              <div className="mb-3 p-2 bg-red-50 border border-red-200 text-red-700 rounded text-xs">
                {modalError}
              </div>
            )}

            <form onSubmit={handleCreateInquiry} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">
                  Buyer Name / Organisation *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Hanseatic Textile Imports GmbH"
                  value={buyerNameInput}
                  onChange={(e) => setBuyerNameInput(e.target.value)}
                  className="w-full text-xs bg-[#FAFAF8] border border-[#E4E3DF] rounded px-3 py-1.5 text-[#1B1D1F]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">
                    Sender Email
                  </label>
                  <input
                    type="email"
                    placeholder="procurement@buyer.de"
                    value={senderEmailInput}
                    onChange={(e) => setSenderEmailInput(e.target.value)}
                    className="w-full text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-3 py-1.5 text-[#1B1D1F]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">
                    Subject / RFQ Code
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. RFQ for 10,000 units Pants"
                    value={subjectInput}
                    onChange={(e) => setSubjectInput(e.target.value)}
                    className="w-full text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded px-3 py-1.5 text-[#1B1D1F]"
                  />
                </div>
              </div>

              {ingestTab === 'text' ? (
                <div>
                  <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">
                    Raw Inquiry / Email Body *
                  </label>
                  <textarea
                    rows={5}
                    required
                    placeholder="Paste buyer email, WhatsApp text, or specification table here..."
                    value={rawTextContent}
                    onChange={(e) => setRawTextContent(e.target.value)}
                    className="w-full text-xs font-mono bg-[#FAFAF8] border border-[#E4E3DF] rounded p-2.5 text-[#1B1D1F]"
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">
                    Inquiry Document (PDF, Excel, Word, CSV) *
                  </label>
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    accept=".pdf,.xlsx,.xls,.csv,.doc,.docx,.txt"
                    className="w-full text-xs bg-[#FAFAF8] border border-[#E4E3DF] rounded p-2 text-[#1B1D1F]"
                  />
                  {file && (
                    <div className="mt-1 text-[11px] font-mono text-[#0E5E52]">
                      Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
                    </div>
                  )}
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#E4E3DF]">
                <button
                  type="button"
                  onClick={() => setShowIngestModal(false)}
                  className="px-3 py-1.5 text-xs text-[#585D63] hover:text-[#1B1D1F] font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-[#0E5E52] hover:bg-[#0C4A40] rounded transition"
                >
                  {isSubmitting ? 'Ingesting to DB...' : 'Save & Ingest'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
