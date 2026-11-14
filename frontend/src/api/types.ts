export type Role = 'admin' | 'member';

export interface User {
  id: string;
  username: string;
  display_name: string;
  role: Role;
  can_do_inventory: boolean;
  active: boolean;
}

export type BaseUnit = 'piece' | 'g' | 'ml';
export type PackageUnit = 'piece' | 'g' | 'kg' | 'ml' | 'l';
export type ExpiryType = 'best_before' | 'use_by' | 'none' | 'unknown';

export interface Category {
  id: string;
  name: string;
  sort_order: number;
  active: boolean;
}

export interface Variant {
  id: string;
  name: string | null;
  barcode: string | null;
  package_quantity: number;
  package_unit: PackageUnit;
  base_quantity: number;
  is_default: boolean;
  active: boolean;
}

export interface Product {
  id: string;
  name: string;
  brand: string | null;
  category_id: string;
  category_name: string;
  base_unit: BaseUnit;
  minimum_stock: number | null;
  target_stock: number | null;
  default_location_id: string | null;
  default_shelf_life_days: number | null;
  expiry_warning_days: number | null;
  notes: string | null;
  active: boolean;
  has_image: boolean;
  image_source: string | null;
  variants: Variant[];
  stock_quantity: number;
  updated_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
}

export interface Location {
  id: string;
  parent_id: string | null;
  name: string;
  description: string | null;
  location_type: string | null;
  active: boolean;
  path: string;
}

export interface StockItem {
  id: string;
  product_id: string;
  product_name: string;
  product_brand: string | null;
  base_unit: BaseUnit;
  variant_id: string | null;
  location_id: string;
  location_path: string;
  quantity: number;
  expiry_type: ExpiryType;
  expiry_date: string | null;
  received_on: string;
  opened_on: string | null;
  status: 'available' | 'consumed' | 'disposed';
  note: string | null;
  version: number;
}

export interface ReceiptLine {
  quantity: number;
  unit: 'package' | 'base';
  expiry_type: ExpiryType;
  expiry_date: string | null;
}

export interface ReceiptResult {
  transaction_id: string;
  product: Product;
  stock_items: StockItem[];
  received_quantity: number;
}

export interface ReceiptDefaults {
  variant_id: string | null;
  location_id: string | null;
  expiry_type: ExpiryType;
  expiry_date: string | null;
}

export interface BarcodeLookup {
  product: Product;
  variant_id: string;
}
