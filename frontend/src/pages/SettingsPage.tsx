import { useState } from 'react';
import {
  Badge,
  Button,
  Checkbox,
  Group,
  Modal,
  PasswordInput,
  Select,
  Stack,
  Switch,
  Table,
  Tabs,
  TextInput,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { notifications } from '@mantine/notifications';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, errorMessage } from '../api/client';
import type { Role, User } from '../api/types';
import { useUser } from '../auth/AuthContext';
import { CategoriesAdmin } from './CategoriesAdmin';

function PasswordForm() {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const mutation = useMutation({
    mutationFn: () =>
      api.post('/auth/password', { current_password: current, new_password: next }),
    onSuccess: () => {
      notifications.show({ color: 'green', message: 'Passwort geändert.' });
      setCurrent('');
      setNext('');
    },
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });
  return (
    <Stack maw={400}>
      <PasswordInput label="Aktuelles Passwort" value={current} onChange={(e) => setCurrent(e.currentTarget.value)} />
      <PasswordInput
        label="Neues Passwort"
        description="Mindestens 8 Zeichen"
        value={next}
        onChange={(e) => setNext(e.currentTarget.value)}
      />
      <Button onClick={() => mutation.mutate()} loading={mutation.isPending} disabled={!current || next.length < 8}>
        Passwort ändern
      </Button>
    </Stack>
  );
}

function UserDialog({ user, onClose }: { user: User | null; onClose: () => void }) {
  const qc = useQueryClient();
  const isNew = user === null;
  const [username, setUsername] = useState(user?.username ?? '');
  const [displayName, setDisplayName] = useState(user?.display_name ?? '');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<Role>(user?.role ?? 'member');
  const [inventory, setInventory] = useState(user?.can_do_inventory ?? false);
  const [active, setActive] = useState(user?.active ?? true);

  const mutation = useMutation({
    mutationFn: () =>
      isNew
        ? api.post('/users', {
            username,
            display_name: displayName,
            password,
            role,
            can_do_inventory: inventory,
          })
        : api.patch(`/users/${user.id}`, {
            display_name: displayName,
            role,
            can_do_inventory: inventory,
            active,
            ...(password ? { password } : {}),
          }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      notifications.show({ color: 'green', message: 'Benutzer gespeichert.' });
      onClose();
    },
    onError: (e) => notifications.show({ color: 'red', message: errorMessage(e) }),
  });

  return (
    <Stack>
      <TextInput label="Benutzername" value={username} disabled={!isNew} onChange={(e) => setUsername(e.currentTarget.value)} />
      <TextInput label="Anzeigename" value={displayName} onChange={(e) => setDisplayName(e.currentTarget.value)} />
      <PasswordInput
        label={isNew ? 'Passwort' : 'Neues Passwort (optional)'}
        value={password}
        onChange={(e) => setPassword(e.currentTarget.value)}
      />
      <Select
        label="Rolle"
        data={[
          { value: 'member', label: 'Haushaltsmitglied' },
          { value: 'admin', label: 'Administrator' },
        ]}
        value={role}
        onChange={(v) => v && setRole(v as Role)}
        allowDeselect={false}
      />
      <Checkbox label="Darf Inventuren durchführen" checked={inventory} onChange={(e) => setInventory(e.currentTarget.checked)} />
      {!isNew && <Switch label="Aktiv" checked={active} onChange={(e) => setActive(e.currentTarget.checked)} />}
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose}>
          Abbrechen
        </Button>
        <Button onClick={() => mutation.mutate()} loading={mutation.isPending}>
          Speichern
        </Button>
      </Group>
    </Stack>
  );
}

function UserAdmin() {
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api.get<User[]>('/users') });
  const [opened, { open, close }] = useDisclosure();
  const [editing, setEditing] = useState<User | null>(null);

  return (
    <Stack>
      <Group justify="flex-end">
        <Button
          onClick={() => {
            setEditing(null);
            open();
          }}
        >
          Benutzer anlegen
        </Button>
      </Group>
      <Table.ScrollContainer minWidth={500}>
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Benutzer</Table.Th>
              <Table.Th>Rolle</Table.Th>
              <Table.Th>Inventur</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {users.map((u) => (
              <Table.Tr
                key={u.id}
                style={{ cursor: 'pointer' }}
                onClick={() => {
                  setEditing(u);
                  open();
                }}
              >
                <Table.Td>
                  {u.display_name} <small>({u.username})</small>
                </Table.Td>
                <Table.Td>{u.role === 'admin' ? 'Administrator' : 'Haushaltsmitglied'}</Table.Td>
                <Table.Td>{u.role === 'admin' || u.can_do_inventory ? 'Ja' : 'Nein'}</Table.Td>
                <Table.Td>
                  {u.active ? <Badge color="green">Aktiv</Badge> : <Badge color="gray">Deaktiviert</Badge>}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
      <Modal opened={opened} onClose={close} title={editing ? 'Benutzer bearbeiten' : 'Benutzer anlegen'}>
        {opened && <UserDialog key={editing?.id ?? 'new'} user={editing} onClose={close} />}
      </Modal>
    </Stack>
  );
}

export function SettingsPage() {
  const user = useUser();
  return (
    <Stack>
      <Title order={2}>Einstellungen</Title>
      <Tabs defaultValue="konto" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="konto">Mein Konto</Tabs.Tab>
          {user.role === 'admin' && <Tabs.Tab value="benutzer">Benutzer</Tabs.Tab>}
          {user.role === 'admin' && <Tabs.Tab value="gruppen">Produktgruppen</Tabs.Tab>}
        </Tabs.List>
        <Tabs.Panel value="konto" pt="md">
          <PasswordForm />
        </Tabs.Panel>
        {user.role === 'admin' && (
          <Tabs.Panel value="benutzer" pt="md">
            <UserAdmin />
          </Tabs.Panel>
        )}
        {user.role === 'admin' && (
          <Tabs.Panel value="gruppen" pt="md">
            <CategoriesAdmin />
          </Tabs.Panel>
        )}
      </Tabs>
    </Stack>
  );
}
