export type BaseUnit = 'piece' | 'g' | 'ml';

export const UNIT_LABELS: Record<BaseUnit, string> = {
  piece: 'Stück',
  g: 'Gramm',
  ml: 'Milliliter',
};

const numberFormat = (maxFractionDigits: number) =>
  new Intl.NumberFormat('de-DE', { maximumFractionDigits: maxFractionDigits });

/** Formatiert eine Zahl im deutschen Format, z. B. 1234.5 → "1.234,5". */
export function formatNumber(value: number | string, maxFractionDigits = 3): string {
  return numberFormat(maxFractionDigits).format(Number(value));
}

/**
 * Menge in Basiseinheit verständlich darstellen (Spezifikation 9.6).
 * Ab 1.000 g bzw. 1.000 ml wird in kg bzw. l umgerechnet.
 */
export function formatQuantity(value: number | string, unit: BaseUnit): string {
  const n = Number(value);
  if (unit === 'piece') return `${formatNumber(n)} Stück`;
  if (Math.abs(n) >= 1000) return `${formatNumber(n / 1000)} ${unit === 'g' ? 'kg' : 'l'}`;
  return `${formatNumber(n)} ${unit}`;
}

/** ISO-Datum (YYYY-MM-DD) als TT.MM.JJJJ. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '–';
  const [y, m, d] = iso.slice(0, 10).split('-');
  return `${d}.${m}.${y}`;
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(iso),
  );
}
