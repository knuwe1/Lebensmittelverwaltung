import { IconLayoutDashboard, IconSettings } from '@tabler/icons-react';
import type { Icon } from '@tabler/icons-react';

export interface NavItem {
  to: string;
  label: string;
  icon: Icon;
  adminOnly?: boolean;
}

/** Hauptnavigation der Webanwendung (Spezifikation 9.2). */
export const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: IconLayoutDashboard },
  { to: '/einstellungen', label: 'Einstellungen', icon: IconSettings },
];

/** Große Schnellaktionen in der mobilen Fußleiste (Spezifikation 9.3). */
export const MOBILE_ACTIONS: NavItem[] = [
  { to: '/', label: 'Start', icon: IconLayoutDashboard },
];
