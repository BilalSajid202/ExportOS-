import { useState, useEffect } from 'react';
import api from '../lib/api';
import { useAuth } from '../context/AuthContext';

const ROLE_CONFIG = {
  ADMIN: {
    label: 'Admin',
    color: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    desc: 'Full organisation settings and user management',
  },
  EXPORT_MANAGER: {
    label: 'Export Manager',
    color: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    desc: 'Full deal lifecycle and quotation approvals',
  },
  DOCUMENTATION_OFFICER: {
    label: 'Documentation Officer',
    color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    desc: 'Document generation, HS code, and consistency checks',
  },
  SALES: {
    label: 'Sales Officer',
    color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    desc: 'Inquiry intake and buyer communications',
  },
  ACCOUNTS: {
    label: 'Accounts / Finance',
    color: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    desc: 'Payment tracking and costing adjustments',
  },
};

export default function Team() {
  const { user, isAdmin } = useAuth();
  const [members, setMembers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Add Member Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    password: '',
    role: 'SALES',
  });
  const [modalError, setModalError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchMembers = async () => {
    setIsLoading(true);
    try {
      const data = await api.get('/organisation/users');
      setMembers(data);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load team members');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMembers();
  }, []);

  const handleAddMember = async (e) => {
    e.preventDefault();
    setModalError('');
    setIsSubmitting(true);

    try {
      await api.post('/organisation/users', formData);
      setIsModalOpen(false);
      setFormData({ full_name: '', email: '', password: '', role: 'SALES' });
      fetchMembers();
    } catch (err) {
      setModalError(err.message || 'Failed to add member');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Team Management</h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage your organisation's members and their operational roles
          </p>
        </div>

        {isAdmin && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl shadow-lg shadow-indigo-600/20 transition"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add Team Member
          </button>
        )}
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={fetchMembers} className="underline text-xs hover:text-rose-300">
            Retry
          </button>
        </div>
      )}

      {/* Members Grid / Table */}
      <div className="bg-slate-900/60 backdrop-blur border border-slate-800/80 rounded-2xl overflow-hidden shadow-xl">
        <div className="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
            Members ({members.length})
          </h2>
          <span className="text-xs text-slate-500 font-mono">Tenant Isolation Active</span>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-slate-500 flex flex-col items-center">
            <div className="w-8 h-8 border-3 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin mb-3" />
            <span className="text-sm">Loading team...</span>
          </div>
        ) : members.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <p className="text-sm">No team members found.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {members.map((member) => {
              const roleMeta = ROLE_CONFIG[member.role] || {
                label: member.role,
                color: 'bg-slate-800 text-slate-300 border-slate-700',
              };
              const isSelf = member.id === user?.id;

              return (
                <div
                  key={member.id}
                  className="px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-800/30 transition"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-slate-800 to-slate-700 border border-slate-700 flex items-center justify-center font-bold text-slate-200 text-sm shadow-inner">
                      {member.full_name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-white">{member.full_name}</span>
                        {isSelf && (
                          <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                            You
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-slate-400 font-mono">{member.email}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span
                      className={`text-xs font-medium px-3 py-1 rounded-lg border ${roleMeta.color}`}
                    >
                      {roleMeta.label}
                    </span>
                    <span className="text-xs text-slate-500">
                      Joined {new Date(member.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Add Member Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl relative">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-bold text-white">Add Team Member</h3>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white transition"
              >
                ✕
              </button>
            </div>

            {modalError && (
              <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs">
                {modalError}
              </div>
            )}

            <form onSubmit={handleAddMember} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  placeholder="e.g. Tariq Khan"
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="tariq@company.com"
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Temporary Password
                </label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Assigned Role
                </label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="SALES">Sales Officer</option>
                  <option value="EXPORT_MANAGER">Export Manager</option>
                  <option value="DOCUMENTATION_OFFICER">Documentation Officer</option>
                  <option value="ACCOUNTS">Accounts / Finance</option>
                  <option value="ADMIN">Administrator</option>
                </select>
                <p className="text-[11px] text-slate-500 mt-1">
                  {ROLE_CONFIG[formData.role]?.desc}
                </p>
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
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition shadow-lg shadow-indigo-600/20 disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isSubmitting ? 'Creating...' : 'Create Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
