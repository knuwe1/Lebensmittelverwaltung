import { useState } from 'react';
import {
  Button,
  Group,
  NumberInput,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api, ApiError, errorMessage } from '../api/client';
import type { BaseUnit, Product } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { COMPATIBLE_PACKAGE_UNITS, PACKAGE_UNIT_LABELS, UNIT_LABELS } from '../lib/format';
import { CategorySelect, LocationSelect } from './selects';

const num = (v: string | number) => (v === '' ? null : Number(v));

interface Props {
  product?: Product;
  /** Bei Neuanlage: Barcode aus einem Scan übernehmen (AC-002) */
  initialBarcode?: string;
  initialName?: string;
  onSaved: (p: Product) => void;
  onCancel?: () => void;
  compact?: boolean;
}

/** Anlage und Bearbeitung von Lebensmittelstammdaten (FR-PRD-001, FR-PRD-006). */
export function ProductForm({ product, initialBarcode, initialName, onSaved, onCancel, compact }: Props) {
  const isNew = !product;
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const qc = useQueryClient();

  const [name, setName] = useState(product?.name ?? initialName ?? '');
  const [brand, setBrand] = useState(product?.brand ?? '');
  const [categoryId, setCategoryId] = useState<string | null>(product?.category_id ?? null);
  const [baseUnit, setBaseUnit] = useState<BaseUnit>(product?.base_unit ?? 'piece');
  const [locationId, setLocationId] = useState<string | null>(product?.default_location_id ?? null);
  const [shelfLife, setShelfLife] = useState<string | number>(product?.default_shelf_life_days ?? '');
  const [warnDays, setWarnDays] = useState<string | number>(product?.expiry_warning_days ?? '');
  const [minStock, setMinStock] = useState<string | number>(product?.minimum_stock ?? '');
  const [targetStock, setTargetStock] = useState<string | number>(product?.target_stock ?? '');
  const [notes, setNotes] = useState(product?.notes ?? '');
  // Erste Verpackungsvariante bei Neuanlage
  const [pkgQty, setPkgQty] = useState<string | number>('');
  const [pkgUnit, setPkgUnit] = useState<string>('piece');
  const [barcode, setBarcode] = useState(initialBarcode ?? '');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const mutation = useMutation({
    mutationFn: async () => {
      const common = {
        name: name.trim(),
        brand: brand.trim() || null,
        category_id: categoryId,
        base_unit: baseUnit,
        default_location_id: locationId,
        default_shelf_life_days: num(shelfLife),
        expiry_warning_days: num(warnDays),
        notes: notes.trim() || null,
        ...(isAdmin ? { minimum_stock: num(minStock), target_stock: num(targetStock) } : {}),
      };
      if (isNew) {
        const variants =
          pkgQty !== '' || barcode.trim()
            ? [
                {
                  package_quantity: pkgQty === '' ? 1 : Number(pkgQty),
                  package_unit: pkgQty === '' ? 'piece' : pkgUnit,
                  barcode: barcode.trim() || null,
                  is_default: true,
                },
              ]
            : [];
        return api.post<Product>('/products', { ...common, variants });
      }
      return api.patch<Product>(`/products/${product.id}`, common);
    },
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ['products'] });
      qc.setQueryData(['product', p.id], p);
      notifications.show({ color: 'green', message: `„${p.name}“ gespeichert.` });
      onSaved(p);
    },
    onError: (e) => {
      if (e instanceof ApiError) setErrors(e.fieldErrors);
      notifications.show({ color: 'red', message: errorMessage(e) });
    },
  });

  const units = COMPATIBLE_PACKAGE_UNITS[baseUnit];
  // Ohne Packungsgröße ergibt ein Barcode nur bei Stückware Sinn (1 Barcode = 1 Stück)
  const needsSize = isNew && barcode.trim() !== '' && pkgQty === '' && baseUnit !== 'piece';
  const unitShort = baseUnit === 'piece' ? 'Stück' : baseUnit;

  return (
    <Stack gap="sm">
      <TextInput label="Bezeichnung" required value={name} onChange={(e) => setName(e.currentTarget.value)} error={errors.name} data-autofocus />
      <SimpleGrid cols={{ base: 1, sm: 2 }}>
        <CategorySelect required value={categoryId} onChange={setCategoryId} error={errors.category_id} />
        <TextInput label="Hersteller / Marke" value={brand} onChange={(e) => setBrand(e.currentTarget.value)} />
      </SimpleGrid>
      <div>
        <Text size="sm" fw={500} mb={4}>
          Basiseinheit
        </Text>
        <SegmentedControl
          fullWidth
          value={baseUnit}
          onChange={(v) => {
            setBaseUnit(v as BaseUnit);
            setPkgUnit(COMPATIBLE_PACKAGE_UNITS[v as BaseUnit][0]);
          }}
          data={(['piece', 'g', 'ml'] as const).map((u) => ({ value: u, label: UNIT_LABELS[u] }))}
        />
      </div>

      {isNew && (
        <SimpleGrid cols={{ base: 2, sm: 3 }}>
          <NumberInput
            label="Packungsgröße"
            placeholder="optional"
            decimalSeparator=","
            thousandSeparator="."
            min={0}
            value={pkgQty}
            onChange={setPkgQty}
            error={needsSize ? 'Für den Barcode bitte die Packungsgröße angeben' : undefined}
          />
          <Select
            label="Einheit"
            data={units.map((u) => ({ value: u, label: PACKAGE_UNIT_LABELS[u] }))}
            value={pkgUnit}
            onChange={(v) => v && setPkgUnit(v)}
            allowDeselect={false}
          />
          <TextInput
            label="Barcode"
            inputMode="numeric"
            value={barcode}
            onChange={(e) => setBarcode(e.currentTarget.value)}
            error={errors['variants.0.barcode']}
          />
        </SimpleGrid>
      )}

      {!compact && (
        <>
          <SimpleGrid cols={{ base: 1, sm: 3 }}>
            <LocationSelect label="Standardlagerplatz" clearable value={locationId} onChange={setLocationId} />
            <NumberInput label="Standardhaltbarkeit (Tage)" min={0} value={shelfLife} onChange={setShelfLife} />
            <NumberInput label="Warnfrist vor Ablauf (Tage)" placeholder="Standard: 7" min={0} value={warnDays} onChange={setWarnDays} />
          </SimpleGrid>
          {isAdmin && (
            <SimpleGrid cols={2}>
              <NumberInput
                label={`Mindestbestand (${unitShort})`}
                placeholder="keine Überwachung"
                decimalSeparator=","
                thousandSeparator="."
                min={0}
                value={minStock}
                onChange={setMinStock}
              />
              <NumberInput
                label={`Zielbestand (${unitShort})`}
                decimalSeparator=","
                thousandSeparator="."
                min={0}
                value={targetStock}
                onChange={setTargetStock}
                error={errors.target_stock}
              />
            </SimpleGrid>
          )}
          <Textarea label="Notiz" autosize minRows={2} value={notes} onChange={(e) => setNotes(e.currentTarget.value)} />
        </>
      )}

      <Group justify="flex-end" mt="xs">
        {onCancel && (
          <Button variant="default" onClick={onCancel}>
            Abbrechen
          </Button>
        )}
        <Button onClick={() => mutation.mutate()} loading={mutation.isPending} disabled={!name.trim() || !categoryId || needsSize}>
          {isNew ? 'Anlegen' : 'Speichern'}
        </Button>
      </Group>
    </Stack>
  );
}
