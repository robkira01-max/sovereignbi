import { describe, it, expect } from 'vitest'
import { ADM2_LEVELS, normName, escapeHtml, popupExtra } from '../adm2Levels'
import QUARTIERS from '../../data/admin_quartiers.json'

describe('ADM2_LEVELS', () => {
  it('quartiers level uses the official admin_pol layer joined on "nom"', () => {
    expect(ADM2_LEVELS.quartiers.endpoint).toBe('admin_quartiers')
    const first = (QUARTIERS as { features: { properties: Record<string, unknown> }[] }).features[0]
    expect(first.properties).toHaveProperty(ADM2_LEVELS.quartiers.nameKey)
    expect(ADM2_LEVELS.quartiers.note).toContain('CERD')
  })

  it('adm2 level keeps the district layer on "name"', () => {
    expect(ADM2_LEVELS.adm2.endpoint).toBe('adm2')
    expect(ADM2_LEVELS.adm2.nameKey).toBe('name')
  })

  it('quartiers view is centred on Djibouti-ville', () => {
    const [lon, lat] = ADM2_LEVELS.quartiers.center
    expect(lon).toBeGreaterThan(43.06)
    expect(lon).toBeLessThan(43.19)
    expect(lat).toBeGreaterThan(11.54)
    expect(lat).toBeLessThan(11.63)
  })
})

describe('normName', () => {
  it('matches names regardless of case, accents, apostrophes and spacing', () => {
    expect(normName("Cité d'Arhiba")).toBe(normName('CITE D’ARHIBA'))
    expect(normName('Quartier  7')).toBe(normName('quartier 7'))
    expect(normName('Bâche à eau')).toBe('bache a eau')
  })
})

describe('popupExtra', () => {
  it('quartiers: commune and area, HTML-escaped', () => {
    const h = popupExtra('quartiers', { commune: 'Boulaos', superficie_ha: 12.5 })
    expect(h).toContain('Commune : Boulaos')
    expect(h).toContain('ha')
    expect(popupExtra('quartiers', { commune: '<img src=x>' })).not.toContain('<img')
  })
  it('adm2: population', () => {
    expect(popupExtra('adm2', { population_est: 1000 })).toContain('Pop.')
    expect(popupExtra('adm2', {})).toBe('')
  })
  it('escapeHtml escapes markup characters', () => {
    expect(escapeHtml('<a href="x">&</a>')).toBe('&lt;a href=&quot;x&quot;&gt;&amp;&lt;/a&gt;')
  })
})
