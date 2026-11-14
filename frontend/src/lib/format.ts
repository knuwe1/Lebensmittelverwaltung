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

export const PACKAGE_UNIT_LABELS: Record<string, string> = {
  piece: 'Stück',
  g: 'g',
  kg: 'kg',
  ml: 'ml',
  l: 'l',
};

export const COMPATIBLE_PACKAGE_UNITS: Record<BaseUnit, string[]> = {
  piece: ['piece'],
  g: ['g', 'kg'],
  ml: ['ml', 'l'],
};

export const EXPIRY_TYPE_LABELS: Record<string, string> = {
  best_before: 'Mindestens haltbar bis (MHD)',
  use_by: 'Zu verbrauchen bis',
  none: 'Kein Haltbarkeitsdatum',
  unknown: 'Datum unbekannt',
};

export function variantLabel(v: {
  name: string | null;
  package_quantity: number;
  package_unit: string;
}): string {
  const size = `${formatNumber(v.package_quantity)} ${PACKAGE_UNIT_LABELS[v.package_unit] ?? v.package_unit}`;
  return v.name ? `${v.name} (${size})` : size;
}

/** Lokales Datum als ISO-String (YYYY-MM-DD), ohne Zeitzonenverschiebung. */
export function toIsoDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function fromIsoDate(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d);
}

/** Kurzbezeichnung der Basiseinheit für Beschriftungen, z. B. "Menge (g)". */
export function unitShort(unit: BaseUnit): string {
  return unit === 'piece' ? 'Stück' : unit;
}
