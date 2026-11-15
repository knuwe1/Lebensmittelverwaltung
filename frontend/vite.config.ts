/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icon.svg'],
      manifest: {
        name: 'Lebensmittelverwaltung',
        short_name: 'Vorräte',
        description: 'Lebensmittel- und Vorratsverwaltung für den Haushalt',
        lang: 'de',
        start_url: '/',
        display: 'standalone',
        background_color: '#ffffff',
        theme_color: '#2f9e44',
        icons: [
          { src: 'icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any maskable' },
        ],
      },
      workbox: {
        // Nur die App-Hülle wird gecacht. API-Antworten nie – Buchungen benötigen
        // immer eine Serververbindung (NFR-REL-003, DEC-010).
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [],
      },
    }),
  ],
  server: {
    host: true,
    proxy: { '/api': { target: 'http://localhost:8000' } },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    css: false,
  },
});
