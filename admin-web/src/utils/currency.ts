/**
 * Currency formatting utilities for INR.
 */

export function formatInr(amount: string | number | null | undefined): string {
  if (amount === null || amount === undefined || amount === '') {
    return '₹0.00';
  }
  const numeric = typeof amount === 'number' ? amount : parseFloat(amount);
  if (isNaN(numeric)) {
    return '₹0.00';
  }
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numeric);
}
