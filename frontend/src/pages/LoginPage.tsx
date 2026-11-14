import { useState } from 'react';
import type { FormEvent } from 'react';
import { Alert, Button, Center, Paper, PasswordInput, Stack, TextInput, Title } from '@mantine/core';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { errorMessage } from '../api/client';

export function LoginPage() {
  const { user, login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username.trim(), password);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Center mih="100dvh" p="md">
      <Paper withBorder shadow="sm" p="xl" radius="md" w="100%" maw={400}>
        <form onSubmit={submit}>
          <Stack>
            <Title order={2} ta="center">
              Lebensmittelverwaltung
            </Title>
            {error && <Alert color="red">{error}</Alert>}
            <TextInput
              label="Benutzername"
              autoComplete="username"
              autoCapitalize="none"
              value={username}
              onChange={(e) => setUsername(e.currentTarget.value)}
              required
              size="md"
            />
            <PasswordInput
              label="Passwort"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
              required
              size="md"
            />
            <Button type="submit" loading={busy} size="md">
              Anmelden
            </Button>
          </Stack>
        </form>
      </Paper>
    </Center>
  );
}
