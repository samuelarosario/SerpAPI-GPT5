import { defineConfig } from 'vite';
import path from 'node:path';

export default defineConfig({
  root: '.',
  server: {
  port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/auth': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000'
    }
  },
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } }
});
