import { useQuery } from '@tanstack/react-query';
import { api } from './client';
import type { Category, Location, Page, Product, StockItem } from './types';

export const queryKeys = {
  categories: ['categories'] as const,
  locations: ['locations'] as const,
  products: (params: object) => ['products', params] as const,
  product: (id: string) => ['product', id] as const,
  stock: (params: object) => ['stock', params] as const,
};

export function useCategories() {
  return useQuery({
    queryKey: queryKeys.categories,
    queryFn: () => api.get<Category[]>('/categories'),
    staleTime: 5 * 60_000,
  });
}

export function useLocations() {
  return useQuery({
    queryKey: queryKeys.locations,
    queryFn: () => api.get<Location[]>('/locations'),
    staleTime: 60_000,
  });
}

export interface ProductQuery {
  q?: string;
  category_id?: string | null;
  location_id?: string | null;
  in_stock?: boolean;
  include_inactive?: boolean;
  limit?: number;
}

export function useProducts(params: ProductQuery, enabled = true) {
  return useQuery({
    queryKey: queryKeys.products(params),
    queryFn: ({ signal }) =>
      api.get<Page<Product>>('/products', { limit: 100, ...params }, signal),
    enabled,
    placeholderData: (prev) => prev,
  });
}

export function useProduct(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.product(id ?? ''),
    queryFn: () => api.get<Product>(`/products/${id}`),
    enabled: !!id,
  });
}

export interface StockQuery {
  q?: string;
  product_id?: string;
  location_id?: string | null;
  category_id?: string | null;
  sort?: 'product' | 'expiry' | 'received';
}

/**
 * @param keepPrevious Beim Filtern die bisherige Liste weiter anzeigen (verhindert Flackern).
 *   Für Ansichten eines einzelnen Produkts abschalten – sonst wären kurzzeitig Positionen
 *   einer anderen Abfrage sichtbar bzw. auswählbar.
 */
export function useStock(params: StockQuery, { keepPrevious = true } = {}) {
  return useQuery({
    queryKey: queryKeys.stock(params),
    queryFn: ({ signal }) => api.get<Page<StockItem>>('/stock', { limit: 1000, ...params }, signal),
    placeholderData: keepPrevious ? (prev) => prev : undefined,
  });
}

export function productImageUrl(p: Pick<Product, 'id' | 'has_image' | 'updated_at'>) {
  return p.has_image ? `/api/v1/products/${p.id}/image?v=${encodeURIComponent(p.updated_at)}` : null;
}
