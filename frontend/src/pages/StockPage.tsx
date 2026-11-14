import { useMemo, useState } from 'react';
import {
  ActionIcon,
  Badge,
  Card,
  Group,
  Loader,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconArrowsTransferUp, IconSearch } from '@tabler/icons-react';
import { Link, useSearchParams } from 'react-router-dom';
import { useStock } from '../api/hooks';
import type { StockItem } from '../api/types';
import { CategorySelect, LocationSelect } from '../components/selects';
import { formatQuantity } from '../lib/format';
import { ExpiryText } from '../components/ExpiryText';
import { TransferDialog } from '../components/TransferDialog';

interface Group_ {
  productId: string;
  name: string;
  brand: string | null;
  unit: StockItem['base_unit'];
  total: number;
  items: StockItem[];
}

/** Bestandsübersicht mit Such- und Filterfunktionen (MVP 9, FR-LOC-004). */
export function StockPage() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState('');
  const [transferItem, setTransferItem] = useState<StockItem | null>(null);
  const [debounced] = useDebouncedValue(q.trim(), 250);
  const locationId = params.get('lagerplatz');
  const categoryId = params.get('gruppe');
  const sort = (params.get('sortierung') as 'product' | 'expiry') ?? 'product';
  const setParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  const { data, isLoading } = useStock({
    q: debounced || undefined,
    location_id: locationId,
    category_id: categoryId,
    sort,
  });

  const groups = useMemo(() => {
    const map = new Map<string, Group_>();
    for (const item of data?.items ?? []) {
      let g = map.get(item.product_id);
      if (!g) {
        g = {
          productId: item.product_id,
          name: item.product_name,
          brand: item.product_brand,
          unit: item.base_unit,
          total: 0,
          items: [],
        };
        map.set(item.product_id, g);
      }
      g.total += item.quantity;
      g.items.push(item);
    }
    return [...map.values()];
  }, [data]);

  return (
    <Stack>
      <Title order={2}>Vorräte</Title>
      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }}>
        <TextInput
          placeholder="Suchen…"
          leftSection={<IconSearch size={18} />}
          value={q}
          onChange={(e) => setQ(e.currentTarget.value)}
        />
        <LocationSelect label={null} placeholder="Alle Lagerplätze" clearable value={locationId} onChange={(v) => setParam('lagerplatz', v)} />
        <CategorySelect label={null} placeholder="Alle Produktgruppen" clearable value={categoryId} onChange={(v) => setParam('gruppe', v)} />
        <Select
          value={sort}
          onChange={(v) => setParam('sortierung', v === 'product' ? null : v)}
          data={[
            { value: 'product', label: 'Nach Produkt' },
            { value: 'expiry', label: 'Nach Haltbarkeit' },
          ]}
          allowDeselect={false}
        />
      </SimpleGrid>

      {isLoading && <Loader mx="auto" />}
      {data && data.total === 0 && (
        <Text c="dimmed" ta="center" py="xl">
          Keine Vorräte gefunden.
        </Text>
      )}

      {sort === 'expiry' ? (
        <Table.ScrollContainer minWidth={560}>
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Haltbarkeit</Table.Th>
                <Table.Th>Lebensmittel</Table.Th>
                <Table.Th>Menge</Table.Th>
                <Table.Th>Lagerplatz</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {data?.items.map((i) => (
                <Table.Tr key={i.id}>
                  <Table.Td><ExpiryText item={i} /></Table.Td>
                  <Table.Td>
                    <Link to={`/lebensmittel/${i.product_id}`}>{i.product_name}</Link>
                  </Table.Td>
                  <Table.Td>{formatQuantity(i.quantity, i.base_unit)}</Table.Td>
                  <Table.Td>{i.location_path}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      ) : (
        <Stack gap="xs">
          {groups.map((g) => (
            <Card key={g.productId} withBorder padding="sm">
              <Group justify="space-between" wrap="nowrap" mb={4}>
                <div style={{ minWidth: 0 }}>
                  <Text fw={600} component={Link} to={`/lebensmittel/${g.productId}`} truncate>
                    {g.name}
                  </Text>
                  {g.brand && <Text size="xs" c="dimmed">{g.brand}</Text>}
                </div>
                <Badge size="lg" variant="light">
                  {formatQuantity(g.total, g.unit)}
                </Badge>
              </Group>
              {g.items.map((i) => (
                <Group key={i.id} justify="space-between" gap="xs" wrap="nowrap">
                  <Text size="sm" c="dimmed" truncate style={{ flex: 1 }}>
                    {i.location_path}
                  </Text>
                  <ExpiryText item={i} />
                  <Text size="sm" w={90} ta="right">
                    {formatQuantity(i.quantity, i.base_unit)}
                  </Text>
                  <ActionIcon variant="subtle" size="sm" onClick={() => setTransferItem(i)} aria-label="Umlagern">
                    <IconArrowsTransferUp size={16} />
                  </ActionIcon>
                </Group>
              ))}
            </Card>
          ))}
        </Stack>
      )}
      <TransferDialog item={transferItem} onClose={() => setTransferItem(null)} />
      {data && data.total > data.items.length && (
        <Text c="dimmed" size="sm" ta="center">
          {data.items.length} von {data.total} Positionen angezeigt – bitte Filter verwenden.
        </Text>
      )}
    </Stack>
  );
}
