import { describe, it, expect } from 'vitest'
import { GLYPHS_URL, MAP_TEXT_FONT } from '../mapFonts'

const glyphFiles = Object.keys(import.meta.glob('/public/fonts/**/*.pbf', { query: '?url', import: 'default' }))
const sources = import.meta.glob('../../components/{MapLibreMap,MapAdm2,BivariateChoropleth}.tsx', {
  query: '?raw', import: 'default', eager: true,
}) as Record<string, string>

describe('self-hosted map glyphs', () => {
  it('uses a same-origin glyph URL (no third-party font server)', () => {
    expect(GLYPHS_URL.startsWith('/')).toBe(true)
    expect(GLYPHS_URL).not.toMatch(/^https?:/)
  })

  it('ships the glyph ranges for the font stack used by map labels', () => {
    const stack = MAP_TEXT_FONT.join(',')
    for (const r of ['0-255.pbf', '256-511.pbf', '8192-8447.pbf']) {
      expect(glyphFiles).toContain(`/public/fonts/${stack}/${r}`)
    }
  })

  it('no map component references a remote glyph server', () => {
    expect(Object.keys(sources)).toHaveLength(3)
    for (const [file, src] of Object.entries(sources)) {
      expect(src, file).not.toContain('fonts.openmaptiles.org')
      expect(src, file).toContain('GLYPHS_URL')
    }
  })
})
