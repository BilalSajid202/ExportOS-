import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import api from '../lib/api';

const CHANNEL_CONFIG = {
  FILE_UPLOAD: {
    label: 'File Upload',
    icon: '📄',
    badge: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  },
  EMAIL: {
    label: 'Email Ingestion',
    icon: '✉️',
    badge: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  },
  WEB_FORM: {
    label: 'Direct Form',
    icon: '📝',
    badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  },
};

export default function Inquiries() {
  const [inquiries, setInquiries] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'text'

  // Selected Inquiry for details modal
  const [selectedInquiry, setSelectedInquiry] = useState(null);

  // File Upload Form State
  const [file, setFile] = useState(null);
  const [uploadBuyerName, setUploadBuyerName] = useState('');
  const [uploadSenderEmail, setUploadSenderEmail] = useState('');
  const [uploadSubject, setUploadSubject] = useState('');
  const [uploadNotes, setUploadNotes] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState('');
  const fileInputRef = useRef(null);

  // Text Ingestion Form State
  const [textBuyerName, setTextBuyerName] = useState('');
  const [textSenderEmail, setTextSenderEmail] = useState('');
  const [textSubject, setTextSubject] = useState('');
  const [textRawContent, setTextRawContent] = useState('');
  const [textNotes, setTextNotes] = useState('');
  const [isIngesting, setIsIngesting] = useState(false);
  const [textError, setTextError] = useState('');
  const [textSuccess, setTextSuccess] = useState('');

  const fetchInquiries = async () => {
    setIsLoading(true);
    try {
      const data = await api.get('/inquiries');
      setInquiries(data);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load inquiries');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchInquiries();
  }, []);

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setUploadError('Please select a file to upload');
      return;
    }

    setUploadError('');
    setUploadSuccess('');
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('buyer_name', uploadBuyerName);
      if (uploadSenderEmail) formData.append('sender_email', uploadSenderEmail);
      if (uploadSubject) formData.append('subject', uploadSubject);
      if (uploadNotes) formData.append('notes', uploadNotes);

      const token = localStorage.getItem('exportos_token');
      const response = await fetch('/api/inquiries/upload', {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      const created = await response.json();
      setUploadSuccess(`Inquiry artifact ingested and linked to deal ${created.deal_reference || ''}`);
      setFile(null);
      setUploadBuyerName('');
      setUploadSenderEmail('');
      setUploadSubject('');
      setUploadNotes('');
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchInquiries();
    } catch (err) {
      setUploadError(err.message || 'File upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleTextIngest = async (e) => {
    e.preventDefault();
    setTextError('');
    setTextSuccess('');
    setIsIngesting(true);

    try {
      const payload = {
        buyer_name: textBuyerName,
        sender_email: textSenderEmail || null,
        subject: textSubject || null,
        raw_content: textRawContent,
        notes: textNotes || null,
      };

      const created = await api.post('/inquiries/text', payload);
      setTextSuccess(`Inquiry ingested and linked to deal ${created.deal_reference || ''}`);
      setTextBuyerName('');
      setTextSenderEmail('');
      setTextSubject('');
      setTextRawContent('');
      setTextNotes('');
      fetchInquiries();
    } catch (err) {
      setTextError(err.message || 'Text ingestion failed');
    } finally {
      setIsIngesting(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const copyHash = (hash) => {
    navigator.clipboard.writeText(hash);
    alert('SHA-256 Hash copied to clipboard: ' + hash);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Inquiry Ingestion</h1>
          <p className="text-sm text-slate-400 mt-1">
            Intake buyer RFQs across files and email streams with cryptographic audit records
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchInquiries}
            className="p-2.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 rounded-xl text-sm font-medium transition"
            title="Refresh Inquiries"
          >
            🔄
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchInquiries} className="underline text-xs hover:text-rose-300">
            Retry
          </button>
        </div>
      )}

      {/* Ingestion Hub Card */}
      <div className="bg-slate-900/70 backdrop-blur-xl border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        {/* Tabs */}
        <div className="flex border-b border-slate-800 bg-slate-950/40">
          <button
            onClick={() => setActiveTab('upload')}
            className={`flex items-center gap-2 px-6 py-3.5 text-sm font-semibold border-b-2 transition ${
              activeTab === 'upload'
                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>📁</span> File Upload Ingestion (PDF / Excel / Word)
          </button>
          <button
            onClick={() => setActiveTab('text')}
            className={`flex items-center gap-2 px-6 py-3.5 text-sm font-semibold border-b-2 transition ${
              activeTab === 'text'
                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>✉️</span> Raw Email / Text Ingestion
          </button>
        </div>

        <div className="p-6 sm:p-8">
          {/* Tab 1: File Upload */}
          {activeTab === 'upload' && (
            <form onSubmit={handleFileUpload} className="space-y-5">
              {uploadError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs">
                  {uploadError}
                </div>
              )}
              {uploadSuccess && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400 text-xs flex items-center justify-between">
                  <span>{uploadSuccess}</span>
                  <Link to="/deals" className="underline font-semibold ml-2 hover:text-emerald-300">
                    View Deals Board →
                  </Link>
                </div>
              )}

              {/* Drag & Drop Box */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition ${
                  file
                    ? 'border-indigo-500/60 bg-indigo-500/5'
                    : 'border-slate-800 hover:border-slate-700 bg-slate-950/40'
                }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="hidden"
                  accept=".pdf,.xlsx,.xls,.csv,.doc,.docx,.txt"
                />
                <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 text-2xl mx-auto mb-3">
                  {file ? '📄' : '☁️'}
                </div>
                {file ? (
                  <div>
                    <p className="text-sm font-semibold text-white">{file.name}</p>
                    <p className="text-xs text-slate-400 mt-1">{formatFileSize(file.size)}</p>
                    <p className="text-[11px] text-indigo-400 mt-2 font-medium">Click to replace file</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-semibold text-slate-200">
                      Click to upload or drag & drop RFQ document
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      Supports PDF, Excel (.xlsx, .csv), Word (.docx), or plain text
                    </p>
                  </div>
                )}
              </div>

              {/* Metadata Inputs */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Buyer / Client Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={uploadBuyerName}
                    onChange={(e) => setUploadBuyerName(e.target.value)}
                    placeholder="e.g. Intersport Germany GmbH"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Sender Email
                  </label>
                  <input
                    type="email"
                    value={uploadSenderEmail}
                    onChange={(e) => setUploadSenderEmail(e.target.value)}
                    placeholder="procurement@intersport.de"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Subject / RFQ Reference
                  </label>
                  <input
                    type="text"
                    value={uploadSubject}
                    onChange={(e) => setUploadSubject(e.target.value)}
                    placeholder="e.g. RFQ: 5,000 Footballs CIF Hamburg"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Internal Notes
                  </label>
                  <input
                    type="text"
                    value={uploadNotes}
                    onChange={(e) => setUploadNotes(e.target.value)}
                    placeholder="e.g. Client requested urgent delivery schedule"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={isUploading}
                  className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-medium text-sm rounded-xl shadow-lg shadow-indigo-600/25 transition disabled:opacity-50 flex items-center gap-2"
                >
                  {isUploading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                      <span>Ingesting Artifact...</span>
                    </>
                  ) : (
                    <>
                      <span>📥</span> Ingest Document & Create Deal
                    </>
                  )}
                </button>
              </div>
            </form>
          )}

          {/* Tab 2: Raw Email / Text Intake */}
          {activeTab === 'text' && (
            <form onSubmit={handleTextIngest} className="space-y-5">
              {textError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs">
                  {textError}
                </div>
              )}
              {textSuccess && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400 text-xs flex items-center justify-between">
                  <span>{textSuccess}</span>
                  <Link to="/deals" className="underline font-semibold ml-2 hover:text-emerald-300">
                    View Deals Board →
                  </Link>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Buyer / Client Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={textBuyerName}
                    onChange={(e) => setTextBuyerName(e.target.value)}
                    placeholder="e.g. Adidas AG Purchasing"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Sender Email
                  </label>
                  <input
                    type="email"
                    value={textSenderEmail}
                    onChange={(e) => setTextSenderEmail(e.target.value)}
                    placeholder="inquiry@adidas.de"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Email Subject
                  </label>
                  <input
                    type="text"
                    value={textSubject}
                    onChange={(e) => setTextSubject(e.target.value)}
                    placeholder="e.g. Quotation Request: 2,500 Footballs Size 5"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Raw Inquiry Message / Email Body *
                  </label>
                  <textarea
                    rows={6}
                    required
                    value={textRawContent}
                    onChange={(e) => setTextRawContent(e.target.value)}
                    placeholder={`Paste incoming email message or buyer WhatsApp inquiry here...\n\nExample:\n"Dear Team, please quote 2,500 Size-5 match footballs for delivery to Hamburg port (CIF Hamburg). Required delivery by November 15, 2026. Target price $12.50/pc. Looking forward to your prompt proforma."`}
                    className="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 font-mono text-xs placeholder-slate-500 focus:outline-none focus:border-indigo-500 leading-relaxed"
                  />
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={isIngesting}
                  className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-medium text-sm rounded-xl shadow-lg shadow-indigo-600/25 transition disabled:opacity-50 flex items-center gap-2"
                >
                  {isIngesting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                      <span>Processing...</span>
                    </>
                  ) : (
                    <>
                      <span>✉️</span> Ingest Text & Create Deal
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

      {/* Inbound Artifacts Repository Table */}
      <div className="bg-slate-900/70 backdrop-blur-xl border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
              Inbound Artifacts Repository ({inquiries.length})
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Cryptographically hashed records stored immutably
            </p>
          </div>
          <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-lg">
            SHA-256 Verified
          </span>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-500 flex flex-col items-center">
            <div className="w-8 h-8 border-3 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin mb-3" />
            <span className="text-sm">Loading artifacts...</span>
          </div>
        ) : inquiries.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <p className="text-sm">No inquiry artifacts recorded yet.</p>
            <p className="text-xs text-slate-400 mt-1">Upload an inquiry document or paste raw email text above to begin.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-xs text-slate-400 uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3.5 font-semibold">Channel</th>
                  <th className="px-6 py-3.5 font-semibold">Artifact / Subject</th>
                  <th className="px-6 py-3.5 font-semibold">Buyer / Sender</th>
                  <th className="px-6 py-3.5 font-semibold">Linked Deal</th>
                  <th className="px-6 py-3.5 font-semibold">SHA-256 Hash</th>
                  <th className="px-6 py-3.5 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {inquiries.map((item) => {
                  const channel = CHANNEL_CONFIG[item.channel] || {
                    label: item.channel,
                    icon: '📦',
                    badge: 'bg-slate-800 text-slate-300 border-slate-700',
                  };

                  return (
                    <tr key={item.id} className="hover:bg-slate-800/30 transition">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg border ${channel.badge}`}>
                          <span>{channel.icon}</span>
                          <span>{channel.label}</span>
                        </span>
                      </td>

                      <td className="px-6 py-4">
                        <div className="font-semibold text-white">{item.filename}</div>
                        {item.subject && (
                          <div className="text-xs text-slate-400 truncate max-w-xs">{item.subject}</div>
                        )}
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          {formatFileSize(item.file_size_bytes)} • {new Date(item.created_at).toLocaleString()}
                        </div>
                      </td>

                      <td className="px-6 py-4">
                        <div className="text-xs font-medium text-slate-200">
                          {item.deal_buyer_name || item.sender_info || 'Unknown Buyer'}
                        </div>
                        {item.sender_info && (
                          <div className="text-[11px] text-slate-400 font-mono">{item.sender_info}</div>
                        )}
                      </td>

                      <td className="px-6 py-4 whitespace-nowrap">
                        {item.deal_reference ? (
                          <Link
                            to={`/deals/${item.deal_id}`}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-mono font-medium hover:bg-indigo-500/20 transition"
                          >
                            <span>📋</span>
                            <span>{item.deal_reference}</span>
                          </Link>
                        ) : (
                          <span className="text-xs text-slate-400 font-mono">Unlinked</span>
                        )}
                      </td>

                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-slate-400 truncate max-w-[120px]">
                            {item.sha256_hash.substring(0, 12)}...
                          </span>
                          <button
                            onClick={() => copyHash(item.sha256_hash)}
                            className="text-slate-400 hover:text-white text-xs p-1 rounded hover:bg-slate-800 transition"
                            title="Copy Full SHA-256 Hash"
                          >
                            📋
                          </button>
                        </div>
                      </td>

                      <td className="px-6 py-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => setSelectedInquiry(item)}
                            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition"
                          >
                            Inspect
                          </button>
                          {item.file_path && (
                            <a
                              href={`/api/inquiries/${item.id}/download`}
                              download
                              className="px-3 py-1.5 bg-indigo-600/20 border border-indigo-500/30 hover:bg-indigo-600/30 text-indigo-300 text-xs font-medium rounded-lg transition inline-flex items-center gap-1"
                            >
                              <span>⬇️</span> Download
                            </a>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Inspect Artifact Detail Modal */}
      {selectedInquiry && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl p-6 shadow-2xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <span>📄</span> {selectedInquiry.filename}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Artifact ID: <span className="font-mono text-slate-400">{selectedInquiry.id}</span>
                </p>
              </div>
              <button
                onClick={() => setSelectedInquiry(null)}
                className="text-slate-400 hover:text-white transition text-lg"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 flex-1 overflow-y-auto pr-1">
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl">
                  <span className="text-slate-400 block mb-1">Inbound Channel</span>
                  <span className="font-semibold text-white">{selectedInquiry.channel}</span>
                </div>
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl">
                  <span className="text-slate-400 block mb-1">MIME Type</span>
                  <span className="font-mono text-slate-200">{selectedInquiry.mime_type}</span>
                </div>
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl">
                  <span className="text-slate-400 block mb-1">File Size</span>
                  <span className="font-semibold text-white">{formatFileSize(selectedInquiry.file_size_bytes)}</span>
                </div>
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl">
                  <span className="text-slate-400 block mb-1">Linked Deal</span>
                  <span className="font-mono font-semibold text-indigo-400">
                    {selectedInquiry.deal_reference || 'None'}
                  </span>
                </div>
              </div>

              <div>
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-1.5">
                  Cryptographic SHA-256 Hash
                </span>
                <div className="flex items-center gap-2 p-2.5 bg-slate-950 border border-slate-800 rounded-xl font-mono text-xs text-emerald-400 break-all">
                  <span>{selectedInquiry.sha256_hash}</span>
                </div>
              </div>

              {selectedInquiry.raw_content && (
                <div>
                  <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-1.5">
                    Raw Inbound Content
                  </span>
                  <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl font-mono text-xs text-slate-200 whitespace-pre-wrap max-h-60 overflow-y-auto leading-relaxed">
                    {selectedInquiry.raw_content}
                  </div>
                </div>
              )}
            </div>

            <div className="pt-4 border-t border-slate-800 mt-4 flex items-center justify-between">
              {selectedInquiry.deal_id && (
                <Link
                  to={`/deals/${selectedInquiry.deal_id}`}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-medium transition"
                >
                  Open Linked Deal →
                </Link>
              )}
              <button
                onClick={() => setSelectedInquiry(null)}
                className="ml-auto px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
