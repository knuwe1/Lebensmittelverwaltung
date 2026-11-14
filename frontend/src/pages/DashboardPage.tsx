import { Anchor, Button, Card, Group, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { IconPackageExport, IconPackageImport } from '@tabler/icons-react';
import { Link } from 'react-router-dom';
import { useProducts, useStock } from '../api/hooks';
import { useUser } from '../auth/AuthContext';
import { formatDateTime } from '../lib/format';
import { MovementBadge, signedQuantity, useMovements } from './HistoryPage';

/** Startseite (Spez. 9.2/9.3). Warnungen und Einkaufsliste folgen in Phase 5. */
export function DashboardPage() {
  const user = useUser();
  const products = useProducts({ limit: 1 });
  const stock = useStock({});
  const movements = useMovements({ limit: 6 });
  return (
    <Stack>
      <Title order={2}>Hallo {user.display_name}</Title>
      <SimpleGrid cols={2}>
        <Button component={Link} to="/einlagern" size="xl" h={88} leftSection={<IconPackageImport size={28} />}>
          Einlagern
        </Button>
        <Button component={Link} to="/entnehmen" size="xl" h={88} variant="light" leftSection={<IconPackageExport size={28} />}>
          Entnehmen
        </Button>
      </SimpleGrid>
      <SimpleGrid cols={{ base: 2, sm: 4 }}>
        <Card withBorder component={Link} to="/lebensmittel">
          <Text size="xs" c="dimmed">Lebensmittel</Text>
          <Text size="xl" fw={700}>{products.data?.total ?? '–'}</Text>
        </Card>
        <Card withBorder component={Link} to="/vorraete">
          <Text size="xs" c="dimmed">Bestandspositionen</Text>
          <Text size="xl" fw={700}>{stock.data?.total ?? '–'}</Text>
        </Card>
      </SimpleGrid>
      <Card withBorder>
        <Group justify="space-between" mb="xs">
          <Text fw={600}>Letzte Bestandsbewegungen</Text>
          <Anchor component={Link} to="/historie" size="sm">
            Alle anzeigen
          </Anchor>
        </Group>
        <Stack gap={6}>
          {movements.data?.items.map((m) => (
            <Group key={m.id} justify="space-between" wrap="nowrap" gap="xs">
              <Group gap="xs" wrap="nowrap" style={{ minWidth: 0 }}>
                <MovementBadge m={m} />
                <Text size="sm" truncate>
                  {m.product_name}
                </Text>
              </Group>
              <Group gap="xs" wrap="nowrap">
                <Text size="sm" c={m.quantity_delta > 0 ? 'green' : 'red'}>
                  {signedQuantity(m)}
                </Text>
                <Text size="xs" c="dimmed" visibleFrom="xs">
                  {formatDateTime(m.created_at)}
                </Text>
              </Group>
            </Group>
          ))}
          {movements.data?.total === 0 && <Text size="sm" c="dimmed">Noch keine Buchungen.</Text>}
        </Stack>
      </Card>
    </Stack>
  );
}
