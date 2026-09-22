import React from 'react';

/**
 * Tradeloop Standard Confidence Chip
 * AI-provenance color (neutral violet / dashed border) reserved exclusively for AI extracted data.
 */
export default function ConfidenceChip({ confidence, sourceEvidence, onEvidenceClick, size = 'sm' }) {
  const score = typeof confidence === 'number' 
    ? Math.round(confidence <= 1 ? confidence * 100 : confidence) 
    : 95;

  let colorClass = 'text-purple-700 bg-purple-50 border-purple-200';
  let barColor = 'bg-purple-600';

  if (score < 70) {
    colorClass = 'text-amber-800 bg-amber-50 border-amber-200';
    barColor = 'bg-amber-600';
  }

  return (
    <div className="inline-flex items-center gap-1.5 font-mono">
      <span
        title={sourceEvidence ? `Extracted with ${score}% confidence` : undefined}
        className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[11px] font-medium ${colorClass}`}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-purple-500 flex-shrink-0" />
        <span>{score}%</span>
      </span>

      {sourceEvidence && onEvidenceClick && (
        <button
          type="button"
          onClick={onEvidenceClick}
          className="text-[10px] font-sans text-purple-700 hover:text-purple-900 underline underline-offset-2 transition"
          title={`View source quote: "${sourceEvidence.slice(0, 60)}..."`}
        >
          evidence
        </button>
      )}
    </div>
  );
}
