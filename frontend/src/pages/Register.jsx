import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AlertTriangleIcon } from '../components/common/Icons';

export default function Register() {
  const [formData, setFormData] = useState({
    company_name: '',
    country: 'Pakistan',
    default_currency: 'USD',
    full_name: '',
    email: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      await register(formData);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAF8] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-lg">
        {/* Brand Header */}
        <div className="flex justify-center mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded bg-[#0E5E52] flex items-center justify-center text-white font-mono font-bold text-sm tracking-tight shadow-sm">
              TL
            </div>
            <div>
              <h1 className="text-xl font-bold text-[#1B1D1F] tracking-tight">Tradeloop</h1>
              <p className="text-[11px] font-mono text-[#848A92] uppercase tracking-wider">Export Operations Onboarding</p>
            </div>
          </div>
        </div>

        {/* Form Container */}
        <div className="bg-[#FFFFFF] border border-[#E4E3DF] shadow-modal rounded p-8 sm:p-10">
          <div className="mb-6">
            <h2 className="text-base font-bold text-[#1B1D1F] tracking-tight">Register Exporter Organization</h2>
            <p className="text-xs text-[#585D63] mt-1">Configure your SME export workspace and initial administrator profile</p>
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
                Company Legal Name (as registered with SECP / Chamber) *
              </label>
              <input
                type="text"
                name="company_name"
                required
                value={formData.company_name}
                onChange={handleChange}
                placeholder="e.g. Indus Garments & Textiles Pvt Ltd"
                className="w-full px-3 py-2 bg-[#FAFAF8] border border-[#E4E3DF] rounded text-[#1B1D1F] text-xs"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">
                  Origin Country
                </label>
                <input
                  type="text"
                  name="country"
                  disabled
                  value={formData.country}
                  className="w-full px-3 py-2 bg-[#F0EFEA] border border-[#E4E3DF] rounded text-[#585D63] text-xs font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">
                  Default Settlement Currency
                </label>
                <select
                  name="default_currency"
                  value={formData.default_currency}
                  onChange={handleChange}
                  className="w-full px-3 py-2 bg-[#FAFAF8] border border-[#E4E3DF] rounded text-[#1B1D1F] text-xs font-mono"
                >
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                  <option value="GBP">GBP (£)</option>
                  <option value="PKR">PKR (₨)</option>
                </select>
              </div>
            </div>

            <div className="pt-2 border-t border-[#E4E3DF]">
              <div className="text-[11px] font-mono text-[#848A92] uppercase mb-2">Administrator Profile</div>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    name="full_name"
                    required
                    value={formData.full_name}
                    onChange={handleChange}
                    placeholder="e.g. Tariq Mehmood"
                    className="w-full px-3 py-2 bg-[#FAFAF8] border border-[#E4E3DF] rounded text-[#1B1D1F] text-xs"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">
                    Corporate Email Address *
                  </label>
                  <input
                    type="email"
                    name="email"
                    required
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="tariq@indusgarments.pk"
                    className="w-full px-3 py-2 bg-[#FAFAF8] border border-[#E4E3DF] rounded text-[#1B1D1F] text-xs font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#1B1D1F] mb-1">
                    Password *
                  </label>
                  <input
                    type="password"
                    name="password"
                    required
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="••••••••"
                    className="w-full px-3 py-2 bg-[#FAFAF8] border border-[#E4E3DF] rounded text-[#1B1D1F] text-xs font-mono"
                  />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 bg-[#0E5E52] hover:bg-[#0C4A40] text-white font-semibold text-xs rounded transition duration-150 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-subtle mt-2"
            >
              {isSubmitting ? 'Creating Workspace...' : 'Register Workspace'}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-[#E4E3DF] text-center">
            <p className="text-xs text-[#585D63]">
              Already have an account?{' '}
              <Link to="/login" className="text-[#0E5E52] hover:underline font-semibold">
                Sign in &rarr;
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
