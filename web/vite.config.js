import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
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
});
