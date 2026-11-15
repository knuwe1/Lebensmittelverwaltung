import { useState } from 'react';
import {
  Badge,
  Button,
  Card,
  Group,
  Modal,
  Pagination,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Textarea,
  Title,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useBooking } from '../api/booking';
import { api } from '../api/client';
import type { Movement, Page } from '../api/types';
import { LocationSelect } from '../components/selects';
import { DISPOSAL_REASONS, formatDateTime, formatQuantity, MOVEMENT_LABELS } from '../lib/format';

const PAGE_SIZE = 50;
const COLORS: Record<string, string> = {
  receipt: 'green',
  consumption: 'blue',
  transfer_out: 'grape',
  transfer_in: 'grape',
  disposal: 'red',
  reversal: 'gray',
  inventory_correction: 'orange',
};

export function useMovements(params: Record<string, string | number | null | undefined>) {
  return useQuery({
    queryKey: ['movements', params],
    queryFn: ({ signal }) => api.get<Page<Movement>>('/stock/movements', params, signal),
    placeholderData: (prev) => prev,
  });
}

export function MovementBadge({ m }: { m: Movement }) {
  return (
    <Badge color={COLORS[m.movement_type]} variant="light">
      {MOVEMENT_LABELS[m.movement_type]}
    </Badge>
  );
}

export function signedQuantity(m: Movement): string {
  const sign = m.quantity_delta > 0 ? '+' : '−';
  return `${sign} ${formatQuantity(Math.abs(m.quantity_delta), m.base_unit)}`;
}

function placeOf(m: Movement): string {
  return m.movement_type === 'transfer_out' || m.movement_type === 'transfer_in'
    ? `${m.source_location_path ?? '?'} → ${m.target_location_path ?? '?'}`
    : (m.target_location_path ?? m.source_location_path ?? '–');
}

function noteOf(m: Movement): string {
  return [m.reason ? (DISPOSAL_REASONS[m.reason] ?? m.reason) : null, m.comment].filter(Boolean).join(' · ');
}

function ReverseDialog({ movement, onClose }: { movement: Movement | null; onClose: () => void }) {
  const [comment, setComment] = useState('');
  const booking = useBooking(`/stock/transactions/${movement?.transaction_id}/reversal`, () => {
    notifications.show({ color: 'green', message: 'Buchung storniert.' });
    onClose();
  });
  return (
    <Modal opened={movement !== null} onClose={onClose} title="Buchung stornieren">
      {movement && (
        <Stack>
          <Text size="sm">
            {MOVEMENT_LABELS[movement.movement_type]} von {movement.product_name} ({signedQuantity(movement)}) am{' '}
            {formatDateTime(movement.created_at)} wird durch eine Gegenbuchung aufgehoben. Die ursprüngliche
            Buchung bleibt in der Historie sichtbar.
          </Text>
          <Textarea label="Begründung (optional)" value={comment} onChange={(e) => setComment(e.currentTarget.value)} />
          <Button color="red" loading={booking.isPending} onClick={() => booking.mutate({ comment: comment.trim() || null })}>
            Stornieren
          </Button>
        </Stack>
      )}
    </Modal>
  );
}

/** Nachvollziehbarkeit aller Bestandsbewegungen (Spezifikation 9.2 „Historie“). */
export function HistoryPage() {
  const [type, setType] = useState<string | null>(null);
  const [locationId, setLocationId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [reverse, setReverse] = useState<Movement | null>(null);
  const { data } = useMovements({
    movement_type: type,
    location_id: locationId,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });

  const isMobile = useMediaQuery('(max-width: 48em)') ?? false;
  // Storno-Schaltfläche nur einmal je Vorgang (z. B. Umlagerung = 2 Bewegungen)
  const seen = new Set<string>();
  const rows = (data?.items ?? []).map((m) => {
    const first = !seen.has(m.transaction_id);
    seen.add(m.transaction_id);
    const canReverse =
      first && !m.reversed && m.movement_type !== 'reversal' && m.movement_type !== 'inventory_correction';
    return { m, canReverse };
  });

  return (
    <Stack>
      <Title order={2}>Historie</Title>
      <SimpleGrid cols={{ base: 1, sm: 2 }} maw={640}>
        <Select
          placeholder="Alle Bewegungsarten"
          clearable
          data={Object.entries(MOVEMENT_LABELS).map(([value, label]) => ({ value, label }))}
          value={type}
          onChange={(v) => {
            setType(v);
            setPage(1);
          }}
        />
        <LocationSelect
          label={null}
          placeholder="Alle Lagerplätze"
          clearable
          value={locationId}
          onChange={(v) => {
            setLocationId(v);
            setPage(1);
          }}
        />
      </SimpleGrid>

      {isMobile ? (
        <Stack gap="xs">
          {rows.map(({ m, canReverse }) => (
            <Card key={m.id} withBorder padding="sm" style={m.reversed ? { opacity: 0.55 } : undefined}>
              <Group justify="space-between" wrap="nowrap" gap="xs">
                <MovementBadge m={m} />
                <Text size="sm" fw={600} c={m.quantity_delta > 0 ? 'green' : 'red'}>
                  {signedQuantity(m)}
                </Text>
              </Group>
              <Text component={Link} to={`/lebensmittel/${m.product_id}`} fw={500} mt={4}>
                {m.product_name}
              </Text>
              <Text size="sm" c="dimmed">
                {placeOf(m)}
              </Text>
              {noteOf(m) && <Text size="sm">{noteOf(m)}</Text>}
              <Group justify="space-between" mt={4}>
                <Text size="xs" c="dimmed">
                  {formatDateTime(m.created_at)} · {m.created_by_name}
                  {m.reversed && ' · storniert'}
                </Text>
                {canReverse && (
                  <Button size="compact-sm" variant="subtle" color="red" onClick={() => setReverse(m)}>
                    Stornieren
                  </Button>
                )}
              </Group>
            </Card>
          ))}
        </Stack>
      ) : (
      <Table.ScrollContainer minWidth={760}>
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Zeitpunkt</Table.Th>
              <Table.Th>Art</Table.Th>
              <Table.Th>Lebensmittel</Table.Th>
              <Table.Th>Menge</Table.Th>
              <Table.Th>Lagerplatz</Table.Th>
              <Table.Th>Benutzer</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.map(({ m, canReverse }) => {
              const place = placeOf(m);
              return (
                <Table.Tr key={m.id} style={m.reversed ? { opacity: 0.55 } : undefined}>
                  <Table.Td>
                    <Text size="sm">{formatDateTime(m.created_at)}</Text>
                  </Table.Td>
                  <Table.Td>
                    <MovementBadge m={m} />
                    {m.reversed && (
                      <Text size="xs" c="dimmed">
                        storniert
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Link to={`/lebensmittel/${m.product_id}`}>{m.product_name}</Link>
                    {noteOf(m) && (
                      <Text size="xs" c="dimmed">
                        {noteOf(m)}
                      </Text>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" c={m.quantity_delta > 0 ? 'green' : 'red'}>
                      {signedQuantity(m)}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{place}</Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">{m.created_by_name}</Text>
                  </Table.Td>
                  <Table.Td>
                    {canReverse && (
                      <Button size="compact-xs" variant="subtle" color="red" onClick={() => setReverse(m)}>
                        Stornieren
                      </Button>
                    )}
                  </Table.Td>
                </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
      )}
      {data?.total === 0 && (
        <Text c="dimmed" ta="center">
          Keine Bewegungen gefunden.
        </Text>
      )}
      {data && data.total > PAGE_SIZE && (
        <Group justify="center">
          <Pagination total={Math.ceil(data.total / PAGE_SIZE)} value={page} onChange={setPage} />
        </Group>
      )}
      <ReverseDialog key={reverse?.id} movement={reverse} onClose={() => setReverse(null)} />
    </Stack>
  );
}
