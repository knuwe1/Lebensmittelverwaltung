import { Anchor, Button, Card, Group, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { IconCircleCheck, IconPackageExport, IconPackageImport } from '@tabler/icons-react';
import { Link } from 'react-router-dom';
import { useExpiring, useProducts, useStock, useStockLevels } from '../api/hooks';
import { ExpiryText } from '../components/ExpiryText';
import { StockLevelBadge } from '../components/StockLevelBadge';
import { formatQuantity } from '../lib/format';
import { useUser } from '../auth/AuthContext';
import { formatDateTime } from '../lib/format';
import { MovementBadge, signedQuantity, useMovements } from './HistoryPage';

const PREVIEW = 5;

/** Niedriger Bestand (FR-SHP-003/004): unterschritten, erreicht und nahe am Mindestbestand. */
function LowStockCard() {
  const { data } = useStockLevels(['below', 'at_minimum', 'near']);
  if (!data) return null;
  const urgent = data.filter((l) => l.status !== 'near').length;
  return (
    <Card withBorder>
      <Group justify="space-between" mb="xs">
        <Text fw={600}>Niedriger Bestand</Text>
        <Text size="sm" c={urgent ? 'red.8' : 'dimmed'} fw={urgent ? 600 : undefined}>
          {urgent} nachkaufen{data.length > urgent ? ` · ${data.length - urgent} knapp` : ''}
        </Text>
      </Group>
      {data.length === 0 ? (
        <AllGood text="Alle überwachten Lebensmittel sind ausreichend vorrätig." />
      ) : (
        <Stack gap={6}>
          {data.slice(0, PREVIEW).map((l) => (
            <Group key={l.product_id} justify="space-between" wrap="nowrap" gap="xs">
              <Text size="sm" truncate component={Link} to={`/lebensmittel/${l.product_id}`}>
                {l.product_name}
              </Text>
              <Group gap="xs" wrap="nowrap">
                <Text size="sm" c="dimmed" visibleFrom="xs">
                  {formatQuantity(l.available_quantity, l.base_unit)} / min. {formatQuantity(l.minimum_stock, l.base_unit)}
                </Text>
                <StockLevelBadge status={l.status} size="xs" />
              </Group>
            </Group>
          ))}
          {data.length > PREVIEW && (
            <Text size="xs" c="dimmed">und {data.length - PREVIEW} weitere</Text>
          )}
        </Stack>
      )}
    </Card>
  );
}

/** Bald, heute oder bereits abgelaufene Lebensmittel (FR-EXP-004). */
function ExpiryCard() {
  const { data } = useExpiring();
  if (!data) return null;
  const red = data.items.filter((i) => i.expiry_status !== 'expiring').length;
  return (
    <Card withBorder>
      <Group justify="space-between" mb="xs">
        <Text fw={600}>Haltbarkeit</Text>
        <Anchor component={Link} to="/haltbarkeit" size="sm">
          Alle anzeigen
        </Anchor>
      </Group>
      {data.total === 0 ? (
        <AllGood text="Nichts läuft in den nächsten Tagen ab." />
      ) : (
        <Stack gap={6}>
          <Text size="sm" c={red ? 'red.8' : 'orange.8'} fw={600}>
            {red ? `${red} abgelaufen oder heute fällig` : ''}
            {red && data.total > red ? ' · ' : ''}
            {data.total > red ? `${data.total - red} bald` : ''}
          </Text>
          {data.items.slice(0, PREVIEW).map((i) => (
            <div key={i.id}>
              <Text size="sm" truncate component={Link} to={`/lebensmittel/${i.product_id}`} display="block">
                {i.product_name} · {i.location_path}
              </Text>
              <ExpiryText item={i} />
            </div>
          ))}
          {data.total > PREVIEW && (
            <Text size="xs" c="dimmed">und {data.total - PREVIEW} weitere</Text>
          )}
        </Stack>
      )}
    </Card>
  );
}

function AllGood({ text }: { text: string }) {
  return (
    <Group gap={6} wrap="nowrap">
      <IconCircleCheck size={18} color="var(--mantine-color-green-7)" aria-hidden />
      <Text size="sm" c="dimmed">{text}</Text>
    </Group>
  );
}

/** Startseite (Spez. 9.2/9.3) mit kompakten Warnungen. Die Einkaufsliste folgt in Phase 5b. */
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
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <ExpiryCard />
        <LowStockCard />
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
