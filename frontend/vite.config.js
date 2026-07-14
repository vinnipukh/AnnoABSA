/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react({
    include: "**/*.{jsx,tsx,js,ts}",
    babel: {
      plugins: []
    }
  })],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: [],
  },
  server: {
    port: 3000,
    host: 'localhost',
    open: true
  },
  build: {
    outDir: 'build'
  }
})



