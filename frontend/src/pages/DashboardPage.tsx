import { Stack, Text, Title } from '@mantine/core';
import { useUser } from '../auth/AuthContext';

export function DashboardPage() {
  const user = useUser();
  return (
    <Stack>
      <Title order={2}>Hallo {user.display_name}</Title>
      <Text c="dimmed">Die Übersicht wird in den folgenden Ausbaustufen ergänzt.</Text>
    </Stack>
  );
}
