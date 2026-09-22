import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AlertTriangleIcon } from '../components/common/Icons';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAF8] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        {/* Brand Header */}
        <div className="flex justify-center mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded bg-[#0E5E52] flex items-center justify-center text-white font-mono font-bold text-sm tracking-tight shadow-sm">
              TL
            </div>
            <div>
              <h1 className="text-xl font-bold text-[#1B1D1F] tracking-tight">Tradeloop</h1>
              <p className="text-[11px] font-mono text-[#848A92] uppercase tracking-wider">Export Operations Platform</p>
            </div>
          </div>
        </div>

        {/* Login Box */}
        <div className="bg-[#FFFFFF] border border-[#E4E3DF] shadow-modal rounded p-8 sm:p-10">
          <div className="mb-6">
            <h2 className="text-base font-bold text-[#1B1D1F] tracking-tight">Sign In to Exporter Workspace</h2>
            <p className="text-xs text-[#585D63] mt-1">Access deterministic deal ledger, costing, and SBP regulatory copilot</p>
          </div>

          {error && (
            <div className="mb-5 p-3 bg-red-50 border border-red-200 rounded flex items-center gap-2 text-xs text-red-800">
              <AlertTriangleIcon className="w-4 h-4 text-red-700 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">
                Corporate Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ops@sme-exporter.pk"
                className="w-full px-3 py-2 bg-[#FAFAF8] border border-[#E4E3DF] rounded text-[#1B1D1F] placeholder-[#848A92] focus:outline-none focus:border-[#0E5E52] text-xs font-mono"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-[#1B1D1F]">
                  Password
                </label>
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3 py-2 bg-[#FAFAF8] border border-[#E4E3DF] rounded text-[#1B1D1F] placeholder-[#848A92] focus:outline-none focus:border-[#0E5E52] text-xs font-mono"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 bg-[#0E5E52] hover:bg-[#0C4A40] text-white font-semibold text-xs rounded transition duration-150 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-subtle mt-2"
            >
              {isSubmitting ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-[#E4E3DF] text-center">
            <p className="text-xs text-[#585D63]">
              Need to register a new SME export organization?{' '}
              <Link to="/register" className="text-[#0E5E52] hover:underline font-semibold">
                Register company &rarr;
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
