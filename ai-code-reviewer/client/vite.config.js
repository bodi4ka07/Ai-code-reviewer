import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icons/icon.svg'],
      manifest: {
        name: 'AI Code Reviewer',
        short_name: 'Code Reviewer',
        description: "Автоматичне рев'ю коду за допомогою AI",
        lang: 'uk',
        start_url: '/',
        display: 'standalone',
        background_color: '#0a0d14',
        theme_color: '#0a0d14',
        icons: [
          { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      // Запити до API ніколи не кешуються і не підміняються index.html
      workbox: { navigateFallbackDenylist: [/^\/api\//] },
    }),
  ],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
