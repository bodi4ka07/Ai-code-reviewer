import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import qrcode from 'qrcode-terminal';

// Після запуску `npm run dev` друкує QR-код з адресою для телефона (та сама Wi-Fi мережа)
function terminalQr() {
  // Домашні мережі (192.168.x, 10.x) першими, віртуальні адаптери (Docker, WSL) останніми
  const rank = (url) => (/\/\/(192\.168|10\.)/.test(url) ? 0 : /\/\/172\.(1[6-9]|2\d|3[01])\./.test(url) ? 2 : 1);

  return {
    name: 'terminal-qr',
    configureServer(server) {
      const printUrls = server.printUrls.bind(server);
      server.printUrls = () => {
        printUrls();
        const [url] = [...(server.resolvedUrls?.network || [])].sort((a, b) => rank(a) - rank(b));
        if (!url) return;
        console.log('\n  Відкрийте на телефоні (той самий Wi-Fi, що й комп\'ютер):\n');
        qrcode.generate(url, { small: true }, (code) => console.log(code.replace(/^/gm, '  ')));
        console.log(`  ${url}\n`);
      };
    },
  };
}

export default defineConfig({
  plugins: [
    react(),
    terminalQr(),
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
