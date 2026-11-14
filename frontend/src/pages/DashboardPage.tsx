import { Button, Card, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { IconPackageImport, IconPackages } from '@tabler/icons-react';
import { Link } from 'react-router-dom';
import { useProducts, useStock } from '../api/hooks';
import { useUser } from '../auth/AuthContext';

/** Startseite. Warnungen, Einkaufsliste und letzte Bewegungen folgen in Phase 3 und 5. */
export function DashboardPage() {
  const user = useUser();
  const products = useProducts({ limit: 1 });
  const stock = useStock({});
  return (
    <Stack>
      <Title order={2}>Hallo {user.display_name}</Title>
      <SimpleGrid cols={2}>
        <Button component={Link} to="/einlagern" size="xl" h={88} leftSection={<IconPackageImport size={28} />}>
          Einlagern
        </Button>
        <Button component={Link} to="/vorraete" size="xl" h={88} variant="light" leftSection={<IconPackages size={28} />}>
          Vorräte
        </Button>
      </SimpleGrid>
      <SimpleGrid cols={{ base: 2, sm: 4 }}>
        <Card withBorder>
          <Text size="xs" c="dimmed">Lebensmittel</Text>
          <Text size="xl" fw={700}>{products.data?.total ?? '–'}</Text>
        </Card>
        <Card withBorder>
          <Text size="xs" c="dimmed">Bestandspositionen</Text>
          <Text size="xl" fw={700}>{stock.data?.total ?? '–'}</Text>
        </Card>
      </SimpleGrid>
    </Stack>
  );
}
