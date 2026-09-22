/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Base Paper / Neutral palette
        canvas: '#FAFAF8',
        surface: {
          DEFAULT: '#FFFFFF',
          muted: '#F7F7F5',
          subtle: '#F0EFEA',
          hover: '#EFEFEA',
        },
        border: {
          hairline: '#E4E3DF',
          DEFAULT: '#E4E3DF',
          strong: '#D1D0C9',
          focus: '#0E5E52',
        },
        ink: {
          DEFAULT: '#1B1D1F',
          secondary: '#585D63',
          muted: '#848A92',
          faint: '#A6ACB3',
        },
        // Primary Accent - Deep Teal / Forest
        teal: {
          DEFAULT: '#0E5E52',
          dark: '#0C4A40',
          hover: '#13796A',
          subtle: '#E8F2F0',
          border: '#B6D9D2',
        },
        // Secondary Accent - Muted Terracotta / Rust
        terracotta: {
          DEFAULT: '#B5622B',
          dark: '#934E20',
          subtle: '#FDF3EB',
          border: '#F2D3BE',
        },
        // AI Provenance - Reserved strictly for AI-drafted / extracted elements
        ai: {
          DEFAULT: '#7C3AED',
          subtle: '#F5F3FF',
          border: '#DDD6FE',
          text: '#6D28D9',
        },
        // 8 Semantic Deal States
        state: {
          inquiry: { bg: '#F1F5F9', text: '#475569', dot: '#64748B', border: '#CBD5E1' },
          quoted: { bg: '#FEF3C7', text: '#92400E', dot: '#D97706', border: '#FDE68A' },
          confirmed: { bg: '#E8F2F0', text: '#0C4A40', dot: '#0E5E52', border: '#B6D9D2' },
          in_production: { bg: '#EEF2FF', text: '#3730A3', dot: '#4F46E5', border: '#C7D2FE' },
          docs_ready: { bg: '#ECFEFF', text: '#155E75', dot: '#0891B2', border: '#A5F3FC' },
          shipped: { bg: '#EFF6FF', text: '#1E40AF', dot: '#2563EB', border: '#BFDBFE' },
          paid: { bg: '#F0FDF4', text: '#166534', dot: '#16A34A', border: '#BBF7D0' },
          closed: { bg: '#F1F5F9', text: '#334155', dot: '#475569', border: '#94A3B8' },
          cancelled: { bg: '#FEF2F2', text: '#991B1B', dot: '#DC2626', border: '#FECACA' },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '4px',
        sm: '4px',
        md: '6px',
        lg: '8px',
      },
      boxShadow: {
        'subtle': '0 1px 2px 0 rgba(27, 29, 31, 0.04)',
        'modal': '0 12px 32px -4px rgba(27, 29, 31, 0.12), 0 4px 12px -2px rgba(27, 29, 31, 0.06)',
        'dropdown': '0 4px 16px -2px rgba(27, 29, 31, 0.08), 0 2px 6px -1px rgba(27, 29, 31, 0.04)',
      },
    },
  },
  plugins: [],
}
