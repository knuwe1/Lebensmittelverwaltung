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

export const MOVEMENT_LABELS: Record<string, string> = {
  receipt: 'Einlagerung',
  consumption: 'Verbrauch',
  transfer_out: 'Umlagerung (Abgang)',
  transfer_in: 'Umlagerung (Zugang)',
  inventory_correction: 'Inventurkorrektur',
  disposal: 'Entsorgung',
  reversal: 'Storno',
};

export const DISPOSAL_REASONS: Record<string, string> = {
  expired: 'Haltbarkeit überschritten',
  spoiled: 'Verdorben',
  damaged: 'Beschädigt',
  other: 'Sonstiger Grund',
};

/** Haltbarkeitsstatus einer Position (vereinfachte Vorstufe zu FR-EXP-003, Phase 5). */
export function isExpired(item: { expiry_type: string; expiry_date: string | null }, today = new Date()): boolean {
  return !!item.expiry_date && item.expiry_date < toIsoDate(today);
}

/**
 * Liest ein deutsch eingegebenes Datum (Spez. 9.6), wie es von Verpackungen abgetippt wird:
 * "20.11.2027", "20.11.27", "20.11." (aktuelles/nächstes Jahr), "201127", "20112027",
 * auch mit "/" oder "-" als Trenner. Zweistellige Jahre werden als 20xx gelesen.
 * Ungültige Angaben (z. B. 31.02.) liefern null.
 */
export function parseGermanDate(input: string, today = new Date()): Date | null {
  const s = input.trim();
  if (!s) return null;
  let d: number, m: number, y: number | undefined;
  const sep = s.match(/^(\d{1,2})[./-](\d{1,2})[./-]?(\d{2}|\d{4})?$/);
  const compact = s.match(/^(\d{2})(\d{2})(\d{2}|\d{4})$/);
  if (sep) {
    [d, m] = [Number(sep[1]), Number(sep[2])];
    y = sep[3] ? Number(sep[3]) : undefined;
  } else if (compact) {
    [d, m, y] = [Number(compact[1]), Number(compact[2]), Number(compact[3])];
  } else {
    return null;
  }
  if (y === undefined) {
    // Ohne Jahr: nächstes Vorkommen dieses Tages (Haltbarkeitsdaten liegen in der Zukunft)
    y = today.getFullYear();
    const candidate = new Date(y, m - 1, d);
    if (candidate < new Date(today.getFullYear(), today.getMonth(), today.getDate())) y += 1;
  } else if (y < 100) {
    y += 2000;
  }
  const date = new Date(y, m - 1, d);
  if (date.getFullYear() !== y || date.getMonth() !== m - 1 || date.getDate() !== d) return null;
  return date;
}
