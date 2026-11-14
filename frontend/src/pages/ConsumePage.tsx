import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActionIcon,
  Alert,
  Button,
  Card,
  Chip,
  Group,
  NumberInput,
  SegmentedControl,
  Select,
  Stack,
  Text,
  Title,
  UnstyledButton,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconArrowLeft, IconCheck, IconScale, IconTrash } from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';
import { useLocation as useRouterLocation } from 'react-router-dom';
import { useBooking } from '../api/booking';
import { api, errorMessage } from '../api/client';
import { useStock } from '../api/hooks';
import type { BookingResult, ConsumptionPlan, Product, StockItem, WeighingPreview } from '../api/types';
import { ExpiryText } from '../components/ExpiryText';
import { ProductAvatar } from '../components/ProductAvatar';
import { ProductSearch } from '../components/ProductSearch';
import { DISPOSAL_REASONS, formatNumber, formatQuantity, isExpired, unitShort, variantLabel } from '../lib/format';
import classes from './ConsumePage.module.css';

type Mode = 'consume' | 'dispose';
const AUTO = 'auto';
const BASE = '__base__';

function PositionCard({
  item,
  selected,
  onSelect,
  planned,
}: {
  item: StockItem;
  selected: boolean;
  onSelect: () => void;
  planned?: number;
}) {
  return (
    <UnstyledButton onClick={onSelect} className={classes.option} data-selected={selected || undefined}>
      <Group justify="space-between" wrap="nowrap" gap="xs">
        <div style={{ minWidth: 0 }}>
          <Text size="sm" fw={500} truncate>
            {item.location_path}
          </Text>
          <ExpiryText item={item} />
        </div>
        <Stack gap={0} align="flex-end">
          <Text size="sm">{formatQuantity(item.quantity, item.base_unit)}</Text>
          {planned !== undefined && (
            <Text size="xs" c="green" fw={600}>
              − {formatQuantity(planned, item.base_unit)}
            </Text>
          )}
        </Stack>
      </Group>
    </UnstyledButton>
  );
}

function ProductHeader({ product, onBack }: { product: Product; onBack: () => void }) {
  return (
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
  );
}

/** Angebrochene Packung erkennen: Menge ist kein Vielfaches der Packungsgröße. */
function looksOpened(item: StockItem, product: Product): boolean {
  const v = product.variants.find((x) => x.id === item.variant_id);
  if (!v) return true;
  return Math.abs(item.quantity / v.base_quantity - Math.round(item.quantity / v.base_quantity)) > 1e-6;
}

/** Restmenge per Waage: Differenz zum erwarteten Inhalt wird als Verbrauch gebucht (DEC-029). */
function WeighForm({ product, onDone }: { product: Product; onDone: (r: BookingResult) => void }) {
  const { data: stock } = useStock({ product_id: product.id, sort: 'expiry' }, { keepPrevious: false });
  const items = useMemo(() => stock?.items ?? [], [stock]);
  const [source, setSource] = useState('');
  const [measured, setMeasured] = useState<string | number>('');

  // Standard: die angebrochene Position, sonst die mit der kürzesten Haltbarkeit
  useEffect(() => {
    if (items.length && !items.some((i) => i.id === source)) {
      setSource((items.find((i) => looksOpened(i, product)) ?? items[0]).id);
    }
  }, [items, source, product]);

  const item = items.find((i) => i.id === source);
  const variant = product.variants.find((v) => v.id === item?.variant_id);
  const value = Number(measured);
  const [debounced] = useDebouncedValue(value, 300);
  const preview = useQuery({
    queryKey: ['weighing-preview', source, item?.version, debounced],
    queryFn: () =>
      api.get<WeighingPreview>('/stock/weighing-preview', { stock_item_id: source, measured_weight: debounced }),
    enabled: !!item && debounced > 0,
    retry: false,
  });
  const ready = preview.data && debounced === value;
  const booking = useBooking('/stock/weighings', onDone);

  if (items.length === 0) return <Alert color="yellow">Von diesem Produkt ist kein Bestand vorhanden.</Alert>;
  return (
    <Stack>
      <Text size="sm" fw={500}>
        Gewogene Packung gehört zu
      </Text>
      <Stack gap={6}>
        {items.map((i) => (
          <PositionCard key={i.id} item={i} selected={source === i.id} onSelect={() => setSource(i.id)} />
        ))}
      </Stack>
      <NumberInput
        label="Abgelesenes Gewicht (g)"
        description={
          variant?.tare_weight
            ? `Inklusive Verpackung – das Leergewicht von ${formatNumber(variant.tare_weight)} g wird abgezogen.`
            : 'Nur die angebrochene Packung wiegen. Kein Leergewicht hinterlegt – Verpackung ggf. vorher tarieren.'
        }
        min={0}
        decimalScale={1}
        decimalSeparator=","
        thousandSeparator="."
        inputMode="decimal"
        value={measured}
        onChange={setMeasured}
        size="lg"
        data-autofocus
      />
      {ready && (
        <Card withBorder padding="sm">
          <Text size="sm">
            Erwartet in der angebrochenen Packung: <b>{formatQuantity(preview.data!.open_before, 'g')}</b>
            {preview.data!.full_packages > 0 && ` (zusätzlich ${preview.data!.full_packages} volle Packung${preview.data!.full_packages > 1 ? 'en' : ''})`}
          </Text>
          <Text size="sm">
            Tatsächlich vorhanden: <b>{formatQuantity(preview.data!.net, 'g')}</b>
          </Text>
          <Text size="sm" fw={600} c="green">
            Verbrauch: {formatQuantity(preview.data!.consumption, 'g')} · Neuer Bestand der Position:{' '}
            {formatQuantity(preview.data!.remaining_total, 'g')}
          </Text>
        </Card>
      )}
      {preview.error && debounced === value && <Alert color="red">{errorMessage(preview.error)}</Alert>}
      <Button
        size="xl"
        leftSection={<IconScale />}
        disabled={!ready || preview.data!.consumption <= 0}
        loading={booking.isPending || preview.isFetching}
        onClick={() =>
          booking.mutate({ stock_item_id: source, measured_weight: value, expected_version: item!.version })
        }
      >
        {ready && preview.data!.consumption > 0
          ? `${formatQuantity(preview.data!.consumption, 'g')} als Verbrauch buchen`
          : 'Verbrauch buchen'}
      </Button>
    </Stack>
  );
}

/** Buchungsmaske für Verbrauch bzw. Entsorgung eines Produkts (FR-CNS-001…008). */
function TakeForm({
  product,
  mode,
  onDone,
}: {
  product: Product;
  mode: Mode;
  onDone: (r: BookingResult) => void;
}) {
  const variants = product.variants.filter((v) => v.active);
  const defaultVariant = variants.find((v) => v.is_default);
  const [variantId, setVariantId] = useState<string>(defaultVariant?.id ?? BASE);
  const variant = variants.find((v) => v.id === variantId);
  const [quantity, setQuantity] = useState<string | number>(
    defaultVariant || product.base_unit === 'piece' ? 1 : '',
  );
  const [reason, setReason] = useState('expired');
  const { data: stock } = useStock({ product_id: product.id, sort: 'expiry' }, { keepPrevious: false });
  const items = useMemo(() => stock?.items ?? [], [stock]);
  const [source, setSource] = useState<string>(mode === 'consume' ? AUTO : '');

  // Entsorgung: standardmäßig die erste abgelaufene bzw. älteste Position
  useEffect(() => {
    if (mode === 'dispose' && items.length && !items.some((i) => i.id === source)) {
      const first = items.find((i) => isExpired(i)) ?? items[0];
      setSource(first.id);
      setVariantId(BASE);
      setQuantity(first.quantity);
    }
  }, [mode, source, items]);

  const baseQty = (Number(quantity) || 0) * (variant ? variant.base_quantity : 1);
  const [debouncedQty] = useDebouncedValue(baseQty, 300);
  const selectedItem = items.find((i) => i.id === source);

  const plan = useQuery({
    queryKey: ['consumption-plan', product.id, debouncedQty],
    queryFn: () =>
      api.get<ConsumptionPlan>('/stock/consumption-plan', { product_id: product.id, quantity: debouncedQty }),
    enabled: mode === 'consume' && source === AUTO && debouncedQty > 0,
  });
  const planReady = plan.data && debouncedQty === baseQty;
  const plannedById = new Map(
    source === AUTO && planReady ? plan.data!.allocations.map((a) => [a.stock_item.id, a.quantity]) : [],
  );

  const booking = useBooking(mode === 'consume' ? '/stock/consumptions' : '/stock/disposals', onDone);

  let allocations: { stock_item_id: string; quantity: number; expected_version: number }[] = [];
  let problem: string | null = null;
  if (source === AUTO) {
    if (planReady && plan.data!.sufficient) {
      allocations = plan.data!.allocations.map((a) => ({
        stock_item_id: a.stock_item.id,
        quantity: a.quantity,
        expected_version: a.stock_item.version,
      }));
    } else if (planReady) {
      problem = `Nur ${formatQuantity(plan.data!.available, product.base_unit)} verfügbar.`;
    }
  } else if (selectedItem && baseQty > 0) {
    if (baseQty > selectedItem.quantity) {
      problem = `An dieser Position sind nur ${formatQuantity(selectedItem.quantity, product.base_unit)} vorhanden.`;
    } else {
      allocations = [{ stock_item_id: selectedItem.id, quantity: baseQty, expected_version: selectedItem.version }];
    }
  }

  const submit = () =>
    booking.mutate(
      mode === 'consume'
        ? { product_id: product.id, allocations }
        : { product_id: product.id, allocations, reason },
    );

  return (
    <Stack>

      {items.length === 0 ? (
        <Alert color="yellow">Von diesem Produkt ist kein Bestand vorhanden.</Alert>
      ) : (
        <>
          <Text size="sm" fw={500}>
            {mode === 'consume' ? 'Entnehmen aus' : 'Position'}
          </Text>
          <Stack gap={6}>
            {mode === 'consume' && (
              <UnstyledButton
                onClick={() => setSource(AUTO)}
                className={classes.option}
                data-selected={source === AUTO || undefined}
              >
                <Text size="sm" fw={500}>
                  Automatisch – kürzeste Haltbarkeit zuerst
                </Text>
              </UnstyledButton>
            )}
            {items.map((i) => (
              <PositionCard
                key={i.id}
                item={i}
                selected={source === i.id}
                planned={plannedById.get(i.id)}
                onSelect={() => setSource(i.id)}
              />
            ))}
          </Stack>

          <Group align="flex-end" wrap="nowrap">
            <NumberInput
              style={{ flex: 1 }}
              label={variant ? 'Anzahl Packungen' : `Menge (${unitShort(product.base_unit)})`}
              min={0}
              decimalScale={3}
              decimalSeparator=","
              thousandSeparator="."
              inputMode="decimal"
              value={quantity}
              onChange={setQuantity}
            />
            {variants.length > 0 && (
              <Select
                w={150}
                data={[
                  ...variants.map((v) => ({ value: v.id, label: variantLabel(v) })),
                  { value: BASE, label: unitShort(product.base_unit) },
                ]}
                value={variantId}
                onChange={(v) => v && setVariantId(v)}
                allowDeselect={false}
                aria-label="Einheit"
              />
            )}
            {selectedItem && (
              <Button
                variant="default"
                onClick={() => {
                  setVariantId(BASE);
                  setQuantity(selectedItem.quantity);
                }}
              >
                Alles
              </Button>
            )}
          </Group>

          {mode === 'dispose' && (
            <Chip.Group value={reason} onChange={(v) => setReason(v as string)}>
              <Group gap="xs">
                {Object.entries(DISPOSAL_REASONS).map(([value, label]) => (
                  <Chip key={value} value={value}>
                    {label}
                  </Chip>
                ))}
              </Group>
            </Chip.Group>
          )}

          {problem && <Alert color="red">{problem}</Alert>}

          <Button
            size="xl"
            color={mode === 'dispose' ? 'red' : undefined}
            leftSection={mode === 'dispose' ? <IconTrash /> : <IconCheck />}
            disabled={allocations.length === 0 || !!problem}
            loading={booking.isPending || (source === AUTO && plan.isFetching)}
            onClick={submit}
          >
            {baseQty > 0
              ? `${formatQuantity(baseQty, product.base_unit)} ${mode === 'consume' ? 'entnehmen' : 'entsorgen'}`
              : mode === 'consume'
                ? 'Entnehmen'
                : 'Entsorgen'}
          </Button>
        </>
      )}
    </Stack>
  );
}

/** Entnehmen – optimiert für das Smartphone (Spezifikation 9.5). */
export function ConsumePage() {
  const routerLocation = useRouterLocation();
  const preselected = (routerLocation.state as { product?: Product } | null)?.product ?? null;
  const [mode, setMode] = useState<Mode>('consume');
  const [product, setProduct] = useState<Product | null>(preselected);
  const [last, setLast] = useState<{ r: BookingResult; mode: Mode } | null>(null);
  const [entry, setEntry] = useState<'weigh' | 'quantity'>('weigh');
  const recent = useQuery({
    queryKey: ['recent-products'],
    queryFn: () => api.get<Product[]>('/stock/recent-products'),
  });
  const select = useCallback((p: Product) => setProduct(p), []);

  return (
    <Stack maw={560} mx="auto">
      <Title order={2}>{mode === 'consume' ? 'Entnehmen' : 'Entsorgen'}</Title>
      <SegmentedControl
        value={mode}
        onChange={(v) => setMode(v as Mode)}
        data={[
          { value: 'consume', label: 'Verbrauch' },
          { value: 'dispose', label: 'Entsorgung' },
        ]}
      />
      {last && !product && (
        <Alert color="green" icon={<IconCheck />} withCloseButton onClose={() => setLast(null)}>
          {formatQuantity(last.r.quantity, last.r.product.base_unit)} {last.r.product.name}{' '}
          {last.mode === 'consume' ? 'entnommen' : 'entsorgt'}. Neuer Bestand:{' '}
          {formatQuantity(last.r.product.stock_quantity, last.r.product.base_unit)}
        </Alert>
      )}
      {product && (
        <ProductHeader product={product} onBack={() => setProduct(null)} />
      )}
      {product && mode === 'consume' && product.weigh_remaining && (
        <SegmentedControl
          value={entry}
          onChange={(v) => setEntry(v as 'weigh' | 'quantity')}
          data={[
            { value: 'weigh', label: 'Restgewicht wiegen' },
            { value: 'quantity', label: 'Menge eingeben' },
          ]}
        />
      )}
      {product && mode === 'consume' && product.weigh_remaining && entry === 'weigh' ? (
        <WeighForm
          key={product.id}
          product={product}
          onDone={(r) => {
            setLast({ r, mode });
            setProduct(null);
          }}
        />
      ) : product ? (
        <TakeForm
          key={`${product.id}-${mode}`}
          product={product}
          mode={mode}
          onDone={(r) => {
            setLast({ r, mode });
            setProduct(null);
          }}
        />
      ) : (
        <>
          {mode === 'consume' && !!recent.data?.length && (
            <Card withBorder padding="sm">
              <Text size="sm" c="dimmed" mb={6}>
                Zuletzt entnommen
              </Text>
              <Group gap="xs">
                {recent.data.map((p) => (
                  <Button key={p.id} variant="light" size="sm" onClick={() => select(p)}>
                    {p.name}
                  </Button>
                ))}
              </Group>
            </Card>
          )}
          <ProductSearch autoFocus onSelect={select} />
        </>
      )}
    </Stack>
  );
}
