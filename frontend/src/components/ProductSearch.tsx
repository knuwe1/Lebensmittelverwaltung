import { useCallback, useEffect, useState } from 'react';
import {
  ActionIcon,
  Alert,
  Anchor,
  Button,
  Card,
  Group,
  Image,
  Loader,
  Stack,
  Text,
  TextInput,
  UnstyledButton,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconBarcode, IconPlus, IconScan, IconSearch } from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';
import { api, ApiError } from '../api/client';
import { useHouseholdSettings, useProducts } from '../api/hooks';
import type { BarcodeLookup, Product, ProductPrefill, ProductSuggestion } from '../api/types';
import { formatNumber, formatQuantity, PACKAGE_UNIT_LABELS } from '../lib/format';
import { BarcodeScanner } from './BarcodeScanner';
import { ProductAvatar } from './ProductAvatar';

const BARCODE = /^\d{8,14}$/;

interface Props {
  onSelect: (product: Product, variantId?: string) => void;
  /** Neues Produkt anlegen – mit vorbelegtem Namen, Barcode bzw. externem Vorschlag */
  onCreate?: (prefill: ProductPrefill) => void;
  autoFocus?: boolean;
}

/** Vorschlag aus einer externen Produktdatenbank – muss vor der Übernahme geprüft werden. */
function ExternalSuggestion({
  barcode,
  onCreate,
}: {
  barcode: string;
  onCreate?: (prefill: ProductPrefill) => void;
}) {
  const settings = useHouseholdSettings();
  const enabled = !!settings.data?.external_product_data;
  const suggestion = useQuery({
    queryKey: ['product-data', barcode],
    queryFn: () => api.get<ProductSuggestion>(`/product-data/barcode/${barcode}`),
    enabled,
    retry: false,
    staleTime: Infinity,
  });

  const manual = onCreate && (
    <Button variant={suggestion.data ? 'default' : 'filled'} leftSection={<IconPlus size={18} />} onClick={() => onCreate({ barcode })}>
      Manuell anlegen
    </Button>
  );

  if (!enabled) {
    return (
      <Alert color="yellow" title="Barcode unbekannt">
        <Stack gap="xs">
          <Text size="sm">Der Barcode {barcode} ist noch keinem Lebensmittel zugeordnet.</Text>
          {manual}
        </Stack>
      </Alert>
    );
  }
  if (suggestion.isLoading) {
    return (
      <Group gap="xs">
        <Loader size="sm" />
        <Text size="sm">Suche bei Open Food Facts …</Text>
      </Group>
    );
  }
  const s = suggestion.data;
  if (!s) {
    const err = suggestion.error instanceof ApiError ? suggestion.error : null;
    return (
      <Alert color="yellow" title="Barcode unbekannt">
        <Stack gap="xs">
          <Text size="sm">
            Der Barcode {barcode} ist noch keinem Lebensmittel zugeordnet.{' '}
            {err?.message ?? 'Keine externen Produktdaten verfügbar.'}
          </Text>
          {manual}
        </Stack>
      </Alert>
    );
  }
  return (
    <Card withBorder>
      <Text size="xs" c="dimmed" mb={6}>
        Unbekannter Barcode – Vorschlag von{' '}
        <Anchor href={s.source_url} target="_blank" rel="noreferrer" size="xs">
          {s.source}
        </Anchor>{' '}
        ({s.license})
      </Text>
      <Group wrap="nowrap" align="flex-start">
        {s.image_url && (
          <Image
            src={`/api/v1/product-data/image?url=${encodeURIComponent(s.image_url)}`}
            w={64}
            h={64}
            fit="contain"
            radius="sm"
            alt=""
          />
        )}
        <div style={{ minWidth: 0 }}>
          <Text fw={600}>{s.name ?? 'Ohne Namen'}</Text>
          <Text size="sm" c="dimmed">
            {[
              s.brand,
              s.package_quantity ? `${formatNumber(Number(s.package_quantity))} ${PACKAGE_UNIT_LABELS[s.package_unit ?? ''] ?? ''}` : null,
            ]
              .filter(Boolean)
              .join(' · ')}
          </Text>
        </div>
      </Group>
      {onCreate && (
        <Stack gap="xs" mt="sm">
          <Button leftSection={<IconPlus size={18} />} onClick={() => onCreate({ barcode, suggestion: s })}>
            Übernehmen und prüfen
          </Button>
          {manual}
        </Stack>
      )}
    </Card>
  );
}

/**
 * Produktidentifikation per Suche, Barcode-Eingabe oder Kamera-Scan
 * (FR-PRD-002, FR-PRD-003, FR-PRD-005).
 */
export function ProductSearch({ onSelect, onCreate, autoFocus }: Props) {
  const [input, setInput] = useState('');
  const [scanning, setScanning] = useState(false);
  const [debounced] = useDebouncedValue(input.trim(), 250);
  const term = debounced.replace(/\s/g, '');
  const isBarcode = BARCODE.test(term);

  const barcode = useQuery({
    queryKey: ['barcode', term],
    queryFn: () => api.get<BarcodeLookup>(`/products/barcode/${encodeURIComponent(term)}`),
    enabled: isBarcode,
    retry: false,
    // Treffer werden sofort übernommen – nie einen zwischengespeicherten (veralteten)
    // Bestand verwenden, z. B. beim erneuten Scannen nach einer Buchung.
    gcTime: 0,
    staleTime: 0,
  });
  const search = useProducts({ q: debounced, limit: 20 }, !isBarcode && debounced.length >= 1);

  // Eindeutiger Barcode-Treffer → Produkt direkt übernehmen
  useEffect(() => {
    if (barcode.data) {
      onSelect(barcode.data.product, barcode.data.variant_id);
      setInput('');
    }
  }, [barcode.data, onSelect]);

  const onScanned = useCallback((code: string) => {
    setScanning(false);
    setInput(code);
  }, []);

  const barcodeUnknown = isBarcode && barcode.error instanceof ApiError && barcode.error.code === 'barcode_unknown';
  const barcodeInvalid = isBarcode && barcode.error instanceof ApiError && !barcodeUnknown;
  const loading = barcode.isFetching || search.isFetching;

  return (
    <Stack gap="sm">
      <Group gap="xs" wrap="nowrap">
        <TextInput
          style={{ flex: 1 }}
          size="lg"
          placeholder="Produktname oder Barcode"
          leftSection={isBarcode ? <IconBarcode /> : <IconSearch />}
          rightSection={loading ? <Loader size="sm" /> : null}
          value={input}
          onChange={(e) => setInput(e.currentTarget.value)}
          autoFocus={autoFocus}
          autoComplete="off"
          enterKeyHint="search"
        />
        <ActionIcon size={50} radius="md" onClick={() => setScanning(true)} aria-label="Barcode scannen">
          <IconScan size={28} />
        </ActionIcon>
      </Group>
      <BarcodeScanner opened={scanning} onClose={() => setScanning(false)} onDetected={onScanned} />

      {barcodeUnknown && <ExternalSuggestion key={term} barcode={term} onCreate={onCreate} />}
      {barcodeInvalid && <Alert color="red">{(barcode.error as ApiError).message}</Alert>}

      {!isBarcode &&
        search.data?.items.map((p) => (
          <UnstyledButton key={p.id} onClick={() => onSelect(p)}>
            <Card withBorder padding="sm">
              <Group wrap="nowrap">
                <ProductAvatar product={p} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Text fw={600} truncate>
                    {p.name}
                  </Text>
                  <Text size="sm" c="dimmed" truncate>
                    {[p.brand, p.category_name].filter(Boolean).join(' · ')}
                  </Text>
                </div>
                <Text size="sm" c={p.stock_quantity > 0 ? undefined : 'dimmed'}>
                  {formatQuantity(p.stock_quantity, p.base_unit)}
                </Text>
              </Group>
            </Card>
          </UnstyledButton>
        ))}

      {!isBarcode && debounced && search.data?.total === 0 && (
        <Text c="dimmed" ta="center">
          Kein Lebensmittel gefunden.
        </Text>
      )}
      {onCreate && !isBarcode && debounced && (
        <Button variant="light" leftSection={<IconPlus size={18} />} onClick={() => onCreate({ name: debounced })}>
          „{debounced}“ als neues Lebensmittel anlegen
        </Button>
      )}
    </Stack>
  );
}
