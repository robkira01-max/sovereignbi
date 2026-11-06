import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import type { Plugin } from 'vite'

function geojsonPlugin(): Plugin {
  return {
    name: 'geojson-transform',
    transform(code, id) {
      if (id.endsWith('.geojson')) {
        return { code: `export default ${code}`, map: null }
      }
    },
  }
}

export default defineConfig({
  plugins: [react(), geojsonPlugin()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts'],
  }
})
