import { describe, it, expect } from 'vitest'
import { APP_TITLE, documentTitle } from '../pageTitle'

const raw = (glob: Record<string, string>) => Object.values(glob)[0] ?? ''
const indexHtml = raw(import.meta.glob('/index.html', { query: '?raw', import: 'default', eager: true }) as Record<string, string>)
const robots = raw(import.meta.glob('/public/robots.txt', { query: '?raw', import: 'default', eager: true }) as Record<string, string>)
const notFound = raw(import.meta.glob('/public/404.html', { query: '?raw', import: 'default', eager: true }) as Record<string, string>)
const nginx = raw(import.meta.glob('/nginx.conf', { query: '?raw', import: 'default', eager: true }) as Record<string, string>)
const manifest = JSON.parse(raw(import.meta.glob('/public/site.webmanifest', { query: '?raw', import: 'default', eager: true }) as Record<string, string>))
const publicFiles = Object.keys(import.meta.glob('/public/*', { query: '?url', import: 'default' }))

const meta = (attr: 'name' | 'property', key: string): string | null => {
  const m = indexHtml.match(new RegExp(`<meta\\s+${attr}="${key}"\\s+content="([^"]*)"`))
  return m ? m[1] : null
}

async function readPublic(name: string): Promise<Uint8Array> {
  // fs chargé dynamiquement : @types/node n'est pas installé dans ce paquet.
  const fs = await import(/* @vite-ignore */ 'node:' + 'fs')
  return new Uint8Array(fs.readFileSync(new URL(`../../../public/${name}`, import.meta.url)))
}

function pngSize(b: Uint8Array): [number, number] {
  expect(String.fromCharCode(b[1], b[2], b[3])).toBe('PNG')
  const u32 = (o: number) => ((b[o] << 24) | (b[o + 1] << 16) | (b[o + 2] << 8) | b[o + 3]) >>> 0
  return [u32(16), u32(20)]
}

describe('page title and description', () => {
  it('has a descriptive title of reasonable length', () => {
    const t = indexHtml.match(/<title>([^<]*)<\/title>/)?.[1] ?? ''
    expect(t).toBe(APP_TITLE)
    expect(t.length).toBeGreaterThanOrEqual(20)
    expect(t.length).toBeLessThanOrEqual(60)
  })

  it('has a meta description of 70-160 characters', () => {
    const d = meta('name', 'description') ?? ''
    expect(d.length).toBeGreaterThanOrEqual(70)
    expect(d.length).toBeLessThanOrEqual(160)
  })

  it('documentTitle gives one unique title per screen', () => {
    expect(documentTitle('Tableaux de bord')).toBe('Tableaux de bord | MizanBI')
    expect(documentTitle('Cartographie SIG')).not.toBe(documentTitle('Accueil'))
    expect(documentTitle(null)).toBe(APP_TITLE)
    expect(documentTitle('  ')).toBe(APP_TITLE)
  })
})

describe('indexing policy (private application)', () => {
  it('is not indexable: noindex meta, and robots.txt does not block crawlers (so noindex and link previews work)', () => {
    expect(meta('name', 'robots')).toMatch(/noindex/)
    expect(robots).toMatch(/User-agent:\s*\*/)
    expect(robots).not.toMatch(/^\s*Disallow:\s*\/\s*$/m)
    expect(robots).not.toMatch(/^\s*Sitemap:/mi)
  })

  it('ships no sitemap (it would list non-indexable or non-existent URLs)', () => {
    expect(publicFiles.some(f => /sitemap/i.test(f))).toBe(false)
  })

  it('nginx sends noindex too', () => {
    expect(nginx).toMatch(/X-Robots-Tag\s+"noindex/)
  })
})

describe('social sharing (Open Graph / Twitter)', () => {
  it('declares the full tag set with a PNG image and absolute-URL placeholders', () => {
    for (const k of ['og:type', 'og:site_name', 'og:locale', 'og:title', 'og:description', 'og:image:alt']) expect(meta('property', k), k).toBeTruthy()
    expect(meta('property', 'og:image')).toBe('%SITE_URL%/og-image.png')
    expect(meta('property', 'og:url')).toBe('%SITE_URL%/')
    expect(meta('property', 'og:image:type')).toBe('image/png')
    expect(meta('name', 'twitter:card')).toBe('summary_large_image')
    expect(meta('name', 'twitter:image')).toBe('%SITE_URL%/og-image.png')
  })

  it('the shared image is a real 1200x630 PNG under 300 KB (SVG is not rendered by LinkedIn/Facebook)', async () => {
    const bytes = await readPublic('og-image.png')
    expect(pngSize(bytes)).toEqual([1200, 630])
    expect(meta('property', 'og:image:width')).toBe('1200')
    expect(meta('property', 'og:image:height')).toBe('630')
    expect(bytes.length / 1024).toBeLessThan(300)
  })
})

describe('favicons and manifest', () => {
  it('ships ico, svg, apple touch icon and Android icons', () => {
    for (const f of ['favicon.ico', 'favicon.svg', 'apple-touch-icon.png', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'site.webmanifest']) {
      expect(publicFiles, f).toContain(`/public/${f}`)
    }
  })

  it('index.html links them', () => {
    for (const h of ['/favicon.svg', '/favicon.ico', '/apple-touch-icon.png', '/site.webmanifest']) expect(indexHtml).toContain(`href="${h}"`)
  })

  it('manifest is valid and every icon exists', () => {
    expect(manifest.name).toBe('MizanBI')
    expect(manifest.start_url).toBe('/')
    expect(manifest.icons.length).toBeGreaterThanOrEqual(3)
    for (const i of manifest.icons as { src: string }[]) expect(publicFiles, i.src).toContain(`/public${i.src}`)
  })
})

describe('404', () => {
  it('has a custom, non-indexable page with a way back home', () => {
    expect(notFound).toContain('Page introuvable')
    expect(notFound).toContain('href="/"')
    expect(notFound).toContain("Retour à l'accueil")
    expect(notFound).toMatch(/name="robots"\s+content="noindex"/)
  })

  it('nginx returns a real 404 (no index.html fallback that would answer 200)', () => {
    expect(nginx).toMatch(/try_files\s+\$uri\s+\$uri\/\s+=404;/)
    expect(nginx).toMatch(/error_page\s+404\s+\/404\.html;/)
    expect(nginx).not.toMatch(/try_files[^;]*\/index\.html/)
  })
})
