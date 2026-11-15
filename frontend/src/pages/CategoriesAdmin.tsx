import { useState } from 'react';
import { ActionIcon, Badge, Button, Group, Stack, Table, TextInput } from '@mantine/core';
import { notifications } from '@mantine/notifications';
import { IconCheck, IconTrash } from '@tabler/icons-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, errorMessage } from '../api/client';
import type { Category } from '../api/types';

function Row({ category }: { category: Category }) {
  const qc = useQueryClient();
  const [name, setName] = useState(category.name);
  const invalidate = () => qc.invalidateQueries({ queryKey: ['categories'] });
  const save = useMutation({
    mutationFn: (body: Partial<Category>) => api.patch(`/categories/${category.id}`, body),
    onSuccess: invalidate,
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });
  const remove = useMutation({
    mutationFn: () => api.delete<{ result: string }>(`/categories/${category.id}`),
    onSuccess: (r) => {
      invalidate();
      if (r.result === 'deactivated')
        notifications.show({ message: 'Die Gruppe wird verwendet und wurde deaktiviert.' });
    },
  });
  return (
    <Table.Tr>
      <Table.Td>
        <TextInput size="sm" value={name} onChange={(e) => setName(e.currentTarget.value)} />
      </Table.Td>
      <Table.Td>{category.active ? <Badge color="green">aktiv</Badge> : <Badge color="gray">inaktiv</Badge>}</Table.Td>
      <Table.Td>
        <Group gap={4} wrap="nowrap">
          <ActionIcon variant="subtle" disabled={name.trim() === category.name || !name.trim()} onClick={() => save.mutate({ name: name.trim() })} aria-label="Speichern">
            <IconCheck size={18} />
          </ActionIcon>
          {category.active ? (
            <ActionIcon variant="subtle" color="red" onClick={() => remove.mutate()} aria-label="Entfernen">
              <IconTrash size={18} />
            </ActionIcon>
          ) : (
            <Button size="compact-xs" variant="light" onClick={() => save.mutate({ active: true })}>
              Aktivieren
            </Button>
          )}
        </Group>
      </Table.Td>
    </Table.Tr>
  );
}

/** Produktgruppen verwalten (Spezifikation 4.2 – durch Administrator erweiterbar). */
export function CategoriesAdmin() {
  const qc = useQueryClient();
  const { data = [] } = useQuery({
    queryKey: ['categories', 'all'],
    queryFn: () => api.get<Category[]>('/categories', { include_inactive: true }),
  });
  const [name, setName] = useState('');
  const create = useMutation({
    mutationFn: () => api.post('/categories', { name: name.trim(), sort_order: (data.length + 1) * 10 }),
    onSuccess: () => {
      setName('');
      qc.invalidateQueries({ queryKey: ['categories'] });
    },
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });
  return (
    <Stack maw={560}>
      <Group align="flex-end">
        <TextInput style={{ flex: 1 }} label="Neue Produktgruppe" value={name} onChange={(e) => setName(e.currentTarget.value)} />
        <Button onClick={() => create.mutate()} disabled={!name.trim()} loading={create.isPending}>
          Anlegen
        </Button>
      </Group>
      <Table>
        <Table.Tbody>
          {data.map((c) => (
            <Row key={c.id} category={c} />
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  );
}
