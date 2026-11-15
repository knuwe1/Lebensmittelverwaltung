import { MantineProvider } from '@mantine/core';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { ExpiryStatus, ExpiryType } from '../api/types';
import { ExpiryText, relativeDays } from './ExpiryText';

function show(expiry_type: ExpiryType, expiry_status: ExpiryStatus, days: number | null) {
  const item = {
    expiry_type,
    expiry_status,
    expiry_date: days === null ? null : '2026-11-20',
    days_until_expiry: days,
  };
  render(
    <MantineProvider>
      <ExpiryText item={item} />
    </MantineProvider>,
  );
}

describe('relativeDays', () => {
  it('formuliert Abstände zum Datum', () => {
    expect([0, 1, 3, -1, -4].map(relativeDays)).toEqual([
      'heute',
      'morgen',
      'in 3 Tagen',
      'seit gestern',
      'seit 4 Tagen',
    ]);
  });
});

describe('ExpiryText – Status immer auch als Text (FR-EXP-003)', () => {
  it('gelb: Datum nähert sich', () => {
    show('best_before', 'expiring', 3);
    expect(screen.getByText(/MHD 20\.11\.2026 · in 3 Tagen/)).toBeInTheDocument();
  });

  it('rot: heute erreicht', () => {
    show('best_before', 'due', 0);
    expect(screen.getByText(/· heute/)).toBeInTheDocument();
  });

  it('rot: MHD überschritten – prüfen, nicht verbieten', () => {
    show('best_before', 'expired', -2);
    expect(screen.getByText(/abgelaufen seit 2 Tagen/)).toBeInTheDocument();
    expect(screen.queryByText(/nicht mehr verwenden/)).not.toBeInTheDocument();
  });

  it('rot: Verbrauchsdatum überschritten – deutliche Warnung', () => {
    show('use_by', 'expired', -1);
    expect(screen.getByText(/nicht mehr verwenden/)).toBeInTheDocument();
  });

  it('grau: kein Datum', () => {
    show('none', 'unknown', null);
    expect(screen.getByText('ohne Datum')).toBeInTheDocument();
  });
});
