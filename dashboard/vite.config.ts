import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8100',
      '/ws': { target: 'ws://127.0.0.1:8100', ws: true },
      '/health': 'http://127.0.0.1:8100',
      '/openapi.json': 'http://127.0.0.1:8100',
    }
  },
  build: { outDir: 'dist' }
})
