import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // Lets the dev server share an origin with the API for cookie-based auth
      // (no cross-site cookie complications) while the backend still runs separately.
      '/api': {
        target: 'http://localhost:8010',
        changeOrigin: true,
      },
    },
  },
})
