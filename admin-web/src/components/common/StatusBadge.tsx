import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

interface Tone {
  bg: string;
  text: string;
  border: string;
}

// Light pastel background + dark text of the same hue keeps every badge readable on white tables.
const TONES = {
  green: { bg: '#dcfce7', text: '#166534', border: '#86efac' },
  amber: { bg: '#fef3c7', text: '#92400e', border: '#fcd34d' },
  blue: { bg: '#dbeafe', text: '#1e40af', border: '#93c5fd' },
  orange: { bg: '#ffedd5', text: '#9a3412', border: '#fdba74' },
  teal: { bg: '#ccfbf1', text: '#115e59', border: '#5eead4' },
  rose: { bg: '#ffe4e6', text: '#9f1239', border: '#fda4af' },
  purple: { bg: '#f3e8ff', text: '#6b21a8', border: '#d8b4fe' },
  slate: { bg: '#f1f5f9', text: '#334155', border: '#cbd5e1' },
} satisfies Record<string, Tone>;

function toneFor(status: string): Tone {
  switch (status) {
    case 'PLACED':
    case 'OCCUPIED':
    case 'ISSUED':
    case 'LOCKED':
      return TONES.amber;
    case 'ACCEPTED':
      return TONES.blue;
    case 'PREPARING':
      return TONES.orange;
    case 'READY':
    case 'AVAILABLE':
    case 'COMPLETED':
    case 'PAID':
    case 'ACTIVE':
      return TONES.green;
    case 'SERVED':
      return TONES.teal;
    case 'CANCELLED':
    case 'REJECTED':
    case 'DISABLED':
      return TONES.rose;
    case 'VOIDED_FOR_REVISION':
      return TONES.purple;
    default:
      return TONES.slate;
  }
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normalized = (status || '').toUpperCase() || 'UNKNOWN';
  const tone = toneFor(normalized);
  const sizeClasses = size === 'sm' ? 'px-2.5 py-0.5 text-xs' : 'px-3 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full border font-bold tracking-wide ${sizeClasses}`}
      style={{ backgroundColor: tone.bg, color: tone.text, borderColor: tone.border }}
    >
      {normalized}
    </span>
  );
};
