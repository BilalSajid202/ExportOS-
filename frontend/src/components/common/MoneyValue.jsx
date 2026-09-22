import React from 'react';

/**
 * Tradeloop Standard Money Value Component
 * Rule: Always tabular-nums, always shows currency code to avoid ambiguity between USD/PKR.
 */
export default function MoneyValue({ 
  amount = 0, 
  currency = 'USD', 
  exchangeRate = 278.5, 
  showBoth = false,
  className = '' 
}) {
  const num = Number(amount) || 0;
  
  const formattedPrimary = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);

  const converted = currency === 'USD' ? num * exchangeRate : num / exchangeRate;
  const secondaryCurrency = currency === 'USD' ? 'PKR' : 'USD';
  const formattedSecondary = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(converted);

  return (
    <span className={`tabular-nums font-mono text-[13px] inline-flex items-baseline gap-1 ${className}`}>
      <span className="font-semibold text-ink">{formattedPrimary}</span>
      <span className="text-[10px] font-sans font-medium text-ink-muted uppercase tracking-wider">{currency}</span>
      {showBoth && (
        <span className="text-[11px] text-ink-muted font-sans ml-1">
          (≈ {formattedSecondary} {secondaryCurrency})
        </span>
      )}
    </span>
  );
}
