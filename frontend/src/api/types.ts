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
  tare_weight: number | null;
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
  weigh_remaining: boolean;
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
  /** Haltbarkeitsampel (FR-EXP-003), vom Server mit der gültigen Warnfrist berechnet. */
  expiry_status: ExpiryStatus;
  /** Tage bis zum Haltbarkeitsdatum; negativ = überschritten, null = kein Datum. */
  days_until_expiry: number | null;
  warning_days: number;
}

/** ok = grün, expiring = gelb, due/expired = rot, unknown = grau. */
export type ExpiryStatus = 'ok' | 'expiring' | 'due' | 'expired' | 'unknown';

export type StockLevelStatus = 'ok' | 'near' | 'at_minimum' | 'below';

/** Bestandsstatus eines Produkts mit Mindestbestand (FR-SHP-003/004). */
export interface StockLevel {
  product_id: string;
  product_name: string;
  product_brand: string | null;
  base_unit: BaseUnit;
  /** Physisch vorhanden – inkl. Positionen mit überschrittenem Verbrauchsdatum. */
  physical_quantity: number;
  /** Für den Verbrauch verfügbar (FR-EXP-006). */
  available_quantity: number;
  minimum_stock: number;
  target_stock: number | null;
  warning_threshold: number;
  status: StockLevelStatus;
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

export interface PlannedAllocation {
  stock_item: StockItem;
  quantity: number;
}

export interface ConsumptionPlan {
  allocations: PlannedAllocation[];
  requested: number;
  available: number;
  sufficient: boolean;
}

export interface BookingResult {
  transaction_id: string;
  product: Product;
  stock_items: StockItem[];
  quantity: number;
}

export type MovementType =
  | 'receipt'
  | 'consumption'
  | 'transfer_out'
  | 'transfer_in'
  | 'inventory_correction'
  | 'disposal'
  | 'reversal';

export interface Movement {
  id: string;
  transaction_id: string;
  movement_type: MovementType;
  product_id: string;
  product_name: string;
  base_unit: BaseUnit;
  stock_item_id: string;
  expiry_type: ExpiryType;
  expiry_date: string | null;
  source_location_path: string | null;
  target_location_path: string | null;
  quantity: number;
  quantity_delta: number;
  reason: string | null;
  comment: string | null;
  created_at: string;
  created_by: string;
  created_by_name: string;
  reverses_movement_id: string | null;
  reversed: boolean;
}

export interface WeighingPreview {
  measured: number;
  tare: number;
  net: number;
  full_packages: number;
  open_before: number;
  consumption: number;
  remaining_total: number;
}

export interface HouseholdSettings {
  external_product_data: boolean;
  expiry_warning_days: number;
  stock_warning_factor: number;
}

export interface ProductSuggestion {
  source: string;
  source_url: string;
  license: string;
  barcode: string;
  name: string | null;
  brand: string | null;
  base_unit: BaseUnit;
  package_quantity: number | string | null;
  package_unit: PackageUnit | null;
  category_id: string | null;
  image_url: string | null;
}

/** Vorbelegung für die Neuanlage eines Produkts (Suche, Scan oder externe Quelle). */
export interface ProductPrefill {
  name?: string;
  barcode?: string;
  suggestion?: ProductSuggestion;
}
