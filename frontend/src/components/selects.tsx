import { Select } from '@mantine/core';
import type { SelectProps } from '@mantine/core';
import { useCategories, useLocations } from '../api/hooks';

type Props = Omit<SelectProps, 'data'> & { excludeId?: string; onlyIds?: string[] };

/** Lagerplatzauswahl mit vollständigem Pfad, durchsuchbar. */
export function LocationSelect({ excludeId, onlyIds, ...props }: Props) {
  const { data = [] } = useLocations();
  return (
    <Select
      label="Lagerplatz"
      placeholder="Lagerplatz wählen"
      searchable
      nothingFoundMessage="Kein Lagerplatz gefunden"
      data={data
        .filter((l) => l.id !== excludeId && (!onlyIds || onlyIds.includes(l.id)))
        .map((l) => ({ value: l.id, label: l.path }))}
      {...props}
    />
  );
}

export function CategorySelect(props: Omit<SelectProps, 'data'>) {
  const { data = [] } = useCategories();
  return (
    <Select
      label="Produktgruppe"
      placeholder="Produktgruppe wählen"
      searchable
      data={data.map((c) => ({ value: c.id, label: c.name }))}
      {...props}
    />
  );
}
