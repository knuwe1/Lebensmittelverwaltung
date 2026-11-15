import { Badge } from '@mantine/core';
import type { StockLevelStatus } from '../api/types';

export const STOCK_LEVEL_LABELS: Record<StockLevelStatus, string> = {
  ok: 'Ausreichend',
  near: 'Nahe am Mindestbestand',
  at_minimum: 'Mindestbestand erreicht',
  below: 'Mindestbestand unterschritten',
};

const COLORS: Record<StockLevelStatus, string> = {
  ok: 'green',
  near: 'orange',
  at_minimum: 'red',
  below: 'red',
};

/** Bestandsstatus gegenüber dem Mindestbestand (FR-SHP-003/004) – Farbe plus Text. */
export function StockLevelBadge({ status, size = 'sm' }: { status: StockLevelStatus; size?: 'xs' | 'sm' | 'md' }) {
  return (
    <Badge color={COLORS[status]} variant={status === 'ok' ? 'light' : 'filled'} size={size} style={{ flexShrink: 0 }}>
      {STOCK_LEVEL_LABELS[status]}
    </Badge>
  );
}
