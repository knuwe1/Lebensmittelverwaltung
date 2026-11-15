import {
  IconBuildingWarehouse,
  IconCalendarExclamation,
  IconClipboardList,
  IconHistory,
  IconLayoutDashboard,
  IconPackageExport,
  IconPackageImport,
  IconPackages,
  IconSettings,
  IconShoppingCart,
  IconToolsKitchen2,
} from '@tabler/icons-react';
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
  { to: '/einlagern', label: 'Einlagern', icon: IconPackageImport },
  { to: '/entnehmen', label: 'Entnehmen', icon: IconPackageExport },
  { to: '/vorraete', label: 'Vorräte', icon: IconPackages },
  { to: '/einkaufsliste', label: 'Einkaufsliste', icon: IconShoppingCart },
  { to: '/haltbarkeit', label: 'Haltbarkeit', icon: IconCalendarExclamation },
  { to: '/lebensmittel', label: 'Lebensmittel', icon: IconToolsKitchen2 },
  { to: '/lagerplaetze', label: 'Lagerplätze', icon: IconBuildingWarehouse },
  { to: '/inventur', label: 'Inventur', icon: IconClipboardList },
  { to: '/historie', label: 'Historie', icon: IconHistory },
  { to: '/einstellungen', label: 'Einstellungen', icon: IconSettings },
];

/** Große Schnellaktionen in der mobilen Fußleiste (Spezifikation 9.3). */
export const MOBILE_ACTIONS: NavItem[] = [
  { to: '/', label: 'Start', icon: IconLayoutDashboard },
  { to: '/einlagern', label: 'Einlagern', icon: IconPackageImport },
  { to: '/entnehmen', label: 'Entnehmen', icon: IconPackageExport },
  { to: '/vorraete', label: 'Vorräte', icon: IconPackages },
  { to: '/einkaufsliste', label: 'Einkauf', icon: IconShoppingCart },
];
