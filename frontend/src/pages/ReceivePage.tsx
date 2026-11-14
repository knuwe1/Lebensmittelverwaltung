import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActionIcon,
  Alert,
  Button,
  Card,
  Group,
  NumberInput,
  Paper,
  SegmentedControl,
  Select,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconArrowLeft, IconCheck, IconPlus, IconTrash } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocation as useRouterLocation } from 'react-router-dom';
import { api, errorMessage, newIdempotencyKey } from '../api/client';
import type { ExpiryType, Product, ReceiptDefaults, ReceiptResult } from '../api/types';
import { GermanDateInput } from '../components/GermanDateInput';
import { ProductAvatar } from '../components/ProductAvatar';
import { ProductForm } from '../components/ProductForm';
import { ProductSearch } from '../components/ProductSearch';
import { LocationSelect } from '../components/selects';
import {
  EXPIRY_TYPE_LABELS,
  formatQuantity,
  fromIsoDate,
  toIsoDate,
  unitShort,
  variantLabel,
} from '../lib/format';

interface Line {
  key: number;
  quantity: string | number;
  expiryType: ExpiryType;
  expiryDate: Date | null;
}

const BASE = '__base__';
let lineCounter = 0;
const newLine = (expiryType: ExpiryType = 'best_before', expiryDate: Date | null = null): Line => ({
  key: ++lineCounter,
  quantity: 1,
  expiryType,
  expiryDate,
});

/** Buchungsmaske für ein identifiziertes Produkt (FR-STK-001…004). */
function ReceiptForm({
  product,
  initialVariantId,
  onDone,
  onBack,
}: {
  product: Product;
  initialVariantId?: string;
  onDone: (r: ReceiptResult) => void;
  onBack: () => void;
}) {
  const qc = useQueryClient();
  const variants = product.variants.filter((v) => v.active);
  const [variantId, setVariantId] = useState<string>(initialVariantId ?? BASE);
  const [locationId, setLocationId] = useState<string | null>(null);
  const [lines, setLines] = useState<Line[]>([newLine()]);
  // Ein Schlüssel je Buchungsvorgang; bleibt bei Fehlern gleich, damit ein erneutes
  // Absenden nicht doppelt bucht (DEC-025).
  const idempotencyKey = useRef(newIdempotencyKey());

  const defaults = useQuery({
    queryKey: ['receipt-defaults', product.id],
    queryFn: () => api.get<ReceiptDefaults>('/stock/receipt-defaults', { product_id: product.id }),
    staleTime: Infinity,
    refetchOnWindowFocus: false,
  });
  // Vorschläge genau einmal übernehmen – nie bereits getätigte Eingaben überschreiben
  // (z. B. wenn die Antwort erst nach dem Tippen eintrifft).
  const defaultsApplied = useRef(false);
  const edited = useRef(false);
  useEffect(() => {
    const d = defaults.data;
    if (!d || defaultsApplied.current) return;
    defaultsApplied.current = true;
    setLocationId((cur) => cur ?? d.location_id);
    if (edited.current) return;
    if (!initialVariantId) setVariantId(d.variant_id ?? BASE);
    setLines([newLine(d.expiry_type, fromIsoDate(d.expiry_date))]);
  }, [defaults.data, initialVariantId]);

  const variant = variants.find((v) => v.id === variantId);
  const usePackages = !!variant;
  const total = lines.reduce(
    (sum, l) => sum + (Number(l.quantity) || 0) * (variant ? variant.base_quantity : 1),
    0,
  );
  const needsDate = (l: Line) => l.expiryType === 'best_before' || l.expiryType === 'use_by';
  const valid =
    !!locationId && lines.every((l) => Number(l.quantity) > 0 && (!needsDate(l) || l.expiryDate));

  const mutation = useMutation({
    mutationFn: () =>
      api.post<ReceiptResult>(
        '/stock/receipts',
        {
          product_id: product.id,
          variant_id: variant?.id ?? null,
          location_id: locationId,
          lines: lines.map((l) => ({
            quantity: Number(l.quantity),
            unit: usePackages ? 'package' : 'base',
            expiry_type: l.expiryType,
            expiry_date: needsDate(l) && l.expiryDate ? toIsoDate(l.expiryDate) : null,
          })),
        },
        { idempotencyKey: idempotencyKey.current },
      ),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['stock'] });
      qc.invalidateQueries({ queryKey: ['products'] });
      qc.setQueryData(['product', r.product.id], r.product);
      onDone(r);
    },
    onError: (e) => notifications.show({ color: 'red', title: 'Nicht gebucht', message: errorMessage(e) }),
  });

  const update = (key: number, patch: Partial<Line>) => {
    edited.current = true;
    setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)));
  };

  return (
    <Stack>
      <Group wrap="nowrap">
        <ActionIcon variant="subtle" size="lg" onClick={onBack} aria-label="Anderes Produkt wählen">
          <IconArrowLeft />
        </ActionIcon>
        <ProductAvatar product={product} size={56} />
        <div style={{ minWidth: 0 }}>
          <Text fw={700} size="lg" truncate>
            {product.name}
          </Text>
          <Text size="sm" c="dimmed">
            Bestand: {formatQuantity(product.stock_quantity, product.base_unit)}
          </Text>
        </div>
      </Group>

      <Select
        label="Verpackung"
        data={[
          ...variants.map((v) => ({ value: v.id, label: variantLabel(v) })),
          { value: BASE, label: `Menge in ${unitShort(product.base_unit)}` },
        ]}
        value={variantId}
        onChange={(v) => {
          if (!v) return;
          edited.current = true;
          setVariantId(v);
        }}
        allowDeselect={false}
      />

      {lines.map((line, i) => (
        <Paper key={line.key} withBorder p="sm">
          <Stack gap="xs">
            <Group align="flex-end" wrap="nowrap">
              <NumberInput
                style={{ flex: 1 }}
                label={usePackages ? 'Anzahl Packungen' : `Menge (${unitShort(product.base_unit)})`}
                min={0}
                decimalScale={3}
                decimalSeparator=","
                thousandSeparator="."
                inputMode="decimal"
                value={line.quantity}
                onChange={(v) => update(line.key, { quantity: v })}
              />
              {lines.length > 1 && (
                <ActionIcon
                  color="red"
                  variant="subtle"
                  size="xl"
                  onClick={() => setLines((ls) => ls.filter((l) => l.key !== line.key))}
                  aria-label={`Zeile ${i + 1} entfernen`}
                >
                  <IconTrash />
                </ActionIcon>
              )}
            </Group>
            <SegmentedControl
              fullWidth
              size="xs"
              value={line.expiryType}
              onChange={(v) => update(line.key, { expiryType: v as ExpiryType })}
              data={[
                { value: 'best_before', label: 'MHD' },
                { value: 'use_by', label: 'Verbrauch' },
                { value: 'none', label: 'Kein' },
                { value: 'unknown', label: 'Unbekannt' },
              ]}
            />
            {needsDate(line) && (
              <GermanDateInput
                label={EXPIRY_TYPE_LABELS[line.expiryType]}
                value={line.expiryDate}
                onChange={(d) => update(line.key, { expiryDate: d })}
                size="md"
              />
            )}
          </Stack>
        </Paper>
      ))}
      <Button
        variant="subtle"
        leftSection={<IconPlus size={18} />}
        onClick={() => {
          edited.current = true;
          setLines((ls) => [...ls, newLine(ls[ls.length - 1].expiryType)]);
        }}
      >
        Weiteres Haltbarkeitsdatum
      </Button>

      <LocationSelect value={locationId} onChange={setLocationId} size="md" required />

      <Button size="xl" leftSection={<IconCheck />} onClick={() => mutation.mutate()} loading={mutation.isPending} disabled={!valid}>
        {total > 0 ? `${formatQuantity(total, product.base_unit)} einlagern` : 'Einlagern'}
      </Button>
    </Stack>
  );
}

type Step =
  | { kind: 'search' }
  | { kind: 'create'; name?: string; barcode?: string }
  | { kind: 'book'; product: Product; variantId?: string };

/** Einlagern – optimiert für das Smartphone (Spezifikation 9.4, DEC-026). */
export function ReceivePage() {
  const routerLocation = useRouterLocation();
  const preselected = (routerLocation.state as { product?: Product } | null)?.product;
  const [step, setStep] = useState<Step>(preselected ? { kind: 'book', product: preselected } : { kind: 'search' });
  const [last, setLast] = useState<ReceiptResult | null>(null);

  const select = useCallback((product: Product, variantId?: string) => {
    setStep({ kind: 'book', product, variantId });
  }, []);

  return (
    <Stack maw={560} mx="auto">
      <Title order={2}>Einlagern</Title>
      {last && step.kind === 'search' && (
        <Alert color="green" icon={<IconCheck />} withCloseButton onClose={() => setLast(null)}>
          {formatQuantity(last.received_quantity, last.product.base_unit)} {last.product.name} eingelagert. Neuer
          Bestand: {formatQuantity(last.product.stock_quantity, last.product.base_unit)}
        </Alert>
      )}
      {step.kind === 'search' && (
        <ProductSearch autoFocus onSelect={select} onCreate={(prefill) => setStep({ kind: 'create', ...prefill })} />
      )}
      {step.kind === 'create' && (
        <Card withBorder>
          <Title order={4} mb="sm">
            Neues Lebensmittel
          </Title>
          <ProductForm
            compact
            initialName={step.name}
            initialBarcode={step.barcode}
            onSaved={(p) => select(p, p.variants.find((v) => v.is_default)?.id)}
            onCancel={() => setStep({ kind: 'search' })}
          />
        </Card>
      )}
      {step.kind === 'book' && (
        <ReceiptForm
          key={step.product.id}
          product={step.product}
          initialVariantId={step.variantId}
          onBack={() => setStep({ kind: 'search' })}
          onDone={(r) => {
            setLast(r);
            setStep({ kind: 'search' });
          }}
        />
      )}
    </Stack>
  );
}
