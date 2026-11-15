import { Alert, AppShell, Burger, Group, Menu, NavLink, Text, UnstyledButton } from '@mantine/core';
import { useDisclosure, useMediaQuery, useNetwork } from '@mantine/hooks';
import { IconLogout, IconUserCircle, IconWifiOff } from '@tabler/icons-react';
import { NavLink as RouterLink, Outlet, useLocation } from 'react-router-dom';
import { useAuth, useUser } from '../auth/AuthContext';
import { MOBILE_ACTIONS, NAV_ITEMS } from './navigation';
import classes from './AppLayout.module.css';

export function AppLayout() {
  const [opened, { toggle, close }] = useDisclosure();
  const user = useUser();
  const { logout } = useAuth();
  const location = useLocation();
  const network = useNetwork();
  const isMobile = useMediaQuery('(max-width: 48em)') ?? false;

  const items = NAV_ITEMS.filter((i) => !i.adminOnly || user.role === 'admin');
  const isActive = (to: string) =>
    to === '/' ? location.pathname === '/' : location.pathname.startsWith(to);

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 240, breakpoint: 'sm', collapsed: { mobile: !opened } }}
      footer={{ height: 68, collapsed: !isMobile }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs">
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" aria-label="Menü" />
            <Text fw={700} component={RouterLink} to="/" className={classes.brand}>
              Lebensmittelverwaltung
            </Text>
          </Group>
          <Menu position="bottom-end">
            <Menu.Target>
              <UnstyledButton aria-label="Benutzermenü">
                <Group gap={6}>
                  <IconUserCircle size={22} />
                  <Text size="sm" visibleFrom="xs">
                    {user.display_name}
                  </Text>
                </Group>
              </UnstyledButton>
            </Menu.Target>
            <Menu.Dropdown>
              <Menu.Item leftSection={<IconLogout size={16} />} onClick={logout}>
                Abmelden
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>
      </AppShell.Header>

      <AppShell.Navbar p="xs">
        {items.map((item) => (
          <NavLink
            key={item.to}
            component={RouterLink}
            to={item.to}
            label={item.label}
            leftSection={<item.icon size={20} stroke={1.6} />}
            active={isActive(item.to)}
            onClick={close}
          />
        ))}
      </AppShell.Navbar>

      <AppShell.Main>
        {!network.online && (
          <Alert color="red" icon={<IconWifiOff />} mb="md" title="Keine Verbindung">
            Buchungen sind derzeit nicht möglich. Bitte Netzwerkverbindung prüfen.
          </Alert>
        )}
        <Outlet />
      </AppShell.Main>

      <AppShell.Footer>
        <nav className={classes.bottomNav}>
          {MOBILE_ACTIONS.map((a) => (
            <RouterLink
              key={a.to}
              to={a.to}
              className={classes.bottomItem}
              data-active={isActive(a.to) || undefined}
            >
              <a.icon size={26} stroke={1.6} />
              <span>{a.label}</span>
            </RouterLink>
          ))}
        </nav>
      </AppShell.Footer>
    </AppShell>
  );
}
