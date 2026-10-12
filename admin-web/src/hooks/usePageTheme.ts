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

  const border = L ? '#e4d9c8' : '#1e293b';
  const accent = '#D95D2B';

  return {
    L,
    heading: L ? '#282820' : '#f8fafc',
    sub: L ? '#6b6150' : '#94a3b8',
    muted: L ? '#8a7e69' : '#64748b',
    value: L ? '#282820' : '#f8fafc',
    accent,
    border,

    card: {
      backgroundColor: L ? '#ffffff' : 'rgba(15,23,42,0.9)',
      border: `1px solid ${border}`,
    },
    cardInner: {
      backgroundColor: L ? '#faf7f2' : '#020617',
      border: `1px solid ${border}`,
    },
    tableWrap: {
      backgroundColor: L ? '#ffffff' : 'rgba(15,23,42,0.6)',
      border: `1px solid ${border}`,
    },
    thead: {
      backgroundColor: L ? '#f5f0e8' : 'rgba(2,6,23,0.7)',
      borderBottomColor: border,
      color: L ? '#6b6150' : '#94a3b8',
    },
    tbodyRow: {
      color: L ? '#282820' : '#cbd5e1',
    },
    tbodyRowHover: {
      backgroundColor: L ? '#fef3e2' : 'rgba(30,41,59,0.4)',
    },
    emptyState: {
      backgroundColor: L ? '#faf7f2' : 'rgba(15,23,42,0.4)',
      border: `1px solid ${border}`,
      color: L ? '#756a56' : '#64748b',
    },
    input: {
      backgroundColor: L ? '#faf7f2' : '#0f172a',
      border: `1px solid ${border}`,
      color: L ? '#282820' : '#f8fafc',
    },
    select: {
      backgroundColor: L ? '#faf7f2' : '#0f172a',
      border: `1px solid ${border}`,
      color: L ? '#282820' : '#f8fafc',
    },
    tabActive: {
      backgroundColor: accent,
      color: '#ffffff',
      boxShadow: `0 2px 8px rgba(217,93,43,0.35)`,
      border: `1px solid transparent`,
    },
    tabInactive: {
      backgroundColor: L ? '#faf7f2' : '#0f172a',
      color: L ? '#5a5545' : '#94a3b8',
      border: `1px solid ${border}`,
    },
    modal: {
      backgroundColor: L ? 'rgba(0,0,0,0.5)' : 'rgba(0,0,0,0.75)',
    },
    modalInner: {
      backgroundColor: L ? '#ffffff' : '#0f172a',
      border: `1px solid ${border}`,
    },
    divider: border,
  };
}
