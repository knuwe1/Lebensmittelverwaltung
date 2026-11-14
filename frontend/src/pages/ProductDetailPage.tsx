import { useState } from 'react';
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  FileButton,
  Group,
  Loader,
  Modal,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { IconArrowsTransferUp, IconCamera, IconEdit, IconPackageExport, IconPackageImport, IconPlus, IconScale, IconStar, IconTrash } from '@tabler/icons-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { api, errorMessage } from '../api/client';
import { useLocations, useProduct, useStock } from '../api/hooks';
import type { Product, StockItem, Variant } from '../api/types';
import { useUser } from '../auth/AuthContext';
import { ProductAvatar } from '../components/ProductAvatar';
import { ProductForm } from '../components/ProductForm';
import { COMPATIBLE_PACKAGE_UNITS, formatNumber, formatQuantity, PACKAGE_UNIT_LABELS, unitShort, variantLabel } from '../lib/format';
import { ExpiryText } from '../components/ExpiryText';
import { TransferDialog } from '../components/TransferDialog';

function VariantForm({ product, onDone }: { product: Product; onDone: () => void }) {
  const qc = useQueryClient();
  const units = COMPATIBLE_PACKAGE_UNITS[product.base_unit];
  const [qty, setQty] = useState<string | number>('');
  const [unit, setUnit] = useState(units[units.length - 1]);
  const [name, setName] = useState('');
  const [barcode, setBarcode] = useState('');
  const [tare, setTare] = useState<string | number>('');
  const mutation = useMutation({
    mutationFn: () =>
      api.post(`/products/${product.id}/variants`, {
        package_quantity: Number(qty),
        package_unit: unit,
        name: name.trim() || null,
        barcode: barcode.trim() || null,
        tare_weight: tare === '' ? null : Number(tare),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['product', product.id] });
      onDone();
    },
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });
  return (
    <Stack>
      <SimpleGrid cols={2}>
        <NumberInput label="Packungsgröße" decimalSeparator="," thousandSeparator="." min={0} value={qty} onChange={setQty} required />
        <Select label="Einheit" data={units.map((u) => ({ value: u, label: PACKAGE_UNIT_LABELS[u] }))} value={unit} onChange={(v) => v && setUnit(v)} allowDeselect={false} />
      </SimpleGrid>
      <TextInput label="Bezeichnung (optional)" placeholder="z. B. Familienpackung" value={name} onChange={(e) => setName(e.currentTarget.value)} />
      <TextInput label="Barcode (optional)" inputMode="numeric" value={barcode} onChange={(e) => setBarcode(e.currentTarget.value)} />
      {product.base_unit === 'g' && (
        <NumberInput label="Leergewicht Verpackung (g, optional)" decimalSeparator="," min={0} value={tare} onChange={setTare} />
      )}
      <Button onClick={() => mutation.mutate()} loading={mutation.isPending} disabled={!(Number(qty) > 0)}>
        Hinzufügen
      </Button>
    </Stack>
  );
}

function TareForm({ product, variant, onDone }: { product: Product; variant: Variant; onDone: () => void }) {
  const qc = useQueryClient();
  const [tare, setTare] = useState<string | number>(variant.tare_weight ?? '');
  const mutation = useMutation({
    mutationFn: () =>
      api.patch(`/products/${product.id}/variants/${variant.id}`, { tare_weight: tare === '' ? null : Number(tare) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['product', product.id] });
      onDone();
    },
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });
  return (
    <Stack>
      <Text size="sm">
        Leergewicht der Verpackung „{variantLabel(variant)}“. Es wird beim Wiegen der Restmenge vom abgelesenen
        Gewicht abgezogen.
      </Text>
      <NumberInput label="Leergewicht (g)" placeholder="kein Abzug" decimalSeparator="," min={0} value={tare} onChange={setTare} data-autofocus />
      <Button onClick={() => mutation.mutate()} loading={mutation.isPending}>
        Speichern
      </Button>
    </Stack>
  );
}

export function ProductDetailPage() {
  const { id } = useParams();
  const user = useUser();
  const isAdmin = user.role === 'admin';
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: product, isLoading } = useProduct(id);
  const { data: stock } = useStock({ product_id: id, sort: 'expiry' }, { keepPrevious: false });
  const { data: locations = [] } = useLocations();
  const [editOpen, edit] = useDisclosure();
  const [variantOpen, variantModal] = useDisclosure();
  const [transferItem, setTransferItem] = useState<StockItem | null>(null);
  const [tareVariant, setTareVariant] = useState<Variant | null>(null);

  const refresh = (p?: Product) => {
    if (p) qc.setQueryData(['product', p.id], p);
    qc.invalidateQueries({ queryKey: ['product', id] });
    qc.invalidateQueries({ queryKey: ['products'] });
  };

  const upload = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append('file', file);
      return api.put<Product>(`/products/${id}/image`, form);
    },
    onSuccess: refresh,
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });
  const variantAction = useMutation({
    mutationFn: ({ v, action }: { v: Variant; action: 'default' | 'remove' }) =>
      action === 'default'
        ? api.patch(`/products/${id}/variants/${v.id}`, { is_default: true })
        : api.delete(`/products/${id}/variants/${v.id}`),
    onSuccess: () => refresh(),
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });
  const toggleActive = useMutation({
    mutationFn: () => api.patch<Product>(`/products/${id}`, { active: !product?.active }),
    onSuccess: refresh,
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });
  const remove = useMutation({
    mutationFn: () => api.delete(`/products/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] });
      navigate('/lebensmittel');
    },
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });

  if (isLoading || !product) return <Loader mx="auto" />;
  const locationName = locations.find((l) => l.id === product.default_location_id)?.path;
  const u = unitShort(product.base_unit);

  return (
    <Stack>
      <Group wrap="nowrap" align="flex-start">
        <ProductAvatar product={product} size={88} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <Title order={2}>{product.name}</Title>
          <Text c="dimmed">{[product.brand, product.category_name].filter(Boolean).join(' · ')}</Text>
          <Group gap="xs" mt={4}>
            <Badge size="lg">{formatQuantity(product.stock_quantity, product.base_unit)}</Badge>
            {!product.active && <Badge color="gray">deaktiviert</Badge>}
          </Group>
        </div>
      </Group>

      <Group>
        <Button leftSection={<IconPackageImport size={18} />} onClick={() => navigate('/einlagern', { state: { product } })} disabled={!product.active}>
          Einlagern
        </Button>
        <Button
          variant="light"
          leftSection={<IconPackageExport size={18} />}
          onClick={() => navigate('/entnehmen', { state: { product } })}
          disabled={product.stock_quantity <= 0}
        >
          Entnehmen
        </Button>
        <FileButton onChange={(f) => f && upload.mutate(f)} accept="image/*" capture="environment">
          {(props) => (
            <Button variant="default" leftSection={<IconCamera size={18} />} loading={upload.isPending} {...props}>
              Foto
            </Button>
          )}
        </FileButton>
        {isAdmin && (
          <Button variant="default" leftSection={<IconEdit size={18} />} onClick={edit.open}>
            Bearbeiten
          </Button>
        )}
      </Group>

      <Card withBorder>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xs">
          <Text size="sm">Basiseinheit: <b>{u}</b></Text>
          <Text size="sm">Standardlagerplatz: <b>{locationName ?? '–'}</b></Text>
          <Text size="sm">Mindestbestand: <b>{product.minimum_stock != null ? `${formatNumber(product.minimum_stock)} ${u}` : 'keine Überwachung'}</b></Text>
          <Text size="sm">Zielbestand: <b>{product.target_stock != null ? `${formatNumber(product.target_stock)} ${u}` : '–'}</b></Text>
          <Text size="sm">Standardhaltbarkeit: <b>{product.default_shelf_life_days != null ? `${product.default_shelf_life_days} Tage` : '–'}</b></Text>
          <Text size="sm">Restmenge per Waage: <b>{product.weigh_remaining ? 'ja' : 'nein'}</b></Text>
          <Text size="sm">Warnfrist: <b>{product.expiry_warning_days != null ? `${product.expiry_warning_days} Tage` : 'Standard'}</b></Text>
        </SimpleGrid>
        {product.notes && <Text size="sm" mt="xs">{product.notes}</Text>}
      </Card>

      <Group justify="space-between">
        <Title order={4}>Verpackungen &amp; Barcodes</Title>
        <Button size="xs" variant="light" leftSection={<IconPlus size={16} />} onClick={variantModal.open}>
          Hinzufügen
        </Button>
      </Group>
      <Table.ScrollContainer minWidth={420}>
        <Table>
          <Table.Tbody>
            {product.variants.map((v) => (
              <Table.Tr key={v.id}>
                <Table.Td>
                  {variantLabel(v)} {v.is_default && <Badge size="xs" ml={4}>Standard</Badge>}
                  {product.base_unit === 'g' && (
                    <Text size="xs" c="dimmed">
                      Leergewicht: {v.tare_weight != null ? `${formatNumber(v.tare_weight)} g` : '–'}
                    </Text>
                  )}
                </Table.Td>
                <Table.Td><Text size="sm" ff="monospace">{v.barcode ?? '–'}</Text></Table.Td>
                <Table.Td align="right">
                  {isAdmin && (
                    <Group gap={4} justify="flex-end" wrap="nowrap">
                      {product.base_unit === 'g' && (
                        <ActionIcon variant="subtle" onClick={() => setTareVariant(v)} aria-label="Leergewicht bearbeiten">
                          <IconScale size={18} />
                        </ActionIcon>
                      )}
                      {!v.is_default && (
                        <ActionIcon variant="subtle" onClick={() => variantAction.mutate({ v, action: 'default' })} aria-label="Als Standard festlegen">
                          <IconStar size={18} />
                        </ActionIcon>
                      )}
                      <ActionIcon variant="subtle" color="red" onClick={() => variantAction.mutate({ v, action: 'remove' })} aria-label="Entfernen">
                        <IconTrash size={18} />
                      </ActionIcon>
                    </Group>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
            {product.variants.length === 0 && (
              <Table.Tr>
                <Table.Td c="dimmed">Keine Verpackungen hinterlegt.</Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>

      <Title order={4}>Bestandspositionen</Title>
      <Table.ScrollContainer minWidth={420}>
        <Table striped>
          <Table.Tbody>
            {stock?.items.map((i) => (
              <Table.Tr key={i.id}>
                <Table.Td>{i.location_path}</Table.Td>
                <Table.Td><ExpiryText item={i} /></Table.Td>
                <Table.Td align="right">{formatQuantity(i.quantity, i.base_unit)}</Table.Td>
                <Table.Td align="right" w={40}>
                  <ActionIcon variant="subtle" onClick={() => setTransferItem(i)} aria-label="Umlagern">
                    <IconArrowsTransferUp size={18} />
                  </ActionIcon>
                </Table.Td>
              </Table.Tr>
            ))}
            {stock?.total === 0 && (
              <Table.Tr>
                <Table.Td c="dimmed">Kein Bestand vorhanden.</Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>

      {isAdmin && (
        <Group mt="md">
          <Button variant="default" onClick={() => toggleActive.mutate()} loading={toggleActive.isPending}>
            {product.active ? 'Deaktivieren' : 'Wieder aktivieren'}
          </Button>
          <Button color="red" variant="subtle" onClick={() => remove.mutate()} loading={remove.isPending}>
            Löschen
          </Button>
        </Group>
      )}
      {product.image_source && (
        <Text size="xs" c="dimmed">
          Bildquelle: {product.image_source}
        </Text>
      )}

      <TransferDialog item={transferItem} onClose={() => setTransferItem(null)} />
      <Modal opened={editOpen} onClose={edit.close} title="Lebensmittel bearbeiten" size="lg">
        <ProductForm product={product} onCancel={edit.close} onSaved={() => edit.close()} />
      </Modal>
      <Modal opened={tareVariant !== null} onClose={() => setTareVariant(null)} title="Leergewicht">
        {tareVariant && <TareForm product={product} variant={tareVariant} onDone={() => setTareVariant(null)} />}
      </Modal>
      <Modal opened={variantOpen} onClose={variantModal.close} title="Verpackung hinzufügen">
        <VariantForm product={product} onDone={variantModal.close} />
      </Modal>
    </Stack>
  );
}
