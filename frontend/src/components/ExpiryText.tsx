import { Text } from '@mantine/core';
import type { StockItem } from '../api/types';
import { formatDate, isExpired } from '../lib/format';

const EXPIRY_SHORT: Record<string, string> = {
  best_before: 'MHD',
  use_by: 'Verbr.',
  none: 'ohne Datum',
  unknown: 'Datum unbekannt',
};

/** Haltbarkeitsangabe; abgelaufene Daten werden rot und mit Text markiert (nicht nur Farbe). */
export function ExpiryText({ item }: { item: Pick<StockItem, 'expiry_type' | 'expiry_date'> }) {
  if (!item.expiry_date)
    return (
      <Text span c="dimmed" size="sm">
        {EXPIRY_SHORT[item.expiry_type]}
      </Text>
    );
  const expired = isExpired(item);
  return (
    <Text span size="sm" c={expired ? 'red' : undefined} fw={expired ? 600 : undefined}>
      {EXPIRY_SHORT[item.expiry_type]} {formatDate(item.expiry_date)}
      {expired && ' (abgelaufen)'}
    </Text>
  );
}
