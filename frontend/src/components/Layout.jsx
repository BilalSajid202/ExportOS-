import { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/* ── Sidebar Navigation Items ─────────────────────────────── */
const navItems = [
  { to: '/', icon: '📊', label: 'Dashboard' },
  { to: '/inquiries', icon: '📥', label: 'Inquiries' },
  { to: '/deals', icon: '📋', label: 'Deals' },
  { to: '/products', icon: '📦', label: 'Products' },
  { to: '/inventory', icon: '🏭', label: 'Inventory' },
  { to: '/team', icon: '👥', label: 'Team Members' },
];

const ROLE_BADGES = {
  ADMIN: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  EXPORT_MANAGER: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  DOCUMENTATION_OFFICER: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  SALES: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  ACCOUNTS: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
};

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { user, organisation, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-slate-100">
      {/* ── Sidebar ─────────────────────────────────────────── */}
      <aside
        className={`
          flex flex-col border-r border-slate-800/80 bg-slate-900/90
          transition-all duration-300 ease-in-out z-20
          ${sidebarOpen ? 'w-64' : 'w-[72px]'}
        `}
      >
        {/* Logo / Header */}
        <div className="flex items-center gap-3 px-4 h-16 border-b border-slate-800/80">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-emerald-400 p-[1px] shadow-md shadow-indigo-500/20 flex-shrink-0">
            <div className="w-full h-full bg-slate-950 rounded-[11px] flex items-center justify-center font-black text-xs text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-emerald-400">
              EX
            </div>
          </div>
          {sidebarOpen && (
            <div className="overflow-hidden">
              <span className="font-bold text-base tracking-tight text-white block">
                ExportOS
              </span>
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block truncate">
                {organisation?.name || 'Copilot'}
              </span>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => `
                flex items-center gap-3 px-3 py-2.5 rounded-xl
                transition-all duration-200 group text-sm font-medium
                ${
                  isActive
                    ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/20 shadow-sm shadow-indigo-500/5'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }
              `}
            >
              <span className="text-lg flex-shrink-0">{item.icon}</span>
              {sidebarOpen && <span className="truncate">{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Organisation Info Pill */}
        {sidebarOpen && organisation && (
          <div className="px-4 py-3 mx-3 mb-3 bg-slate-950/60 border border-slate-800/60 rounded-xl text-xs text-slate-400">
            <div className="flex items-center justify-between font-semibold text-slate-300">
              <span>{organisation.country}</span>
              <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]">
                {organisation.default_currency}
              </span>
            </div>
            <p className="text-[10px] text-slate-500 mt-0.5 truncate">
              ID: {organisation.slug}
            </p>
          </div>
        )}

        {/* Collapse Toggle */}
        <div className="px-3 pb-4">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="flex items-center justify-center w-full py-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition"
          >
            <span className={`text-xs transition-transform duration-300 ${sidebarOpen ? '' : 'rotate-180'}`}>
              ◀
            </span>
          </button>
        </div>
      </aside>

      {/* ── Main Content ────────────────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className="flex items-center justify-between px-6 h-16 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur flex-shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-base font-bold text-white tracking-tight">
                {organisation?.name || 'ExportOS Workspace'}
              </span>
              <span className="text-xs px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full font-medium">
                Live
              </span>
            </div>
            <p className="text-xs text-slate-400">
              AI Export Operations Copilot
            </p>
          </div>

          {/* User Profile & Menu */}
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="flex items-center gap-3 p-1.5 rounded-xl hover:bg-slate-800/60 transition"
            >
              <div className="text-right hidden sm:block">
                <div className="text-xs font-semibold text-white">{user?.full_name || 'User'}</div>
                <div className="text-[10px] text-slate-400 font-mono">{user?.role}</div>
              </div>
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-emerald-500 text-white font-bold text-xs flex items-center justify-center shadow-md shadow-indigo-600/20">
                {user?.full_name?.charAt(0).toUpperCase() || 'U'}
              </div>
            </button>

            {userMenuOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-2 z-50 text-sm">
                <div className="px-3 py-2 border-b border-slate-800 mb-1">
                  <p className="text-xs font-semibold text-white">{user?.full_name}</p>
                  <p className="text-[11px] text-slate-400 font-mono truncate">{user?.email}</p>
                  <span
                    className={`inline-block mt-1.5 text-[10px] font-semibold px-2 py-0.5 rounded-md border ${
                      ROLE_BADGES[user?.role] || 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    {user?.role}
                  </span>
                </div>

                <NavLink
                  to="/team"
                  onClick={() => setUserMenuOpen(false)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-slate-300 hover:text-white hover:bg-slate-800/60 rounded-xl transition text-xs"
                >
                  <span>👥</span> Team Members
                </NavLink>

                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-3 py-2 text-rose-400 hover:bg-rose-500/10 rounded-xl transition text-xs text-left mt-1"
                >
                  <span>🚪</span> Sign Out
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto p-6 lg:p-8 bg-slate-950">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
