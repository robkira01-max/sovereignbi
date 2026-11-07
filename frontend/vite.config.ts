import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

function geojsonPlugin(): Plugin {
  return {
    name: 'geojson',
    transform(code, id) {
      if (!id.endsWith('.geojson')) return
      return { code: `export default ${code}`, map: null }
    },
  }
}

export default defineConfig({
  plugins: [react(), geojsonPlugin()],
  base: process.env.VERCEL ? '/' : '/app/',
  build: {
    outDir: 'dist',
    commonjsOptions: { include: [/maplibre-gl/, /node_modules/] },
  },
  optimizeDeps: {
    include: ['maplibre-gl'],
  },
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', rewrite: (p: string) => p.replace(/^\/api/, '') }
    }
  }
})
