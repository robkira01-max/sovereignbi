import { defineConfig, loadEnv, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'

// Les réseaux sociaux exigent des URL absolues pour og:image / og:url.
// VITE_SITE_URL (ex. https://mizanbi.example.org) remplace %SITE_URL% dans index.html ;
// non défini : URL relatives (le site fonctionne, mais les aperçus de partage échoueront).
function siteUrl(env: Record<string, string>): Plugin {
  const base = (env.VITE_SITE_URL ?? '').replace(/\/+$/, '')
  return {
    name: 'mizan-site-url',
    transformIndexHtml(html) {
      if (!base) console.warn('[mizan-site-url] VITE_SITE_URL non défini : og:image et og:url resteront relatifs.')
      return html.split('%SITE_URL%').join(base)
    },
  }
}

export default defineConfig(({ mode }) => ({
  plugins: [react(), siteUrl(loadEnv(mode, '.', 'VITE_'))],
}))
