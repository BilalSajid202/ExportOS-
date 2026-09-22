import React from 'react';

/**
 * Tradeloop Standard Deal State Badge
 * Rule: Small colored dot + text label. Fixed consistent palette per §3.2.
 */

export const STATE_CONFIG = {
  INQUIRY: {
    label: 'Inquiry',
    dot: 'bg-slate-500',
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    border: 'border-slate-300',
  },
  QUOTED: {
    label: 'Quoted',
    dot: 'bg-amber-500',
    bg: 'bg-amber-50',
    text: 'text-amber-800',
    border: 'border-amber-200',
  },
  CONFIRMED: {
    label: 'Confirmed',
    dot: 'bg-[#0E5E52]',
    bg: 'bg-[#E8F2F0]',
    text: 'text-[#0C4A40]',
    border: 'border-[#B6D9D2]',
  },
  IN_PRODUCTION: {
    label: 'In Production',
    dot: 'bg-indigo-500',
    bg: 'bg-indigo-50',
    text: 'text-indigo-800',
    border: 'border-indigo-200',
  },
  DOCS_READY: {
    label: 'Docs Ready',
    dot: 'bg-cyan-600',
    bg: 'bg-cyan-50',
    text: 'text-cyan-800',
    border: 'border-cyan-200',
  },
  SHIPPED: {
    label: 'Shipped',
    dot: 'bg-blue-600',
    bg: 'bg-blue-50',
    text: 'text-blue-800',
    border: 'border-blue-200',
  },
  PAID: {
    label: 'Paid',
    dot: 'bg-emerald-600',
    bg: 'bg-emerald-50',
    text: 'text-emerald-800',
    border: 'border-emerald-200',
  },
  CLOSED: {
    label: 'Closed',
    dot: 'bg-slate-600',
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    border: 'border-slate-300',
  },
  CANCELLED: {
    label: 'Cancelled',
    dot: 'bg-red-500',
    bg: 'bg-red-50',
    text: 'text-red-700 line-through',
    border: 'border-red-200',
  },
};

export default function StateBadge({ state, size = 'md', className = '' }) {
  const normState = (state || 'INQUIRY').toUpperCase();
  const config = STATE_CONFIG[normState] || STATE_CONFIG.INQUIRY;

  const sizeClasses = {
    sm: 'px-1.5 py-0.5 text-[11px] gap-1.5',
    md: 'px-2 py-0.5 text-xs gap-1.5 font-medium',
    lg: 'px-2.5 py-1 text-xs gap-2 font-medium',
  };

  return (
    <span
      className={`inline-flex items-center rounded border ${config.bg} ${config.text} ${config.border} ${sizeClasses[size]} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${config.dot}`} />
      <span>{config.label}</span>
    </span>
  );
}
