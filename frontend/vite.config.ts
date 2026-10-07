import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    // In development the API runs on :8000; in Docker, nginx does the same proxying.
    proxy: { '/api': 'http://localhost:8000' },
  },
})
