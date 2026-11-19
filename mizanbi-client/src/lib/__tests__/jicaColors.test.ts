import { describe, it, expect } from 'vitest'
import { classColors, JICA_LAYERS, JICA_GROUPS } from '../../components/JicaThemesMap'

describe('JICA themes', () => {
  it('sorts numeric classes numerically and gives each a distinct colour', () => {
    const m = classColors([300, 150, 50, 150, null])
    expect([...m.keys()]).toEqual(['50', '150', '300', '—'])
    expect(new Set(m.values()).size).toBe(4)
  })
  it('keeps text classes and declares the 7 catalogue layers', () => {
    expect(classColors(['b', 'a']).size).toBe(2)
    expect(new Set(classColors(Array.from({ length: 30 }, (_, i) => `c${i}`)).values()).size).toBe(30)
    expect(JICA_LAYERS.length).toBeGreaterThanOrEqual(30)
    expect(new Set(JICA_LAYERS.map(l => l.id)).size).toBe(JICA_LAYERS.length)
    expect(JICA_GROUPS.every(g => g.layers.length > 0)).toBe(true)
    expect(JICA_LAYERS.every(l => l.id.startsWith('jica_'))).toBe(true)
  })
})
