import { describe, expect, it } from 'vitest';
import type { ShoppingItem } from '../api/types';
import { shoppingQuantity } from './ShoppingListPage';

const base: ShoppingItem = {
  id: '1',
  origin: 'auto',
  optional: false,
  status: 'open',
  product_id: 'p',
  name: 'Milch',
  brand: null,
  category_name: null,
  base_unit: 'ml',
  suggested_quantity: 5000,
  quantity: 5000,
  quantity_adjusted: false,
  package: null,
  packages: null,
  received_quantity: 0,
  comment: null,
  available_quantity: 1000,
  minimum_stock: 2000,
  target_stock: 6000,
  level_status: 'below',
  purchased_at: null,
  created_at: '2026-11-15T10:00:00Z',
};

describe('shoppingQuantity', () => {
  it('zeigt ganze Packungen der Standardverpackung', () => {
    const pkg = { variant_id: 'v', package_quantity: 1, package_unit: 'l', base_quantity: 1000, name: null };
    expect(shoppingQuantity({ ...base, package: pkg, packages: 5 })).toBe('5 × 1 l');
  });
  it('sonst die Menge in der Basiseinheit', () => {
    expect(shoppingQuantity(base)).toBe('5 l');
  });
  it('Freitext als Anzahl', () => {
    expect(shoppingQuantity({ ...base, base_unit: null, product_id: null, quantity: 2 })).toBe('2 ×');
  });
  it('ohne Menge', () => {
    expect(shoppingQuantity({ ...base, quantity: null })).toBe('Menge offen');
  });
});
