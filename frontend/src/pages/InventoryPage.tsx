import { useState } from 'react';
import { Badge, Button, Card, Checkbox, Group, Loader, Stack, Table, Text, Title } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { IconClipboardList } from '@tabler/icons-react';
import { Link, useNavigate } from 'react-router-dom';
import { api, ApiError, errorMessage } from '../api/client';
import type { Inventory } from '../api/types';
import { useUser } from '../auth/AuthContext';
import { LocationSelect } from '../components/selects';
import { formatDateTime } from '../lib/format';

export const INVENTORY_STATUS: Record<Inventory['status'], { label: string; color: string }> = {
  open: { label: 'Offen', color: 'blue' },
  completed: { label: 'Abgeschlossen', color: 'green' },
  cancelled: { label: 'Abgebrochen', color: 'gray' },
};

export function useInventories() {
  return useQuery({ queryKey: ['inventories'], queryFn: () => api.get<Inventory[]>('/inventories') });
}

/** Inventur starten (FR-INV-001), offene fortsetzen (FR-INV-006), Protokoll (FR-INV-007). */
export function InventoryPage() {
  const user = useUser();
  const mayInventory = user.role === 'admin' || user.can_do_inventory;
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data, isLoading } = useInventories();
  const [locationId, setLocationId] = useState<string | null>(null);
  const [withSub, setWithSub] = useState(true);

  const start = useMutation({
    mutationFn: () =>
      api.post<Inventory>('/inventories', { location_id: locationId, include_sublocations: withSub }),
    onSuccess: (inv) => {
      qc.invalidateQueries({ queryKey: ['inventories'] });
      qc.setQueryData(['inventory', inv.id], inv);
      navigate(`/inventur/${inv.id}`);
    },
    onError: (e) => {
      const existing = e instanceof ApiError && e.code === 'inventory_overlap' ? (e.details as { inventory_id?: string })?.inventory_id : undefined;
      notifications.show({ color: 'red', message: errorMessage(e), autoClose: 8000 });
      if (existing) navigate(`/inventur/${existing}`);
    },
  });

  const open = (data ?? []).filter((i) => i.status === 'open');
  const history = (data ?? []).filter((i) => i.status !== 'open');

  return (
    <Stack>
      <Title order={2}>Inventur</Title>
      {mayInventory && (
        <Card withBorder>
          <Text fw={600} mb="xs">
            Neue Inventur
          </Text>
          <Stack gap="xs">
            <LocationSelect
              label="Bereich"
              placeholder="Gesamter Haushalt"
              clearable
              value={locationId}
              onChange={setLocationId}
            />
            {locationId && (
              <Checkbox
                label="Einschließlich Unterlagerplätzen"
                checked={withSub}
                onChange={(e) => setWithSub(e.currentTarget.checked)}
              />
            )}
            <Group>
              <Button leftSection={<IconClipboardList size={18} />} onClick={() => start.mutate()} loading={start.isPending}>
                Inventur starten
              </Button>
            </Group>
            <Text size="xs" c="dimmed">
              Die aktuellen Bestände werden als Soll festgehalten. Buchungen bleiben während der
              Inventur möglich; Änderungen werden vor dem Abschluss angezeigt.
            </Text>
          </Stack>
        </Card>
      )}

      {isLoading && <Loader mx="auto" />}
      {open.length > 0 && (
        <Stack gap="xs">
          <Text fw={600}>Offene Inventuren</Text>
          {open.map((inv) => (
            <Card key={inv.id} withBorder padding="sm" component={Link} to={`/inventur/${inv.id}`}>
              <Group justify="space-between" wrap="nowrap">
                <div style={{ minWidth: 0 }}>
                  <Text fw={600} truncate>
                    {inv.scope_label}
                  </Text>
                  <Text size="xs" c="dimmed">
                    Begonnen {formatDateTime(inv.started_at)} von {inv.started_by_name}
                  </Text>
                </div>
                <Text size="sm" style={{ flexShrink: 0 }}>
                  {inv.summary.counted} / {inv.summary.total} gezählt
                </Text>
              </Group>
            </Card>
          ))}
        </Stack>
      )}

      <Text fw={600}>Protokoll</Text>
      {data && history.length === 0 && (
        <Text size="sm" c="dimmed">
          Noch keine abgeschlossene Inventur.
        </Text>
      )}
      {history.length > 0 && (
        <Table.ScrollContainer minWidth={560}>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Beendet</Table.Th>
                <Table.Th>Bereich</Table.Th>
                <Table.Th>Von</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Abweichungen</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {history.map((inv) => (
                <Table.Tr key={inv.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/inventur/${inv.id}`)}>
                  <Table.Td>{inv.completed_at ? formatDateTime(inv.completed_at) : '–'}</Table.Td>
                  <Table.Td>{inv.scope_label}</Table.Td>
                  <Table.Td>{inv.completed_by_name ?? inv.started_by_name}</Table.Td>
                  <Table.Td>
                    <Badge variant="light" color={INVENTORY_STATUS[inv.status].color}>
                      {INVENTORY_STATUS[inv.status].label}
                    </Badge>
                  </Table.Td>
                  <Table.Td>{inv.status === 'completed' ? inv.summary.differences : '–'}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Stack>
  );
}
