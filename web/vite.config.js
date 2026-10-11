import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      '/jobs': 'http://localhost:8000',
      '/tickets': 'http://localhost:8000',
      '/export.csv': 'http://localhost:8000',
      '/webhooks': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
  build: {
    // Perf: keep Leaflet + Motion out of the initial chunk so the first
    // paint (header/rail/skeleton) stays lean. Map + drawer load on demand.
    rollupOptions: {
      output: {
        manualChunks: {
          leaflet: ['leaflet', 'react-leaflet'],
          motion: ['framer-motion'],
          radix: ['@radix-ui/react-dialog', '@radix-ui/react-tooltip', '@radix-ui/react-slot'],
        },
      },
    },
  },
});
