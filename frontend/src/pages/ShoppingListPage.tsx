import { useState } from 'react';
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  Loader,
  Menu,
  Modal,
  NumberInput,
  SegmentedControl,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  IconDots,
  IconEdit,
  IconPackageImport,
  IconPlus,
  IconRefresh,
  IconTrash,
} from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { api, errorMessage } from '../api/client';
import { queryKeys, useShoppingList } from '../api/hooks';
import type { Product, RefreshResult, ShoppingItem, ShoppingList } from '../api/types';
import { ProductSearch } from '../components/ProductSearch';
import { StockLevelBadge } from '../components/StockLevelBadge';
import { formatNumber, formatQuantity, unitShort, variantLabel } from '../lib/format';
import type { ReceiveState } from './ReceivePage';

/** Menge einer Position: „5 × 1 l“, „500 g“, bei Freitext „2 ×“, sonst „Menge offen“. */
export function shoppingQuantity(item: ShoppingItem): string {
  if (item.quantity == null) return 'Menge offen';
  if (!item.base_unit) return `${formatNumber(item.quantity)} ×`;
  if (item.package && item.packages != null) return `${formatNumber(item.packages)} × ${variantLabel(item.package)}`;
  return formatQuantity(item.quantity, item.base_unit);
}

function useListMutation<T>(fn: (arg: T) => Promise<ShoppingItem | ShoppingList | null>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (r) => {
      if (r && 'items' in r) qc.setQueryData(['shopping-list'], r);
      else if (r)
        qc.setQueryData<ShoppingList>(['shopping-list'], (old) =>
          old && { ...old, items: old.items.some((i) => i.id === r.id) ? old.items.map((i) => (i.id === r.id ? r : i)) : [...old.items, r] },
        );
      qc.invalidateQueries({ queryKey: ['shopping-list'] });
    },
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });
}

function ItemRow({ item, onEdit }: { item: ShoppingItem; onEdit: (i: ShoppingItem) => void }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const patch = useListMutation((body: object) => api.patch<ShoppingItem>(`/shopping-list/items/${item.id}`, body));
  // Abhaken sofort anzeigen (schlechter Empfang im Laden); bei Fehler lädt die Liste neu.
  const toggle = useMutation({
    mutationFn: (status: 'open' | 'purchased') => api.patch<ShoppingItem>(`/shopping-list/items/${item.id}`, { status }),
    onMutate: (status) =>
      qc.setQueryData<ShoppingList>(['shopping-list'], (old) =>
        old && { ...old, items: old.items.map((i) => (i.id === item.id ? { ...i, status } : i)) },
      ),
    onSuccess: (r) =>
      qc.setQueryData<ShoppingList>(['shopping-list'], (old) => old && { ...old, items: old.items.map((i) => (i.id === r.id ? r : i)) }),
    onError: (e) => {
      notifications.show({ color: 'red', message: errorMessage(e) });
      qc.invalidateQueries({ queryKey: ['shopping-list'] });
    },
  });
  const remove = useListMutation(async () => {
    await api.delete(`/shopping-list/items/${item.id}`);
    qc.setQueryData<ShoppingList>(['shopping-list'], (old) => old && { ...old, items: old.items.filter((i) => i.id !== item.id) });
    return null;
  });
  const receive = async () => {
    try {
      const product = await qc.fetchQuery({
        queryKey: queryKeys.product(item.product_id!),
        queryFn: () => api.get<Product>(`/products/${item.product_id}`),
      });
      const state: ReceiveState = { product, shoppingItem: item };
      navigate('/einlagern', { state });
    } catch (e) {
      notifications.show({ color: 'red', message: errorMessage(e) });
    }
  };

  const done = item.status === 'done';
  const purchased = item.status === 'purchased';
  const unit = item.base_unit ? unitShort(item.base_unit) : '';
  return (
    <Card withBorder padding="sm" opacity={done ? 0.6 : 1}>
      <Group wrap="nowrap" align="flex-start" gap="sm">
        {!item.optional && !done && (
          <Checkbox
            size="lg"
            mt={2}
            checked={purchased}
            onChange={() => toggle.mutate(purchased ? 'open' : 'purchased')}
            // Feste Beschriftung; den Zustand liefert das Kästchen selbst (angehakt = gekauft)
            aria-label={`${item.name} gekauft`}
          />
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <Group justify="space-between" wrap="nowrap" gap="xs">
            <Text fw={600} truncate td={purchased || done ? 'line-through' : undefined}>
              {item.name}
            </Text>
            <Text fw={600} style={{ flexShrink: 0 }}>
              {shoppingQuantity(item)}
            </Text>
          </Group>
          <Group gap={6} mt={2}>
            <Badge size="xs" variant="light" color={item.origin === 'auto' ? 'blue' : 'gray'}>
              {item.origin === 'auto' ? 'Vorschlag' : 'Manuell'}
            </Badge>
            {item.level_status && item.level_status !== 'ok' && !done && <StockLevelBadge status={item.level_status} size="xs" />}
            {item.brand && (
              <Text size="xs" c="dimmed">
                {item.brand}
              </Text>
            )}
          </Group>
          {item.minimum_stock != null && item.available_quantity != null && !done && (
            <Text size="xs" c="dimmed" mt={2}>
              Bestand {formatNumber(item.available_quantity)} {unit} · min. {formatNumber(item.minimum_stock)} {unit}
              {item.target_stock != null && ` · Ziel ${formatNumber(item.target_stock)} ${unit}`}
            </Text>
          )}
          {done && item.received_quantity > 0 && item.base_unit && (
            <Text size="xs" c="dimmed">
              {formatQuantity(item.received_quantity, item.base_unit)} eingelagert
            </Text>
          )}
          {item.comment && (
            <Text size="sm" fs="italic" mt={2}>
              {item.comment}
            </Text>
          )}
          {(item.optional || purchased) && (
            <Group gap="xs" mt="xs">
              {item.optional && (
                <Button size="xs" variant="light" leftSection={<IconPlus size={16} />} onClick={() => patch.mutate({ optional: false })}>
                  Übernehmen
                </Button>
              )}
              {purchased && item.product_id && (
                <Button size="xs" leftSection={<IconPackageImport size={16} />} onClick={receive}>
                  Einlagern
                </Button>
              )}
              {purchased && (
                <Button size="xs" variant="subtle" onClick={() => patch.mutate({ status: 'done' })}>
                  {item.product_id ? 'Ohne Einlagern erledigt' : 'Erledigt'}
                </Button>
              )}
            </Group>
          )}
        </div>
        {!done && (
          <Menu position="bottom-end" withinPortal>
            <Menu.Target>
              <ActionIcon variant="subtle" aria-label={`Aktionen für ${item.name}`}>
                <IconDots size={18} />
              </ActionIcon>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item leftSection={<IconEdit size={16} />} onClick={() => onEdit(item)}>
                Menge / Kommentar
              </Menu.Item>
              <Menu.Item color="red" leftSection={<IconTrash size={16} />} onClick={() => remove.mutate(undefined)}>
                Entfernen
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        )}
      </Group>
    </Card>
  );
}

/** Menge in Packungen, wenn das Produkt eine Standardverpackung hat, sonst in der Basiseinheit. */
function QuantityInput({
  item,
  product,
  value,
  onChange,
}: {
  item?: ShoppingItem;
  product?: Product;
  value: string | number;
  onChange: (v: string | number) => void;
}) {
  const pkg = item ? item.package : product?.variants.find((v) => v.active && v.is_default);
  const base = item ? item.base_unit : product?.base_unit;
  const label = !base ? 'Anzahl' : pkg ? `Anzahl Packungen (${variantLabel(pkg)})` : `Menge (${unitShort(base)})`;
  return (
    <NumberInput
      label={label}
      min={0}
      decimalScale={3}
      decimalSeparator=","
      thousandSeparator="."
      inputMode="decimal"
      value={value}
      onChange={onChange}
    />
  );
}

function toBase(value: string | number, packageSize: number | undefined): number | null {
  const n = Number(value);
  if (!n || n <= 0) return null;
  return packageSize ? n * packageSize : n;
}

function EditModal({ item, onClose }: { item: ShoppingItem | null; onClose: () => void }) {
  const [qty, setQty] = useState<string | number>('');
  const [comment, setComment] = useState('');
  const [loadedFor, setLoadedFor] = useState<string | null>(null);
  if (item && loadedFor !== item.id) {
    setLoadedFor(item.id);
    setQty(item.package ? (item.packages ?? '') : (item.quantity ?? ''));
    setComment(item.comment ?? '');
  }
  const save = useListMutation((body: object) => api.patch<ShoppingItem>(`/shopping-list/items/${item!.id}`, body));
  const submit = (reset = false) =>
    save.mutate(
      reset ? { quantity: null, comment } : { quantity: toBase(qty, item?.package?.base_quantity), comment },
      { onSuccess: onClose },
    );
  return (
    <Modal opened={!!item} onClose={onClose} title={item?.name}>
      {item && (
        <Stack>
          <QuantityInput item={item} value={qty} onChange={setQty} />
          {item.quantity_adjusted && item.suggested_quantity != null && (
            <Button variant="subtle" size="xs" onClick={() => submit(true)}>
              Auf Vorschlag zurücksetzen
            </Button>
          )}
          <Textarea label="Kommentar" autosize minRows={2} value={comment} onChange={(e) => setComment(e.currentTarget.value)} />
          <Button onClick={() => submit()} loading={save.isPending}>
            Speichern
          </Button>
        </Stack>
      )}
    </Modal>
  );
}

function AddModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const [kind, setKind] = useState<'product' | 'text'>('product');
  const [product, setProduct] = useState<Product | null>(null);
  const [name, setName] = useState('');
  const [qty, setQty] = useState<string | number>('');
  const [comment, setComment] = useState('');
  const close = () => {
    setProduct(null);
    setName('');
    setQty('');
    setComment('');
    onClose();
  };
  const add = useListMutation((body: object) => api.post<ShoppingItem>('/shopping-list/items', body));
  const pkg = product?.variants.find((v) => v.active && v.is_default);
  const submit = () =>
    add.mutate(
      kind === 'product'
        ? { product_id: product!.id, quantity: toBase(qty, pkg?.base_quantity), comment: comment || null }
        : { name, quantity: toBase(qty, undefined), comment: comment || null },
      {
        onSuccess: () => {
          notifications.show({ color: 'green', message: 'Zur Einkaufsliste hinzugefügt.' });
          close();
        },
      },
    );
  const ready = kind === 'product' ? !!product : name.trim().length > 0;
  return (
    <Modal opened={opened} onClose={close} title="Zur Einkaufsliste hinzufügen">
      <Stack>
        <SegmentedControl
          fullWidth
          value={kind}
          onChange={(v) => setKind(v as 'product' | 'text')}
          data={[
            { value: 'product', label: 'Lebensmittel' },
            { value: 'text', label: 'Freier Text' },
          ]}
        />
        {kind === 'product' &&
          (product ? (
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
          ))}
        {kind === 'text' && (
          <TextInput label="Was?" placeholder="z. B. Backpapier" value={name} onChange={(e) => setName(e.currentTarget.value)} />
        )}
        {(kind === 'text' || product) && (
          <>
            <QuantityInput product={product ?? undefined} value={qty} onChange={setQty} />
            <TextInput label="Kommentar" value={comment} onChange={(e) => setComment(e.currentTarget.value)} />
            <Button onClick={submit} disabled={!ready} loading={add.isPending}>
              Hinzufügen
            </Button>
          </>
        )}
      </Stack>
    </Modal>
  );
}

function Section({ title, hint, items, onEdit }: { title: string; hint?: string; items: ShoppingItem[]; onEdit: (i: ShoppingItem) => void }) {
  if (!items.length) return null;
  return (
    <Stack gap="xs">
      <div>
        <Text fw={600}>
          {title} ({items.length})
        </Text>
        {hint && (
          <Text size="xs" c="dimmed">
            {hint}
          </Text>
        )}
      </div>
      {items.map((i) => (
        <ItemRow key={i.id} item={i} onEdit={onEdit} />
      ))}
    </Stack>
  );
}

/** Gemeinsame Einkaufsliste (FR-SHP-005…010, Spez. 9.2/9.3). */
export function ShoppingListPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useShoppingList();
  const [editing, setEditing] = useState<ShoppingItem | null>(null);
  const [adding, setAdding] = useState(false);

  const refresh = useMutation({
    mutationFn: () => api.post<RefreshResult>('/shopping-list/refresh'),
    onSuccess: (r) => {
      qc.setQueryData(['shopping-list'], r.list);
      const parts = [
        r.added && `${r.added} neu`,
        r.updated && `${r.updated} aktualisiert`,
        r.removed && `${r.removed} entfernt`,
      ].filter(Boolean);
      notifications.show({
        color: 'green',
        message: parts.length ? `Bedarf ermittelt: ${parts.join(', ')}.` : 'Bedarf ermittelt – keine Änderungen.',
      });
    },
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });
  const clearDone = useListMutation(() => api.post<ShoppingList>('/shopping-list/clear-done'));

  const items = data?.items ?? [];
  const open = items.filter((i) => i.status === 'open' && !i.optional);
  const optional = items.filter((i) => i.status === 'open' && i.optional);
  const purchased = items.filter((i) => i.status === 'purchased');
  const done = items.filter((i) => i.status === 'done');

  return (
    <Stack maw={640} mx="auto">
      <Title order={2}>Einkaufsliste</Title>
      <Group grow>
        <Button variant="light" leftSection={<IconRefresh size={18} />} onClick={() => refresh.mutate()} loading={refresh.isPending}>
          Bedarf ermitteln
        </Button>
        <Button leftSection={<IconPlus size={18} />} onClick={() => setAdding(true)}>
          Hinzufügen
        </Button>
      </Group>

      {isLoading && <Loader mx="auto" />}
      {data && items.length === 0 && (
        <Text c="dimmed" ta="center" py="xl">
          Die Einkaufsliste ist leer. „Bedarf ermitteln“ schlägt Lebensmittel unter dem Mindestbestand vor.
        </Text>
      )}

      <Section title="Einkaufen" items={open} onEdit={setEditing} />
      <Section
        title="Optional"
        hint="Nahe am Mindestbestand – bei Bedarf übernehmen."
        items={optional}
        onEdit={setEditing}
      />
      <Section
        title="Gekauft"
        hint="Erst das Einlagern erhöht den Bestand."
        items={purchased}
        onEdit={setEditing}
      />
      {done.length > 0 && (
        <Stack gap="xs">
          <Group justify="space-between">
            <Text fw={600}>Erledigt ({done.length})</Text>
            <Button size="xs" variant="subtle" color="gray" onClick={() => clearDone.mutate(undefined)} loading={clearDone.isPending}>
              Erledigte entfernen
            </Button>
          </Group>
          {done.map((i) => (
            <ItemRow key={i.id} item={i} onEdit={setEditing} />
          ))}
        </Stack>
      )}

      <EditModal item={editing} onClose={() => setEditing(null)} />
      <AddModal opened={adding} onClose={() => setAdding(false)} />
    </Stack>
  );
}
