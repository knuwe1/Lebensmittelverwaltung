import { Alert, Button, Group, NumberInput, Stack, Switch, Text } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { api, errorMessage } from '../api/client';
import { useHouseholdSettings } from '../api/hooks';
import type { HouseholdSettings } from '../api/types';

/** Systemeinstellungen des Haushalts (Spez. 9.2 „Einstellungen“, nur Administratoren). */
export function SystemSettings() {
  const qc = useQueryClient();
  const { data } = useHouseholdSettings();
  const [form, setForm] = useState<HouseholdSettings | null>(null);
  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const save = useMutation({
    mutationFn: (body: Partial<HouseholdSettings>) => api.patch<HouseholdSettings>('/settings', body),
    onSuccess: (s) => {
      qc.setQueryData(['settings'], s);
      notifications.show({ color: 'green', message: 'Einstellungen gespeichert.' });
    },
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });

  if (!form) return null;
  return (
    <Stack maw={560}>
      <Switch
        size="md"
        label="Externe Produktdaten verwenden (Open Food Facts)"
        checked={form.external_product_data}
        onChange={(e) => {
          const external_product_data = e.currentTarget.checked;
          setForm({ ...form, external_product_data });
          save.mutate({ external_product_data });
        }}
      />
      <Alert color="blue" variant="light">
        <Text size="sm">
          Ist die Option aktiv, wird bei einem <b>unbekannten Barcode</b> ausschließlich die Barcode-Nummer an
          Open Food Facts (openfoodfacts.org) gesendet – über diesen Server, nicht direkt vom Handy. Bestands- und
          Haushaltsdaten werden nicht übermittelt. Gefundene Angaben sind Vorschläge und werden vor dem Speichern
          angezeigt. Daten: ODbL, Bilder: CC BY-SA.
        </Text>
      </Alert>

      <NumberInput
        label="Haltbarkeitswarnung (Tage vor Ablauf)"
        description="Standard für alle Lebensmittel; pro Produkt überschreibbar."
        min={0}
        max={365}
        value={form.expiry_warning_days}
        onChange={(v) => setForm({ ...form, expiry_warning_days: Number(v) || 0 })}
      />
      <NumberInput
        label="Warnfaktor Mindestbestand"
        description="Ab Mindestbestand × Faktor gilt ein Produkt als „nahe am Mindestbestand“."
        min={1}
        max={10}
        step={0.05}
        decimalScale={2}
        decimalSeparator=","
        value={form.stock_warning_factor}
        onChange={(v) => setForm({ ...form, stock_warning_factor: Number(v) || 1 })}
      />
      <Group>
        <Button
          loading={save.isPending}
          onClick={() =>
            save.mutate({
              expiry_warning_days: form.expiry_warning_days,
              stock_warning_factor: form.stock_warning_factor,
            })
          }
        >
          Speichern
        </Button>
      </Group>
    </Stack>
  );
}
