import { useState, useEffect } from 'react';
import api from '../lib/api';

/* ── Status Badge Component ───────────────────────────────── */
function StatusBadge({ status }) {
  const config = {
    connected: { dot: 'status-dot--healthy', text: 'Connected', textColor: 'var(--color-success)' },
    disconnected: { dot: 'status-dot--unhealthy', text: 'Disconnected', textColor: 'var(--color-error)' },
    loading: { dot: 'status-dot--loading', text: 'Checking...', textColor: 'var(--color-warning)' },
  };

  const { dot, text, textColor } = config[status] || config.loading;

  return (
    <div className="flex items-center gap-2">
      <span className={`status-dot ${dot}`} />
      <span className="text-sm font-medium" style={{ color: textColor }}>
        {text}
      </span>
    </div>
  );
}

/* ── Stat Card (Placeholder for future widgets) ───────────── */
function StatCard({ icon, label, value, delay = 0 }) {
  return (
    <div
      className="glass-card p-5 animate-fade-in"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-center gap-3 mb-3">
        <span className="text-2xl">{icon}</span>
        <span className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
          {label}
        </span>
      </div>
      <div className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
        {value}
      </div>
    </div>
  );
}

/* ── Dashboard Page ───────────────────────────────────────── */
export default function Dashboard() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({
    deals: null,
    products: null,
    inventory: null,
    lowStock: null,
  });

  useEffect(() => {
    async function fetchHealth() {
      try {
        setLoading(true);
        const data = await api.get('/health');
        setHealth(data);
        setError(null);
      } catch (err) {
        setError(err.message || 'Failed to connect to backend');
        setHealth(null);
      } finally {
        setLoading(false);
      }
    }

    async function fetchStats() {
      try {
        const [deals, products, inventory] = await Promise.all([
          api.get('/deals'),
          api.get('/products'),
          api.get('/inventory'),
        ]);
        setStats({
          deals: deals.length,
          products: products.length,
          inventory: inventory.length,
          lowStock: inventory.filter((i) => i.is_low_stock).length,
        });
      } catch {
        // Stats are optional on dashboard — auth may still be hydrating
      }
    }

    fetchHealth();
    fetchStats();

    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const backendStatus = loading ? 'loading' : health ? 'connected' : 'disconnected';
  const dbStatus = loading ? 'loading' : health?.database === 'connected' ? 'connected' : 'disconnected';

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Page Title */}
      <div className="animate-fade-in">
        <h2 className="text-2xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
          Dashboard
        </h2>
        <p className="mt-1 text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          System overview and inventory-aware operations
        </p>
      </div>

      {/* System Health Card */}
      <div className="glass-card p-6 animate-fade-in" style={{ animationDelay: '100ms' }}>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold" style={{ color: 'var(--color-text-primary)' }}>
              System Health
            </h3>
            <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
              Real-time backend and database connectivity
            </p>
          </div>
          {health && (
            <span
              className="text-xs px-3 py-1 rounded-full font-medium"
              style={{
                background: 'rgba(99, 102, 241, 0.15)',
                color: 'var(--color-accent-hover)',
              }}
            >
              v{health.version} • {health.environment}
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div
            className="flex items-center justify-between p-4 rounded-lg"
            style={{ background: 'rgba(15, 23, 42, 0.5)', border: '1px solid var(--color-border)' }}
          >
            <div className="flex items-center gap-3">
              <span className="text-xl">⚡</span>
              <div>
                <div className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                  FastAPI Backend
                </div>
                <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                  localhost:8000
                </div>
              </div>
            </div>
            <StatusBadge status={backendStatus} />
          </div>

          <div
            className="flex items-center justify-between p-4 rounded-lg"
            style={{ background: 'rgba(15, 23, 42, 0.5)', border: '1px solid var(--color-border)' }}
          >
            <div className="flex items-center gap-3">
              <span className="text-xl">🗄️</span>
              <div>
                <div className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                  PostgreSQL
                </div>
                <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                  localhost:5432/exportos
                </div>
              </div>
            </div>
            <StatusBadge status={dbStatus} />
          </div>
        </div>

        {error && (
          <div
            className="mt-4 p-3 rounded-lg text-sm"
            style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              color: 'var(--color-error)',
            }}
          >
            ⚠️ {error}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon="📋" label="Active Deals" value={stats.deals ?? '—'} delay={200} />
        <StatCard icon="📦" label="Products" value={stats.products ?? '—'} delay={300} />
        <StatCard icon="🏭" label="Inventory Items" value={stats.inventory ?? '—'} delay={400} />
        <StatCard icon="⚠️" label="Low Stock" value={stats.lowStock ?? '—'} delay={500} />
      </div>

      <div className="glass-card p-5 animate-fade-in" style={{ animationDelay: '600ms' }}>
        <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--color-text-secondary)' }}>
          Implementation Progress
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs" style={{ color: 'var(--color-text-muted)' }}>
          <div className="flex items-center gap-2">
            <span style={{ color: 'var(--color-success)' }}>✓</span> Phase 0 — Foundation
          </div>
          <div className="flex items-center gap-2">
            <span style={{ color: 'var(--color-success)' }}>✓</span> Phase 1 — Auth & Organisation
          </div>
          <div className="flex items-center gap-2">
            <span style={{ color: 'var(--color-success)' }}>✓</span> Phase 2 — Product Catalogue
          </div>
          <div className="flex items-center gap-2">
            <span style={{ color: 'var(--color-success)' }}>✓</span> Phase 3 — Inventory System
          </div>
          <div className="flex items-center gap-2">
            <span style={{ color: 'var(--color-text-muted)' }}>○</span> Phase 4 — Full Deal State Machine
          </div>
          <div className="flex items-center gap-2">
            <span style={{ color: 'var(--color-text-muted)' }}>○</span> Phase 5+ — Inquiry & AI
          </div>
        </div>
      </div>
    </div>
  );
}
