import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: '/static/',
  build: {
    outDir: path.resolve(import.meta.dirname, '../app/static'),
    emptyOutDir: false,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/data': 'http://localhost:8000',
      '/evaluation': 'http://localhost:8000',
      '/static': 'http://localhost:8000',
    },
  },
});
