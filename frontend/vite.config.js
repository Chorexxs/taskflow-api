import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    environmentOptions: {
      jsdom: {
        url: 'http://localhost:5173/',
      },
    },
    globals: true,
    setupFiles: './src/test/setup.js',
    css: true,
    env: {
      // Tests must never call the deployed API.
      VITE_API_URL: 'http://localhost:8000',
    },
  },
})
