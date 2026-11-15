import { useState } from 'react';
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Loader,
  Modal,
  NumberInput,
  Progress,
  SegmentedControl,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { IconAlertTriangle, IconArrowLeft, IconCheck, IconPlus, IconTrash } from '@tabler/icons-react';
import { Link, useParams } from 'react-router-dom';
import { api, ApiError, errorMessage } from '../api/client';
import type { ExpiryType, Inventory, InventoryItem, Product } from '../api/types';
import { useUser } from '../auth/AuthContext';
import { GermanDateInput } from '../components/GermanDateInput';
import { ProductSearch } from '../components/ProductSearch';
import { LocationSelect } from '../components/selects';
import { EXPIRY_TYPE_LABELS, formatDate, formatDateTime, formatNumber, formatQuantity, toIsoDate, unitShort } from '../lib/format';
import { INVENTORY_STATUS } from './InventoryPage';

const EXPIRY_SHORT: Record<ExpiryType, string> = {
  best_before: 'MHD',
  use_by: 'Verbr.',
  none: 'ohne Datum',
  unknown: 'Datum unbekannt',
};

function expiryLabel(i: InventoryItem): string {
  return i.expiry_date ? `${EXPIRY_SHORT[i.expiry_type]} ${formatDate(i.expiry_date)}` : EXPIRY_SHORT[i.expiry_type];
}

function signed(value: number, unit: InventoryItem['base_unit']): string {
  if (value === 0) return `0 ${unitShort(unit)}`;
  return `${value > 0 ? '+' : '−'}${formatQuantity(Math.abs(value), unit)}`;
}

function DiffText({ value, unit }: { value: number | null; unit: InventoryItem['base_unit'] }) {
  if (value === null) return <Text span c="dimmed">–</Text>;
  return (
    <Text span fw={value ? 600 : undefined} c={value < 0 ? 'red.8' : value > 0 ? 'green.8' : 'dimmed'}>
      {signed(value, unit)}
    </Text>
  );
}

function useInventoryMutation<T>(id: string, fn: (arg: T) => Promise<Inventory>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (inv) => {
      qc.setQueryData(['inventory', id], inv);
      qc.invalidateQueries({ queryKey: ['inventories'] });
    },
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });
}

/** Eingabe des Istbestands; gespeichert wird beim Verlassen des Feldes bzw. mit Enter. */
function CountInput({ inv, item, disabled }: { inv: Inventory; item: InventoryItem; disabled: boolean }) {
  const [value, setValue] = useState<string | number>(item.counted_quantity ?? '');
  const [syncedFrom, setSyncedFrom] = useState(item.counted_quantity);
  if (syncedFrom !== item.counted_quantity) {
    setSyncedFrom(item.counted_quantity);
    setValue(item.counted_quantity ?? '');
  }
  const save = useInventoryMutation(inv.id, (counted: number | null) =>
    api.patch<Inventory>(`/inventories/${inv.id}/items/${item.id}`, { counted_quantity: counted }),
  );
  const commit = () => {
    const next = value === '' ? null : Number(value);
    // Bei einem Konflikt gilt auch das Bestätigen des gleichen Werts als erneute Prüfung
    if (next !== item.counted_quantity || (item.conflict && next !== null)) save.mutate(next);
  };
  return (
    <NumberInput
      aria-label={`Ist ${item.product_name} ${expiryLabel(item)}`}
      placeholder="Ist"
      min={0}
      decimalScale={3}
      decimalSeparator=","
      thousandSeparator="."
      inputMode="decimal"
      hideControls
      rightSection={<Text size="xs" c="dimmed">{unitShort(item.base_unit)}</Text>}
      w={130}
      value={value}
      onChange={setValue}
      onBlur={commit}
      onKeyDown={(e) => e.key === 'Enter' && (e.currentTarget as HTMLInputElement).blur()}
      disabled={disabled || save.isPending}
      error={item.conflict ? true : undefined}
    />
  );
}

function ItemRow({ inv, item, editable }: { inv: Inventory; item: InventoryItem; editable: boolean }) {
  const remove = useInventoryMutation(inv.id, () => api.delete<Inventory>(`/inventories/${inv.id}/items/${item.id}`));
  const done = inv.status === 'completed';
  return (
    <Card withBorder padding="sm">
      <Group justify="space-between" wrap="nowrap" align="flex-start" gap="xs">
        <div style={{ minWidth: 0, flex: 1 }}>
          <Group gap={6} wrap="nowrap">
            <Text fw={600} truncate>
              {item.product_name}
            </Text>
            {item.is_new && (
              <Badge size="xs" variant="light">
                Ergänzt
              </Badge>
            )}
          </Group>
          <Text size="xs" c="dimmed">
            {expiryLabel(item)}
            {item.product_brand && ` · ${item.product_brand}`}
          </Text>
          <Group gap="md" mt={4}>
            <Text size="sm">
              Soll <b>{formatQuantity(item.expected_quantity, item.base_unit)}</b>
            </Text>
            {!editable && item.counted_quantity !== null && (
              <Text size="sm">
                Ist <b>{formatQuantity(item.counted_quantity, item.base_unit)}</b>
              </Text>
            )}
            <Text size="sm">
              {done ? 'Korrektur ' : 'Differenz '}
              <DiffText value={done ? item.applied_delta : item.difference} unit={item.base_unit} />
            </Text>
          </Group>
        </div>
        {editable && <CountInput inv={inv} item={item} disabled={false} />}
        {editable && item.is_new && (
          <ActionIcon variant="subtle" color="red" mt={6} onClick={() => remove.mutate(undefined)} aria-label={`${item.product_name} entfernen`}>
            <IconTrash size={18} />
          </ActionIcon>
        )}
      </Group>
      {item.conflict && (
        <Alert color="orange" variant="light" mt="xs" py={6} icon={<IconAlertTriangle size={16} />}>
          {item.conflict_reason === 'new'
            ? 'Seit dem Start neu eingelagert – bitte zählen.'
            : `Seit dem Start gebucht: aktueller Bestand ${formatQuantity(item.current_quantity ?? 0, item.base_unit)}. Bitte erneut zählen und bestätigen.`}
        </Alert>
      )}
    </Card>
  );
}

function AddItemModal({ inv, opened, onClose }: { inv: Inventory; opened: boolean; onClose: () => void }) {
  const [product, setProduct] = useState<Product | null>(null);
  const [locationId, setLocationId] = useState<string | null>(inv.location_ids.length === 1 ? inv.location_ids[0] : null);
  const [expiryType, setExpiryType] = useState<ExpiryType>('unknown');
  const [expiryDate, setExpiryDate] = useState<Date | null>(null);
  const [qty, setQty] = useState<string | number>('');
  const needsDate = expiryType === 'best_before' || expiryType === 'use_by';
  const close = () => {
    setProduct(null);
    setQty('');
    setExpiryDate(null);
    onClose();
  };
  const add = useInventoryMutation(inv.id, () =>
    api.post<Inventory>(`/inventories/${inv.id}/items`, {
      product_id: product!.id,
      location_id: locationId,
      expiry_type: expiryType,
      expiry_date: needsDate && expiryDate ? toIsoDate(expiryDate) : null,
      counted_quantity: Number(qty),
    }),
  );
  const valid = !!product && !!locationId && Number(qty) > 0 && (!needsDate || !!expiryDate);
  return (
    <Modal opened={opened} onClose={close} title="Lebensmittel ergänzen">
      <Stack>
        <Text size="sm" c="dimmed">
          Für Lebensmittel, die gefunden wurden, aber nicht im Bestand stehen (FR-INV-005). Gebucht
          wird erst beim Abschluss.
        </Text>
        {product ? (
          <Group justify="space-between" wrap="nowrap">
            <Text fw={600} truncate>
              {product.name}
            </Text>
            <Button variant="subtle" size="xs" onClick={() => setProduct(null)}>
              Ändern
            </Button>
          </Group>
        ) : (
          <ProductSearch onSelect={(p) => setProduct(p)} />
        )}
        {product && (
          <>
            <LocationSelect onlyIds={inv.location_ids} value={locationId} onChange={setLocationId} required />
            <SegmentedControl
              fullWidth
              size="xs"
              value={expiryType}
              onChange={(v) => setExpiryType(v as ExpiryType)}
              data={[
                { value: 'best_before', label: 'MHD' },
                { value: 'use_by', label: 'Verbrauch' },
                { value: 'none', label: 'Kein' },
                { value: 'unknown', label: 'Unbekannt' },
              ]}
            />
            {needsDate && <GermanDateInput label={EXPIRY_TYPE_LABELS[expiryType]} value={expiryDate} onChange={setExpiryDate} />}
            <NumberInput
              label={`Gezählte Menge (${unitShort(product.base_unit)})`}
              min={0}
              decimalScale={3}
              decimalSeparator=","
              thousandSeparator="."
              inputMode="decimal"
              value={qty}
              onChange={setQty}
            />
            <Button disabled={!valid} loading={add.isPending} onClick={() => add.mutate(undefined, { onSuccess: close })}>
              Ergänzen
            </Button>
          </>
        )}
      </Stack>
    </Modal>
  );
}

function CompleteModal({ inv, opened, onClose }: { inv: Inventory; opened: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const changes = (inv.items ?? []).filter((i) => i.difference);
  const complete = useMutation({
    mutationFn: () => api.post<Inventory>(`/inventories/${inv.id}/complete`),
    onSuccess: (r) => {
      qc.setQueryData(['inventory', inv.id], r);
      qc.invalidateQueries({ queryKey: ['inventories'] });
      qc.invalidateQueries({ queryKey: ['stock'] });
      qc.invalidateQueries({ queryKey: ['products'] });
      qc.invalidateQueries({ queryKey: ['movements'] });
      qc.invalidateQueries({ queryKey: ['shopping-list'] });
      notifications.show({ color: 'green', message: `Inventur abgeschlossen – ${changes.length} Korrektur(en) gebucht.` });
      onClose();
    },
    onError: (e) => {
      if (e instanceof ApiError && e.code === 'inventory_conflict') {
        qc.invalidateQueries({ queryKey: ['inventory', inv.id] });
        onClose();
      }
      notifications.show({ color: 'red', message: errorMessage(e), autoClose: 8000 });
    },
  });
  return (
    <Modal opened={opened} onClose={onClose} title="Inventur abschließen" size="lg">
      <Stack>
        {changes.length === 0 ? (
          <Text>Keine Abweichungen – der Bestand bleibt unverändert.</Text>
        ) : (
          <>
            <Text size="sm">Folgende Korrekturen werden gebucht (FR-INV-004):</Text>
            <Table.ScrollContainer minWidth={420}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Lebensmittel</Table.Th>
                    <Table.Th>Soll</Table.Th>
                    <Table.Th>Ist</Table.Th>
                    <Table.Th>Differenz</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {changes.map((i) => (
                    <Table.Tr key={i.id}>
                      <Table.Td>
                        {i.product_name}
                        <Text size="xs" c="dimmed">
                          {i.location_path} · {expiryLabel(i)}
                        </Text>
                      </Table.Td>
                      <Table.Td>{formatQuantity(i.expected_quantity, i.base_unit)}</Table.Td>
                      <Table.Td>{formatQuantity(i.counted_quantity ?? 0, i.base_unit)}</Table.Td>
                      <Table.Td>
                        <DiffText value={i.difference} unit={i.base_unit} />
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          </>
        )}
        <Button leftSection={<IconCheck size={18} />} loading={complete.isPending} onClick={() => complete.mutate()}>
          {changes.length ? 'Korrekturen buchen und abschließen' : 'Abschließen'}
        </Button>
      </Stack>
    </Modal>
  );
}

/** Inventurliste mit Soll, Ist und Differenz (FR-INV-002…009). */
export function InventoryDetailPage() {
  const { id = '' } = useParams();
  const user = useUser();
  const mayInventory = user.role === 'admin' || user.can_do_inventory;
  const { data: inv, isLoading } = useQuery({
    queryKey: ['inventory', id],
    queryFn: () => api.get<Inventory>(`/inventories/${id}`),
  });
  const [adding, setAdding] = useState(false);
  const [completing, setCompleting] = useState(false);
  const acceptRest = useInventoryMutation(id, () => api.post<Inventory>(`/inventories/${id}/accept-remaining`));
  const cancel = useInventoryMutation(id, () => api.post<Inventory>(`/inventories/${id}/cancel`));
  const qc = useQueryClient();
  const check = useMutation({
    mutationFn: () => api.post<unknown[]>(`/inventories/${id}/check`),
    onSuccess: (conflicts) => {
      qc.invalidateQueries({ queryKey: ['inventory', id] });
      notifications.show({
        color: conflicts.length ? 'orange' : 'green',
        message: conflicts.length
          ? `${conflicts.length} Position(en) seit dem Start verändert – bitte erneut zählen.`
          : 'Keine zwischenzeitlichen Buchungen.',
      });
    },
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });

  if (isLoading || !inv) return <Loader mx="auto" />;
  const editable = inv.status === 'open' && mayInventory;
  const items = inv.items ?? [];
  const groups = [...new Set(items.map((i) => i.location_path))];
  const s = inv.summary;

  return (
    <Stack maw={760} mx="auto">
      <Group gap="xs" wrap="nowrap">
        <ActionIcon variant="subtle" component={Link} to="/inventur" aria-label="Zur Übersicht">
          <IconArrowLeft />
        </ActionIcon>
        <Title order={2} style={{ minWidth: 0 }}>
          Inventur – {inv.scope_label}
        </Title>
      </Group>
      <Group gap="xs">
        <Badge variant="light" color={INVENTORY_STATUS[inv.status].color}>
          {INVENTORY_STATUS[inv.status].label}
        </Badge>
        <Text size="sm" c="dimmed">
          Begonnen {formatDateTime(inv.started_at)} von {inv.started_by_name}
          {inv.completed_at && ` · beendet ${formatDateTime(inv.completed_at)} von ${inv.completed_by_name}`}
        </Text>
      </Group>

      {inv.status === 'open' && (
        <>
          <div>
            <Group justify="space-between" mb={4}>
              <Text size="sm">
                {s.counted} von {s.total} gezählt · {s.differences} Abweichung(en)
              </Text>
              {s.conflicts > 0 && (
                <Text size="sm" c="orange.8" fw={600}>
                  {s.conflicts} erneut prüfen
                </Text>
              )}
            </Group>
            <Progress value={s.total ? (100 * s.counted) / s.total : 0} />
          </div>
          {editable && (
            <Group gap="xs">
              <Button variant="light" leftSection={<IconPlus size={18} />} onClick={() => setAdding(true)}>
                Lebensmittel ergänzen
              </Button>
              <Button variant="light" onClick={() => acceptRest.mutate(undefined)} loading={acceptRest.isPending} disabled={s.counted === s.total}>
                Rest wie Soll übernehmen
              </Button>
              <Button variant="subtle" onClick={() => check.mutate()} loading={check.isPending}>
                Auf Buchungen prüfen
              </Button>
            </Group>
          )}
        </>
      )}

      {items.length === 0 && (
        <Text c="dimmed" ta="center" py="lg">
          In diesem Bereich sind keine Bestände erfasst. Gefundene Lebensmittel über „Lebensmittel
          ergänzen“ aufnehmen.
        </Text>
      )}
      {groups.map((path) => (
        <Stack key={path} gap="xs">
          <Text fw={600}>{path}</Text>
          {items
            .filter((i) => i.location_path === path)
            .map((i) => (
              <ItemRow key={i.id} inv={inv} item={i} editable={editable} />
            ))}
        </Stack>
      ))}

      {editable && (
        <Group justify="space-between" mt="md">
          <Button variant="subtle" color="red" onClick={() => cancel.mutate(undefined)} loading={cancel.isPending}>
            Inventur abbrechen
          </Button>
          <Button size="md" leftSection={<IconCheck size={18} />} onClick={() => setCompleting(true)} disabled={s.counted < s.total || s.conflicts > 0}>
            Abschließen …
          </Button>
        </Group>
      )}
      {inv.status === 'completed' && (
        <Text size="sm" c="dimmed">
          {s.differences} Korrektur(en) gebucht ({formatNumber(s.total)} Positionen geprüft). Die
          Buchungen stehen in der <Link to="/historie">Historie</Link>.
        </Text>
      )}

      {editable && <AddItemModal inv={inv} opened={adding} onClose={() => setAdding(false)} />}
      {editable && <CompleteModal inv={inv} opened={completing} onClose={() => setCompleting(false)} />}
    </Stack>
  );
}
