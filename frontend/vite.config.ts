import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: process.env.VERCEL ? '/' : '/app/',
  build: { outDir: 'dist' },
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', rewrite: (p: string) => p.replace(/^\/api/, '') }
    }
  }
})
