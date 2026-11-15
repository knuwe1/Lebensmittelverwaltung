import { Text } from '@mantine/core';
import { IconAlertTriangle, IconHourglassLow } from '@tabler/icons-react';
import type { StockItem } from '../api/types';
import { formatDate } from '../lib/format';

const EXPIRY_SHORT: Record<string, string> = {
  best_before: 'MHD',
  use_by: 'Verbr.',
  none: 'ohne Datum',
  unknown: 'Datum unbekannt',
};

/** „heute“, „morgen“, „in 3 Tagen“, „seit gestern“, „seit 4 Tagen“. */
export function relativeDays(days: number): string {
  if (days === 0) return 'heute';
  if (days === 1) return 'morgen';
  if (days > 1) return `in ${days} Tagen`;
  if (days === -1) return 'seit gestern';
  return `seit ${-days} Tagen`;
}

type ExpiryItem = Pick<StockItem, 'expiry_type' | 'expiry_date' | 'expiry_status' | 'days_until_expiry'>;

/** Überschrittenes Verbrauchsdatum: nicht mehr verwenden (Spez. 7.1, FR-EXP-003). */
export function isUnusable(item: Pick<StockItem, 'expiry_type' | 'expiry_status'>): boolean {
  return item.expiry_type === 'use_by' && item.expiry_status === 'expired';
}

/**
 * Haltbarkeitsampel (FR-EXP-003): grün = unauffällig, gelb = nähert sich, rot = heute erreicht
 * oder überschritten, grau = kein Datum. Der Status steht immer auch als Text und Symbol da,
 * nicht nur als Farbe.
 */
export function ExpiryText({ item }: { item: ExpiryItem }) {
  const label = EXPIRY_SHORT[item.expiry_type];
  if (!item.expiry_date || item.expiry_status === 'unknown')
    return (
      <Text span c="dimmed" size="sm">
        {label}
      </Text>
    );
  const date = `${label} ${formatDate(item.expiry_date)}`;
  const days = item.days_until_expiry ?? 0;
  const iconStyle = { verticalAlign: '-2px', marginRight: 3 };

  switch (item.expiry_status) {
    case 'expiring':
      return (
        <Text span size="sm" c="orange.8" fw={500}>
          <IconHourglassLow size={14} style={iconStyle} aria-hidden />
          {date} · {relativeDays(days)}
        </Text>
      );
    case 'due':
      return (
        <Text span size="sm" c="red.8" fw={600}>
          <IconAlertTriangle size={14} style={iconStyle} aria-hidden />
          {date} · heute
        </Text>
      );
    case 'expired':
      return (
        <Text span size="sm" c="red.8" fw={isUnusable(item) ? 700 : 600}>
          <IconAlertTriangle size={14} style={iconStyle} aria-hidden />
          {date} · {isUnusable(item) ? 'überschritten – nicht mehr verwenden!' : `abgelaufen ${relativeDays(days)}`}
        </Text>
      );
    default:
      return <Text span size="sm">{date}</Text>;
  }
}
