import { useMemo, useState } from 'react';
import {
  ActionIcon,
  Alert,
  Autocomplete,
  Button,
  Card,
  Group,
  List,
  Menu,
  Modal,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
  UnstyledButton,
} from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconDots, IconFolder, IconPlus } from '@tabler/icons-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api, ApiError, errorMessage } from '../api/client';
import { useLocations } from '../api/hooks';
import type { BaseUnit, Location } from '../api/types';
import { useUser } from '../auth/AuthContext';
import { LocationSelect } from '../components/selects';
import { formatQuantity } from '../lib/format';

const LOCATION_TYPES = ['Raum', 'Kühlschrank', 'Gefrierschrank', 'Gefriertruhe', 'Schrank', 'Regal', 'Fach', 'Schublade', 'Kiste'];

type Dialog =
  | { kind: 'create'; parentId: string | null }
  | { kind: 'edit'; location: Location }
  | { kind: 'blocked'; location: Location; items: { product_name: string; quantity: number; base_unit: BaseUnit }[] }
  | null;

function LocationDialog({ dialog, onClose }: { dialog: Exclude<Dialog, null | { kind: 'blocked' }>; onClose: () => void }) {
  const qc = useQueryClient();
  const loc = dialog.kind === 'edit' ? dialog.location : null;
  const [name, setName] = useState(loc?.name ?? '');
  const [parentId, setParentId] = useState<string | null>(loc ? loc.parent_id : dialog.kind === 'create' ? dialog.parentId : null);
  const [type, setType] = useState(loc?.location_type ?? '');
  const [description, setDescription] = useState(loc?.description ?? '');
  const mutation = useMutation({
    mutationFn: () => {
      const body = { name: name.trim(), parent_id: parentId, location_type: type.trim() || null, description: description.trim() || null };
      return loc ? api.patch(`/locations/${loc.id}`, body) : api.post('/locations', body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['locations'] });
      qc.invalidateQueries({ queryKey: ['stock'] });
      onClose();
    },
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });
  return (
    <Stack>
      <TextInput label="Name" required value={name} onChange={(e) => setName(e.currentTarget.value)} data-autofocus />
      <LocationSelect label="Übergeordneter Lagerplatz" placeholder="– oberste Ebene –" clearable value={parentId} onChange={setParentId} excludeId={loc?.id} />
      <Autocomplete label="Art" data={LOCATION_TYPES} value={type} onChange={setType} />
      <Textarea label="Beschreibung" autosize value={description} onChange={(e) => setDescription(e.currentTarget.value)} />
      <Button onClick={() => mutation.mutate()} loading={mutation.isPending} disabled={!name.trim()}>
        Speichern
      </Button>
    </Stack>
  );
}

/** Hierarchische Lagerplatzverwaltung (FR-LOC-001…004). */
export function LocationsPage() {
  const user = useUser();
  const isAdmin = user.role === 'admin';
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data: locations = [] } = useLocations();
  const [dialog, setDialog] = useState<Dialog>(null);

  // Baum in Anzeigereihenfolge mit Einrückungstiefe
  const rows = useMemo(() => {
    const children = new Map<string | null, Location[]>();
    for (const l of locations) {
      const key = l.parent_id && locations.some((p) => p.id === l.parent_id) ? l.parent_id : null;
      children.set(key, [...(children.get(key) ?? []), l]);
    }
    const out: { loc: Location; depth: number }[] = [];
    const walk = (parent: string | null, depth: number) => {
      for (const l of (children.get(parent) ?? []).sort((a, b) => a.name.localeCompare(b.name, 'de'))) {
        out.push({ loc: l, depth });
        walk(l.id, depth + 1);
      }
    };
    walk(null, 0);
    return out;
  }, [locations]);

  const remove = useMutation({
    mutationFn: (loc: Location) => api.delete<{ result: string }>(`/locations/${loc.id}`),
    onSuccess: (r, loc) => {
      qc.invalidateQueries({ queryKey: ['locations'] });
      notifications.show({
        color: 'green',
        message: r.result === 'deleted' ? `„${loc.name}“ entfernt.` : `„${loc.name}“ deaktiviert (Historie bleibt erhalten).`,
      });
    },
    onError: (e, loc) => {
      if (e instanceof ApiError && e.code === 'location_has_stock' && Array.isArray(e.details)) {
        setDialog({ kind: 'blocked', location: loc, items: e.details as never });
      } else notifications.show({ color: 'red', message: errorMessage(e) });
    },
  });

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Lagerplätze</Title>
        {isAdmin && (
          <Button leftSection={<IconPlus size={18} />} onClick={() => setDialog({ kind: 'create', parentId: null })}>
            Lagerplatz
          </Button>
        )}
      </Group>
      {rows.length === 0 && (
        <Text c="dimmed">Noch keine Lagerplätze angelegt. Beispiel: Küche › Kühlschrank › Oberes Fach.</Text>
      )}
      <Card withBorder padding={0}>
        {rows.map(({ loc, depth }) => (
          <Group key={loc.id} justify="space-between" wrap="nowrap" px="sm" py={6} style={{ borderBottom: '1px solid var(--mantine-color-default-border)' }}>
            <UnstyledButton style={{ flex: 1, paddingLeft: depth * 20 }} onClick={() => navigate(`/vorraete?lagerplatz=${loc.id}`)}>
              <Group gap="xs" wrap="nowrap">
                <IconFolder size={18} stroke={1.5} />
                <div>
                  <Text size="sm" fw={depth === 0 ? 600 : 400}>
                    {loc.name}
                  </Text>
                  {loc.location_type && <Text size="xs" c="dimmed">{loc.location_type}</Text>}
                </div>
              </Group>
            </UnstyledButton>
            {isAdmin && (
              <Menu position="bottom-end">
                <Menu.Target>
                  <ActionIcon variant="subtle" aria-label={`Aktionen für ${loc.name}`}>
                    <IconDots size={18} />
                  </ActionIcon>
                </Menu.Target>
                <Menu.Dropdown>
                  <Menu.Item onClick={() => setDialog({ kind: 'create', parentId: loc.id })}>Unterlagerplatz anlegen</Menu.Item>
                  <Menu.Item onClick={() => setDialog({ kind: 'edit', location: loc })}>Bearbeiten / verschieben</Menu.Item>
                  <Menu.Item color="red" onClick={() => remove.mutate(loc)}>Entfernen</Menu.Item>
                </Menu.Dropdown>
              </Menu>
            )}
          </Group>
        ))}
      </Card>

      <Modal
        opened={dialog !== null && dialog.kind !== 'blocked'}
        onClose={() => setDialog(null)}
        title={dialog?.kind === 'edit' ? 'Lagerplatz bearbeiten' : 'Lagerplatz anlegen'}
      >
        {dialog && dialog.kind !== 'blocked' && <LocationDialog dialog={dialog} onClose={() => setDialog(null)} />}
      </Modal>
      <Modal opened={dialog?.kind === 'blocked'} onClose={() => setDialog(null)} title="Entfernen nicht möglich">
        {dialog?.kind === 'blocked' && (
          <Stack>
            <Alert color="yellow">
              An „{dialog.location.name}“ sind noch Bestände vorhanden. Bitte zuerst umlagern, verbrauchen oder ausbuchen.
            </Alert>
            <List>
              {dialog.items.map((i, idx) => (
                <List.Item key={idx}>
                  {i.product_name}: {formatQuantity(i.quantity, i.base_unit)}
                </List.Item>
              ))}
            </List>
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
