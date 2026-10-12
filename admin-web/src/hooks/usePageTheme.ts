/**
 * usePageTheme — returns pre-computed style objects and primitives
 * that every admin page can use for consistent light/dark theming.
 */
import { useTheme } from '@/context/ThemeContext';

export interface PageTheme {
  L: boolean;                    // true = light mode
  heading: string;               // text color for page headings
  sub: string;                   // text color for subtitles/secondary text
  muted: string;                 // muted text
  value: string;                 // high-contrast values (numbers, ids)
  accent: string;                // SpiceHub orange
  border: string;                // border-color value
  // Surfaces
  card: React.CSSProperties;     // main card/panel
  cardInner: React.CSSProperties;// inner inset card
  tableWrap: React.CSSProperties;// table wrapper
  thead: React.CSSProperties;    // table head row
  tbodyRow: React.CSSProperties; // table data row (base)
  tbodyRowHover: React.CSSProperties; // table data row hover
  emptyState: React.CSSProperties;
  // Inputs
  input: React.CSSProperties;
  select: React.CSSProperties;
  // Tab buttons
  tabActive: React.CSSProperties;
  tabInactive: React.CSSProperties;
  // Modal
  modal: React.CSSProperties;
  modalInner: React.CSSProperties;
  // Divider
  divider: string;
}

export function usePageTheme(): PageTheme {
  const { theme } = useTheme();
  const L = theme === 'light';

  const border = '#e2e8f0';
  const accent = '#D95D2B';

  return {
    L,
    heading: '#0f172a',
    sub: '#475569',
    muted: '#64748b',
    value: '#0f172a',
    accent,
    border,

    card: {
      backgroundColor: '#ffffff',
      border: `1px solid ${border}`,
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
    },
    cardInner: {
      backgroundColor: '#f8fafc',
      border: `1px solid ${border}`,
    },
    tableWrap: {
      backgroundColor: '#ffffff',
      border: `1px solid ${border}`,
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05)',
    },
    thead: {
      backgroundColor: '#f8fafc',
      borderBottomColor: border,
      color: '#475569',
    },
    tbodyRow: {
      color: '#0f172a',
    },
    tbodyRowHover: {
      backgroundColor: '#f1f5f9',
    },
    emptyState: {
      backgroundColor: '#f8fafc',
      border: `1px solid ${border}`,
      color: '#64748b',
    },
    input: {
      backgroundColor: '#ffffff',
      border: '1px solid #cbd5e1',
      color: '#0f172a',
    },
    select: {
      backgroundColor: '#ffffff',
      border: '1px solid #cbd5e1',
      color: '#0f172a',
    },
    tabActive: {
      backgroundColor: accent,
      color: '#ffffff',
      boxShadow: '0 2px 8px rgba(217,93,43,0.3)',
      border: '1px solid transparent',
    },
    tabInactive: {
      backgroundColor: '#ffffff',
      color: '#475569',
      border: `1px solid ${border}`,
    },
    modal: {
      backgroundColor: 'rgba(15,23,42,0.4)',
    },
    modalInner: {
      backgroundColor: '#ffffff',
      border: `1px solid ${border}`,
      boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
    },
    divider: border,
  };
}
