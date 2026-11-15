import { Center, Loader, Stack, Text, Title } from '@mantine/core';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from './auth/AuthContext';
import { AppLayout } from './layout/AppLayout';
import { ConsumePage } from './pages/ConsumePage';
import { DashboardPage } from './pages/DashboardPage';
import { ExpiryPage } from './pages/ExpiryPage';
import { HistoryPage } from './pages/HistoryPage';
import { InventoryDetailPage } from './pages/InventoryDetailPage';
import { InventoryPage } from './pages/InventoryPage';
import { LocationsPage } from './pages/LocationsPage';
import { LoginPage } from './pages/LoginPage';
import { ProductDetailPage } from './pages/ProductDetailPage';
import { ProductsPage } from './pages/ProductsPage';
import { ReceivePage } from './pages/ReceivePage';
import { SettingsPage } from './pages/SettingsPage';
import { ShoppingListPage } from './pages/ShoppingListPage';
import { StockPage } from './pages/StockPage';

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) {
    return (
      <Center mih="100dvh">
        <Loader />
      </Center>
    );
  }
  if (!user) return <Navigate to="/anmelden" replace state={{ from: location }} />;
  return <>{children}</>;
}

function NotFound() {
  return (
    <Stack>
      <Title order={2}>Seite nicht gefunden</Title>
      <Text>Die angeforderte Seite existiert nicht.</Text>
    </Stack>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/anmelden" element={<LoginPage />} />
      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="einlagern" element={<ReceivePage />} />
        <Route path="entnehmen" element={<ConsumePage />} />
        <Route path="vorraete" element={<StockPage />} />
        <Route path="haltbarkeit" element={<ExpiryPage />} />
        <Route path="einkaufsliste" element={<ShoppingListPage />} />
        <Route path="historie" element={<HistoryPage />} />
        <Route path="inventur" element={<InventoryPage />} />
        <Route path="inventur/:id" element={<InventoryDetailPage />} />
        <Route path="lebensmittel" element={<ProductsPage />} />
        <Route path="lebensmittel/:id" element={<ProductDetailPage />} />
        <Route path="lagerplaetze" element={<LocationsPage />} />
        <Route path="einstellungen" element={<SettingsPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
