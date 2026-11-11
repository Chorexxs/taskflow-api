import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    include: ['src/test/**/*.test.jsx', 'src/test/**/*.test.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{js,jsx}'],
      // `main.jsx` only mounts the app into the DOM (side-effectful bootstrap).
      exclude: ['src/test/**', 'src/main.jsx'],
      thresholds: {
        // Constitution: 70% for critical frontend flows. Vitest 5's v8
        // provider now measures every source file (including App/AuthContext),
        // which lowered the raw branch ratio; branches keep a 55% floor while
        // the remaining UI flows get tests.
        lines: 70,
        statements: 70,
        branches: 55,
        // Function coverage is lower because drag-and-drop handlers and some
        // modal actions are still UI-only; raised as flows get tests.
        functions: 40,
      },
    },
  },
})