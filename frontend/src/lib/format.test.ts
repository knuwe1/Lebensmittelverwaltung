import { describe, expect, it } from 'vitest';
import { formatDate, formatNumber, formatQuantity } from './format';

describe('format', () => {
  it('formatiert Zahlen deutsch', () => {
    expect(formatNumber(1234.5)).toBe('1.234,5');
  });

  it('formatiert Mengen mit sinnvoller Einheit', () => {
    expect(formatQuantity(250, 'g')).toBe('250 g');
    expect(formatQuantity(2000, 'g')).toBe('2 kg');
    expect(formatQuantity(1500, 'ml')).toBe('1,5 l');
    expect(formatQuantity(3, 'piece')).toBe('3 Stück');
    expect(formatQuantity('0.5', 'piece')).toBe('0,5 Stück');
  });

  it('formatiert Datum', () => {
    expect(formatDate('2026-11-20')).toBe('20.11.2026');
    expect(formatDate(null)).toBe('–');
  });
});

import { fromIsoDate, toIsoDate, variantLabel } from './format';

describe('Varianten und Datum', () => {
  it('beschriftet Varianten', () => {
    expect(variantLabel({ name: null, package_quantity: 1.5, package_unit: 'kg' })).toBe('1,5 kg');
    expect(variantLabel({ name: 'Sixpack', package_quantity: 6, package_unit: 'piece' })).toBe(
      'Sixpack (6 Stück)',
    );
  });

  it('wandelt Datum ohne Zeitzonenfehler', () => {
    expect(toIsoDate(new Date(2026, 10, 20))).toBe('2026-11-20');
    expect(toIsoDate(fromIsoDate('2026-01-01')!)).toBe('2026-01-01');
  });
});

import { parseGermanDate } from './format';

describe('parseGermanDate', () => {
  const today = new Date(2026, 10, 14); // 14.11.2026
  const iso = (s: string) => {
    const d = parseGermanDate(s, today);
    return d ? toIsoDate(d) : null;
  };

  it('liest übliche Schreibweisen', () => {
    expect(iso('20.11.2027')).toBe('2027-11-20');
    expect(iso('20.11.27')).toBe('2027-11-20');
    expect(iso('1.2.2027')).toBe('2027-02-01');
    expect(iso('201127')).toBe('2027-11-20');
    expect(iso('20112027')).toBe('2027-11-20');
    expect(iso('20/11/2027')).toBe('2027-11-20');
    expect(iso(' 20.11.2027 ')).toBe('2027-11-20');
  });

  it('ergänzt fehlendes Jahr zukunftsgerichtet', () => {
    expect(iso('20.11.')).toBe('2026-11-20');
    expect(iso('20.11')).toBe('2026-11-20');
    expect(iso('14.11.')).toBe('2026-11-14');
    expect(iso('01.03.')).toBe('2027-03-01');
  });

  it('weist Ungültiges ab', () => {
    expect(iso('31.02.2027')).toBeNull();
    expect(iso('2027-11-20')).toBeNull();
    expect(iso('abc')).toBeNull();
    expect(iso('')).toBeNull();
  });
});
