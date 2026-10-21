/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In dev, the api runs in compose behind its Caddy (127.0.0.1:8030) or on the host;
// SWAP_API points the proxy elsewhere.
const api = process.env.SWAP_API ?? 'http://127.0.0.1:8030'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5180,
    strictPort: true,
    proxy: { '/api': api, '/healthz': api },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
