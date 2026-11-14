import { useRef } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { notifications } from '@mantine/notifications';
import { api, ApiError, errorMessage, newIdempotencyKey } from './client';
import type { BookingResult } from './types';

/**
 * Buchung mit Idempotency-Key (DEC-025). Der Schlüssel bleibt bis zum Erfolg gleich,
 * sodass ein erneutes Absenden nach einem Netzwerkfehler nicht doppelt bucht.
 */
export function useBooking<TBody>(path: string, onSuccess?: (r: BookingResult) => void) {
  const qc = useQueryClient();
  const key = useRef(newIdempotencyKey());
  return useMutation({
    mutationFn: (body: TBody) =>
      api.post<BookingResult>(path, body, { idempotencyKey: key.current }),
    onSuccess: (r) => {
      key.current = newIdempotencyKey();
      qc.invalidateQueries({ queryKey: ['stock'] });
      qc.invalidateQueries({ queryKey: ['products'] });
      qc.invalidateQueries({ queryKey: ['movements'] });
      qc.invalidateQueries({ queryKey: ['consumption-plan'] });
      qc.invalidateQueries({ queryKey: ['recent-products'] });
      qc.setQueryData(['product', r.product.id], r.product);
      onSuccess?.(r);
    },
    onError: (e) => {
      // Fachliche Ablehnung (z. B. Bestand geändert) → neuer Schlüssel für den nächsten Versuch
      if (e instanceof ApiError) key.current = newIdempotencyKey();
      notifications.show({ color: 'red', title: 'Nicht gebucht', message: errorMessage(e), autoClose: 8000 });
    },
  });
}
