import { describe, it, expect } from 'vitest'
import { classColors, JICA_LAYERS } from '../../components/JicaThemesMap'

describe('JICA themes', () => {
  it('sorts numeric classes numerically and gives each a distinct colour', () => {
    const m = classColors([300, 150, 50, 150, null])
    expect([...m.keys()]).toEqual(['50', '150', '300', '—'])
    expect(new Set(m.values()).size).toBe(4)
  })
  it('keeps text classes and declares the 7 catalogue layers', () => {
    expect(classColors(['b', 'a']).size).toBe(2)
    expect(JICA_LAYERS.map(l => l.id)).toHaveLength(7)
    expect(JICA_LAYERS.every(l => l.id.startsWith('jica_'))).toBe(true)
  })
})
