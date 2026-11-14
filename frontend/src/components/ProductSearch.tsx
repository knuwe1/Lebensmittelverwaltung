import { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Group,
  Loader,
  Stack,
  Text,
  TextInput,
  UnstyledButton,
} from '@mantine/core';
import { useDebouncedValue } from '@mantine/hooks';
import { IconBarcode, IconPlus, IconSearch } from '@tabler/icons-react';
import { useQuery } from '@tanstack/react-query';
import { api, ApiError } from '../api/client';
import { useProducts } from '../api/hooks';
import type { BarcodeLookup, Product } from '../api/types';
import { formatQuantity } from '../lib/format';
import { ProductAvatar } from './ProductAvatar';

const BARCODE = /^\d{8,14}$/;

interface Props {
  onSelect: (product: Product, variantId?: string) => void;
  /** Neues Produkt anlegen – mit vorbelegtem Namen oder Barcode */
  onCreate?: (prefill: { name?: string; barcode?: string }) => void;
  autoFocus?: boolean;
}

/**
 * Produktidentifikation per Suche oder Barcode-Eingabe (FR-PRD-002, FR-PRD-005).
 * Kamera-Scan und Bilderkennung werden in Phase 4 hier ergänzt.
 */
export function ProductSearch({ onSelect, onCreate, autoFocus }: Props) {
  const [input, setInput] = useState('');
  const [debounced] = useDebouncedValue(input.trim(), 250);
  const isBarcode = BARCODE.test(debounced.replace(/\s/g, ''));

  const barcode = useQuery({
    queryKey: ['barcode', debounced],
    queryFn: () => api.get<BarcodeLookup>(`/products/barcode/${encodeURIComponent(debounced)}`),
    enabled: isBarcode,
    retry: false,
  });
  const search = useProducts({ q: debounced, limit: 20 }, !isBarcode && debounced.length >= 1);

  // Eindeutiger Barcode-Treffer → Produkt direkt übernehmen
  useEffect(() => {
    if (barcode.data) {
      onSelect(barcode.data.product, barcode.data.variant_id);
      setInput('');
    }
  }, [barcode.data, onSelect]);

  const barcodeUnknown =
    isBarcode && barcode.error instanceof ApiError && barcode.error.code === 'barcode_unknown';
  const barcodeInvalid = isBarcode && barcode.error instanceof ApiError && !barcodeUnknown;
  const loading = barcode.isFetching || search.isFetching;

  return (
    <Stack gap="sm">
      <TextInput
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

      {barcodeUnknown && (
        <Alert color="yellow" title="Barcode unbekannt">
          <Stack gap="xs">
            <Text size="sm">Der Barcode {debounced} ist noch keinem Lebensmittel zugeordnet.</Text>
            {onCreate && (
              <Button leftSection={<IconPlus size={18} />} onClick={() => onCreate({ barcode: debounced })}>
                Neues Lebensmittel mit diesem Barcode
              </Button>
            )}
          </Stack>
        </Alert>
      )}
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
