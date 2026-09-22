import { useState } from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  DashboardIcon,
  InquiriesIcon,
  DealsIcon,
  ProductsIcon,
  InventoryIcon,
  CopilotIcon,
  TeamIcon,
  SearchIcon,
  BellIcon,
  UserIcon,
  LogoutIcon,
  ChevronRightIcon
} from './common/Icons';

/* ── Sidebar Navigation Items ─────────────────────────────── */
const navItems = [
  { to: '/', icon: DashboardIcon, label: 'Dashboard' },
  { to: '/inquiries', icon: InquiriesIcon, label: 'Inquiries' },
  { to: '/deals', icon: DealsIcon, label: 'Deals' },
  { to: '/products', icon: ProductsIcon, label: 'Products' },
  { to: '/inventory', icon: InventoryIcon, label: 'Inventory' },
  { to: '/copilot', icon: CopilotIcon, label: 'Copilot' },
  { to: '/team', icon: TeamIcon, label: 'Team' },
];

const ROLE_BADGES = {
  ADMIN: 'bg-slate-100 text-slate-700 border-slate-300',
  EXPORT_MANAGER: 'bg-[#E8F2F0] text-[#0C4A40] border-[#B6D9D2]',
  DOCUMENTATION_OFFICER: 'bg-cyan-50 text-cyan-800 border-cyan-200',
  SALES: 'bg-amber-50 text-amber-800 border-amber-200',
  ACCOUNTS: 'bg-emerald-50 text-emerald-800 border-emerald-200',
};

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [currency, setCurrency] = useState('USD');
  const [globalSearch, setGlobalSearch] = useState('');
  const { user, organisation, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Compute breadcrumb title
  const getPageTitle = () => {
    const path = location.pathname;
    if (path === '/') return 'Executive Dashboard';
    if (path.startsWith('/inquiries')) return 'Inquiries';
    if (path.startsWith('/deals')) return 'Deals & Operations';
    if (path.startsWith('/products')) return 'Product Catalog';
    if (path.startsWith('/inventory')) return 'Inventory & Reservations';
    if (path.startsWith('/copilot')) return 'Export Copilot';
    if (path.startsWith('/team')) return 'Team & Access';
    return 'Export Operations';
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#FAFAF8] text-[#1B1D1F] antialiased">
      {/* ── Sidebar ─────────────────────────────────────────── */}
      <aside
        className={`
          flex flex-col border-r border-[#E4E3DF] bg-[#FFFFFF]
          transition-all duration-200 ease-in-out z-20 flex-shrink-0
          ${sidebarOpen ? 'w-60' : 'w-16'}
        `}
      >
        {/* Logo / Org Header */}
        <div className="flex items-center justify-between px-4 h-14 border-b border-[#E4E3DF]">
          <div className="flex items-center gap-2.5 overflow-hidden">
            {/* Tradeloop Teal Monogram */}
            <div className="w-8 h-8 rounded bg-[#0E5E52] flex items-center justify-center flex-shrink-0 text-white font-mono font-bold text-xs tracking-tight shadow-sm">
              TL
            </div>
            {sidebarOpen && (
              <div className="overflow-hidden leading-tight">
                <span className="font-semibold text-sm tracking-tight text-[#1B1D1F] block">
                  Tradeloop
                </span>
                <span className="text-[10.5px] font-mono text-[#848A92] uppercase tracking-wider block truncate">
                  {organisation?.name || 'SME Export OS'}
                </span>
              </div>
            )}
          </div>

          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="text-[#848A92] hover:text-[#1B1D1F] p-1 rounded hover:bg-[#F7F7F5] transition"
            title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            <span className="font-mono text-xs">{sidebarOpen ? '‹' : '›'}</span>
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) => `
                  flex items-center gap-3 px-2.5 py-2 rounded text-[13.5px] font-medium
                  transition-colors duration-150 group
                  ${
                    isActive
                      ? 'bg-[#E8F2F0] text-[#0C4A40] font-semibold'
                      : 'text-[#585D63] hover:text-[#1B1D1F] hover:bg-[#F7F7F5]'
                  }
                `}
                title={!sidebarOpen ? item.label : undefined}
              >
                <Icon className={`w-4 h-4 flex-shrink-0 transition-colors ${
                  location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to))
                    ? 'text-[#0E5E52]' 
                    : 'text-[#848A92] group-hover:text-[#1B1D1F]'
                }`} />
                {sidebarOpen && <span className="truncate">{item.label}</span>}
              </NavLink>
            );
          })}
        </nav>

        {/* SBP Realization Status Pill */}
        {sidebarOpen && (
          <div className="mx-2 mb-2 p-2 rounded bg-[#F7F7F5] border border-[#E4E3DF] text-[11px] text-[#585D63]">
            <div className="flex items-center justify-between font-mono font-medium text-[#1B1D1F] mb-0.5">
              <span>SBP FX E-Form</span>
              <span className="text-[#0E5E52] text-[10px] bg-[#E8F2F0] px-1 py-0.2 rounded">ACTIVE</span>
            </div>
            <p className="text-[10px] text-[#848A92] leading-tight">
              120-Day realization tracking enabled
            </p>
          </div>
        )}

        {/* Bottom User Area */}
        <div className="p-2 border-t border-[#E4E3DF] bg-[#FFFFFF]">
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="w-full flex items-center gap-2.5 p-1.5 rounded hover:bg-[#F7F7F5] transition text-left"
            >
              <div className="w-7 h-7 rounded bg-[#F0EFEA] border border-[#E4E3DF] text-[#1B1D1F] font-mono font-semibold text-xs flex items-center justify-center flex-shrink-0">
                {user?.full_name?.charAt(0).toUpperCase() || 'U'}
              </div>
              {sidebarOpen && (
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-semibold text-[#1B1D1F] truncate leading-tight">
                    {user?.full_name || 'Exporter Admin'}
                  </div>
                  <div className="text-[10.5px] font-mono text-[#848A92] truncate">
                    {user?.role || 'EXPORT_MANAGER'}
                  </div>
                </div>
              )}
            </button>

            {userMenuOpen && (
              <div className="absolute bottom-full left-0 mb-1.5 w-56 bg-[#FFFFFF] border border-[#E4E3DF] rounded shadow-dropdown p-1.5 z-50 text-xs">
                <div className="px-2.5 py-2 border-b border-[#E4E3DF] mb-1">
                  <p className="font-semibold text-[#1B1D1F] truncate">{user?.full_name || 'Exporter Staff'}</p>
                  <p className="font-mono text-[10.5px] text-[#848A92] truncate">{user?.email || 'ops@sme-export.pk'}</p>
                  <span
                    className={`inline-block mt-1.5 text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                      ROLE_BADGES[user?.role] || 'bg-slate-100 text-slate-700 border-slate-300'
                    }`}
                  >
                    {user?.role || 'EXPORT_MANAGER'}
                  </span>
                </div>

                <NavLink
                  to="/team"
                  onClick={() => setUserMenuOpen(false)}
                  className="flex items-center gap-2 px-2.5 py-1.5 text-[#585D63] hover:text-[#1B1D1F] hover:bg-[#F7F7F5] rounded transition"
                >
                  <TeamIcon className="w-3.5 h-3.5 text-[#848A92]" />
                  <span>Team & Permissions</span>
                </NavLink>

                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 text-red-700 hover:bg-red-50 rounded transition text-left mt-0.5"
                >
                  <LogoutIcon className="w-3.5 h-3.5 text-red-600" />
                  <span>Sign Out</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* ── Main Operations Canvas ──────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[#FAFAF8]">
        {/* Top Operational Bar (Thin 48px header) */}
        <header className="h-12 border-b border-[#E4E3DF] bg-[#FFFFFF] px-6 flex items-center justify-between flex-shrink-0">
          {/* Breadcrumb & Context */}
          <div className="flex items-center gap-2 text-xs font-medium">
            <span className="text-[#848A92]">Tradeloop</span>
            <span className="text-[#D1D0C9]">/</span>
            <span className="text-[#1B1D1F] font-semibold">{getPageTitle()}</span>
          </div>

          {/* Right Operational Controls */}
          <div className="flex items-center gap-3">
            {/* Global Search */}
            <div className="relative hidden md:block">
              <input
                type="text"
                value={globalSearch}
                onChange={(e) => setGlobalSearch(e.target.value)}
                placeholder="Search deals, SKUs, buyers, HS codes..."
                className="w-64 pl-8 pr-3 py-1 bg-[#F7F7F5] border border-[#E4E3DF] rounded text-xs text-[#1B1D1F] placeholder-[#848A92] focus:outline-none focus:border-[#0E5E52] focus:bg-white transition"
              />
              <SearchIcon className="w-3.5 h-3.5 text-[#848A92] absolute left-2.5 top-1/2 -translate-y-1/2" />
            </div>

            {/* Currency Switcher */}
            <div className="inline-flex items-center rounded border border-[#E4E3DF] bg-[#F7F7F5] p-0.5 text-xs font-mono">
              <button
                type="button"
                onClick={() => setCurrency('USD')}
                className={`px-2 py-0.5 rounded text-[11px] font-semibold transition ${
                  currency === 'USD' 
                    ? 'bg-[#FFFFFF] text-[#0E5E52] shadow-subtle' 
                    : 'text-[#848A92] hover:text-[#1B1D1F]'
                }`}
              >
                USD
              </button>
              <button
                type="button"
                onClick={() => setCurrency('PKR')}
                className={`px-2 py-0.5 rounded text-[11px] font-semibold transition ${
                  currency === 'PKR' 
                    ? 'bg-[#FFFFFF] text-[#0E5E52] shadow-subtle' 
                    : 'text-[#848A92] hover:text-[#1B1D1F]'
                }`}
              >
                PKR
              </button>
            </div>

            {/* Quick SBP FX Alert Indicator */}
            <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded bg-[#E8F2F0] border border-[#B6D9D2] text-[11px] font-mono text-[#0C4A40]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#0E5E52]" />
              <span>SBP: 278.50 PKR/USD</span>
            </div>
          </div>
        </header>

        {/* Page Content Body */}
        <div className="flex-1 overflow-y-auto p-5 lg:p-6 bg-[#FAFAF8]">
          <Outlet context={{ currency, globalSearch }} />
        </div>
      </main>
    </div>
  );
}
