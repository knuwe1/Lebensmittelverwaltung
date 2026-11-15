import { useMemo } from 'react';
import {
  Button,
  Card,
  Group,
  Loader,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useQueryClient } from '@tanstack/react-query';
import { IconPackageExport, IconTrash } from '@tabler/icons-react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api, errorMessage } from '../api/client';
import { queryKeys, useExpiring } from '../api/hooks';
import type { ExpiryStatus, Product, StockItem } from '../api/types';
import { ExpiryText, isUnusable } from '../components/ExpiryText';
import { LocationSelect } from '../components/selects';
import { formatQuantity } from '../lib/format';
import type { ConsumeState, Mode } from './ConsumePage';

type Filter = 'all' | 'expired' | 'due' | 'expiring';
type Sort = 'expiry' | 'product' | 'location';

/** Öffnet die Entnahme mit vorgewähltem Produkt, Modus und Bestandsposition. */
export function useOpenBooking() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  return async (item: StockItem, mode: Mode) => {
    try {
      const product = await qc.fetchQuery({
        queryKey: queryKeys.product(item.product_id),
        queryFn: () => api.get<Product>(`/products/${item.product_id}`),
      });
      const state: ConsumeState = { product, mode, stockItemId: item.id };
      navigate('/entnehmen', { state });
    } catch (e) {
      notifications.show({ color: 'red', message: errorMessage(e) });
    }
  };
}

/** Übersicht gefährdeter Lebensmittel (FR-EXP-004, Spez. 9.2 „Haltbarkeit“). */
export function ExpiryPage() {
  const [params, setParams] = useSearchParams();
  const locationId = params.get('lagerplatz');
  const sort = (params.get('sortierung') as Sort | null) ?? 'expiry';
  const filter = (params.get('status') as Filter | null) ?? 'all';
  const setParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };
  const openBooking = useOpenBooking();

  const { data, isLoading } = useExpiring({ location_id: locationId, sort });
  const all = useMemo(() => data?.items ?? [], [data]);
  const count = (s: ExpiryStatus) => all.filter((i) => i.expiry_status === s).length;
  const items = filter === 'all' ? all : all.filter((i) => i.expiry_status === filter);

  return (
    <Stack>
      <Title order={2}>Haltbarkeit</Title>
      <SegmentedControl
        value={filter}
        onChange={(v) => setParam('status', v === 'all' ? null : v)}
        fullWidth
        data={[
          { value: 'all', label: `Alle (${all.length})` },
          { value: 'expired', label: `Abgelaufen (${count('expired')})` },
          { value: 'due', label: `Heute (${count('due')})` },
          { value: 'expiring', label: `Bald (${count('expiring')})` },
        ]}
      />
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <LocationSelect
          label={null}
          placeholder="Alle Lagerplätze"
          clearable
          value={locationId}
          onChange={(v) => setParam('lagerplatz', v)}
        />
        <Select
          value={sort}
          onChange={(v) => setParam('sortierung', v === 'expiry' ? null : v)}
          data={[
            { value: 'expiry', label: 'Nach Datum' },
            { value: 'product', label: 'Nach Lebensmittel' },
            { value: 'location', label: 'Nach Lagerplatz' },
          ]}
          allowDeselect={false}
          aria-label="Sortierung"
        />
      </SimpleGrid>

      {isLoading && <Loader mx="auto" />}
      {data && items.length === 0 && (
        <Text c="dimmed" ta="center" py="xl">
          {filter === 'all'
            ? 'Keine gefährdeten Lebensmittel – nichts läuft in den nächsten Tagen ab.'
            : 'Keine Lebensmittel in dieser Kategorie.'}
        </Text>
      )}

      <Stack gap="xs">
        {items.map((i) => (
          <Card key={i.id} withBorder padding="sm">
            <Group justify="space-between" wrap="nowrap" align="flex-start" gap="xs">
              <div style={{ minWidth: 0 }}>
                <Text fw={600} component={Link} to={`/lebensmittel/${i.product_id}`} truncate display="block">
                  {i.product_name}
                </Text>
                {i.product_brand && (
                  <Text size="xs" c="dimmed">
                    {i.product_brand}
                  </Text>
                )}
              </div>
              <Text fw={600} style={{ flexShrink: 0 }}>
                {formatQuantity(i.quantity, i.base_unit)}
              </Text>
            </Group>
            <ExpiryText item={i} />
            <Text size="sm" c="dimmed">
              {i.location_path}
            </Text>
            <Group gap="xs" mt="xs">
              {!isUnusable(i) && (
                <Button size="xs" variant="light" leftSection={<IconPackageExport size={16} />} onClick={() => openBooking(i, 'consume')}>
                  Entnehmen
                </Button>
              )}
              <Button
                size="xs"
                variant={i.expiry_status === 'expired' ? 'filled' : 'subtle'}
                color="red"
                leftSection={<IconTrash size={16} />}
                onClick={() => openBooking(i, 'dispose')}
              >
                Entsorgen
              </Button>
            </Group>
          </Card>
        ))}
      </Stack>

      <Text size="xs" c="dimmed">
        Abgelaufenes bleibt im Bestand, bis es entnommen oder entsorgt wird. Ein überschrittenes
        Mindesthaltbarkeitsdatum heißt nicht, dass das Lebensmittel verdorben ist – bitte prüfen. Bei
        überschrittenem Verbrauchsdatum nicht mehr verwenden.
      </Text>
    </Stack>
  );
}
