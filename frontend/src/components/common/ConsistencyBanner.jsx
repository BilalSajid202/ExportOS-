import React from 'react';
import { CheckIcon, AlertTriangleIcon, InfoIcon } from './Icons';

/**
 * Tradeloop Document Consistency & Compliance Banner
 * 3 tones: 'checking' (neutral), 'clear' (green), 'issues' (amber with specific itemized count)
 */
export default function ConsistencyBanner({ 
  status = 'clear', // 'checking' | 'clear' | 'issues'
  issues = [], 
  totalChecked = 4,
  className = '' 
}) {
  if (status === 'checking') {
    return (
      <div className={`p-3 rounded border border-border bg-surface-muted text-xs text-ink-secondary flex items-center justify-between ${className}`}>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-slate-400 animate-pulse" />
          <span>Cross-checking {totalChecked} documents against Incoterms & SBP regulations...</span>
        </div>
      </div>
    );
  }

  if (status === 'clear' || issues.length === 0) {
    return (
      <div className={`p-3 rounded border border-emerald-200 bg-emerald-50/70 text-xs text-emerald-900 flex items-center justify-between ${className}`}>
        <div className="flex items-center gap-2 font-medium">
          <CheckIcon className="w-4 h-4 text-emerald-700" />
          <span>All {totalChecked} documents match: values, HS codes, weights, and consignee data are fully consistent.</span>
        </div>
        <span className="text-[11px] font-mono text-emerald-700 font-semibold uppercase tracking-wider">
          PASSED
        </span>
      </div>
    );
  }

  return (
    <div className={`p-3.5 rounded border border-amber-300 bg-amber-50 text-xs text-amber-950 ${className}`}>
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2 font-semibold text-amber-900">
          <AlertTriangleIcon className="w-4 h-4 text-amber-700 flex-shrink-0" />
          <span>Document Consistency Alert — {issues.length} {issues.length === 1 ? 'mismatch' : 'mismatches'} found</span>
        </div>
        <span className="px-1.5 py-0.5 rounded bg-amber-200/80 text-amber-900 font-mono text-[10px] font-semibold">
          ACTION REQUIRED
        </span>
      </div>

      <ul className="mt-2 space-y-1 text-[12px] text-amber-900/90 pl-6 list-disc">
        {issues.map((issue, idx) => (
          <li key={idx}>
            <span className="font-semibold">{issue.field || issue.docType}: </span>
            {issue.message || issue.description || issue}
          </li>
        ))}
      </ul>
    </div>
  );
}
