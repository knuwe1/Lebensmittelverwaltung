import { useState } from 'react';
import { Badge, Button, Card, Group, Modal, SimpleGrid, Stack, Switch, Text, TextInput, Title } from '@mantine/core';
import { useDebouncedValue, useDisclosure } from '@mantine/hooks';
import { IconPlus, IconSearch } from '@tabler/icons-react';
import { Link, useNavigate } from 'react-router-dom';
import { useProducts } from '../api/hooks';
import { ProductAvatar } from '../components/ProductAvatar';
import { ProductForm } from '../components/ProductForm';
import { CategorySelect } from '../components/selects';
import { formatQuantity } from '../lib/format';

/** Lebensmittelkatalog (FR-PRD-001, FR-PRD-005). */
export function ProductsPage() {
  const [q, setQ] = useState('');
  const [debounced] = useDebouncedValue(q.trim(), 250);
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [inactive, setInactive] = useState(false);
  const [opened, { open, close }] = useDisclosure();
  const navigate = useNavigate();
  const { data } = useProducts({
    q: debounced || undefined,
    category_id: categoryId,
    include_inactive: inactive,
    limit: 200,
  });

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Lebensmittel</Title>
        <Button leftSection={<IconPlus size={18} />} onClick={open}>
          Neues Lebensmittel
        </Button>
      </Group>
      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        <TextInput
          placeholder="Name, Marke oder Barcode"
          leftSection={<IconSearch size={18} />}
          value={q}
          onChange={(e) => setQ(e.currentTarget.value)}
        />
        <CategorySelect label={null} placeholder="Alle Produktgruppen" clearable value={categoryId} onChange={setCategoryId} />
        <Switch label="Deaktivierte anzeigen" checked={inactive} onChange={(e) => setInactive(e.currentTarget.checked)} mt={8} />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="xs">
        {data?.items.map((p) => (
          <Card key={p.id} withBorder padding="sm" component={Link} to={`/lebensmittel/${p.id}`}>
            <Group wrap="nowrap">
              <ProductAvatar product={p} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <Text fw={600} truncate>
                  {p.name}
                </Text>
                <Text size="sm" c="dimmed" truncate>
                  {[p.brand, p.category_name].filter(Boolean).join(' · ')}
                </Text>
              </div>
              <Stack gap={2} align="flex-end">
                <Text size="sm">{formatQuantity(p.stock_quantity, p.base_unit)}</Text>
                {!p.active && <Badge color="gray">deaktiviert</Badge>}
              </Stack>
            </Group>
          </Card>
        ))}
      </SimpleGrid>
      {data?.total === 0 && (
        <Text c="dimmed" ta="center" py="xl">
          Keine Lebensmittel gefunden.
        </Text>
      )}

      <Modal opened={opened} onClose={close} title="Neues Lebensmittel" size="lg">
        <ProductForm initialName={debounced} onCancel={close} onSaved={(p) => navigate(`/lebensmittel/${p.id}`)} />
      </Modal>
    </Stack>
  );
}
