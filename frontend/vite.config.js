import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // Forwards /api requests to the FastAPI backend during dev, so
      // the frontend can call relative paths ("/api/v1/datasets")
      // without hardcoding http://localhost:8000 everywhere or running
      // into CORS during local development.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
