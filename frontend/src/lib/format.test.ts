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
