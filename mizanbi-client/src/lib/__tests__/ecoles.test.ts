import { describe, it, expect } from 'vitest'
import ECOLES_GEO from '../../data/ecoles-djibouti.json'
import { projectLonLat, djiboutiBounds, djiVilleBounds, buildDjiboutiVilleMap, getQuartierForPoint } from '../geo'

interface EcoleProps {
  name: string; type: string; amenity: string | null
  district_adm2: string; osm_id: number; source: string
}
interface EcoleFeature {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: EcoleProps
}

const ECOLES = (ECOLES_GEO as unknown as { features: EcoleFeature[] }).features

describe('ecoles-djibouti.json', () => {
  it('contains 97 features', () => {
    expect(ECOLES).toHaveLength(97)
  })

  it('every feature has Point geometry with [lon, lat]', () => {
    for (const f of ECOLES) {
      expect(f.geometry.type).toBe('Point')
      expect(f.geometry.coordinates).toHaveLength(2)
      const [lon, lat] = f.geometry.coordinates
      expect(lon).toBeGreaterThan(41)
      expect(lon).toBeLessThan(44)
      expect(lat).toBeGreaterThan(10)
      expect(lat).toBeLessThan(13)
    }
  })

  it('every feature has name, type, district_adm2 and osm_id', () => {
    for (const f of ECOLES) {
      expect(typeof f.properties.name).toBe('string')
      expect(f.properties.name.length).toBeGreaterThan(0)
      expect(typeof f.properties.type).toBe('string')
      expect(typeof f.properties.district_adm2).toBe('string')
      expect(typeof f.properties.osm_id).toBe('number')
    }
  })

  it('covers known Djibouti districts', () => {
    const districts = new Set(ECOLES.map((f) => f.properties.district_adm2))
    expect(districts.has('Djibouti')).toBe(true)
    expect(districts.has('Ali Sabieh')).toBe(true)
    expect(districts.has('Dikhil')).toBe(true)
  })

  it('Djibouti district has the most schools (51)', () => {
    const djCount = ECOLES.filter((f) => f.properties.district_adm2 === 'Djibouti').length
    expect(djCount).toBe(51)
  })

  it('projects all schools within SVG viewBox bounds', () => {
    const bounds = djiboutiBounds()
    for (const f of ECOLES) {
      const { x, y } = projectLonLat(f.geometry.coordinates[0], f.geometry.coordinates[1], bounds)
      expect(Number.isFinite(x)).toBe(true)
      expect(Number.isFinite(y)).toBe(true)
      expect(x).toBeGreaterThanOrEqual(-10)
      expect(x).toBeLessThanOrEqual(320)
      expect(y).toBeGreaterThanOrEqual(-10)
      expect(y).toBeLessThanOrEqual(320)
    }
  })

  it('has expected school types', () => {
    const types = new Set(ECOLES.map((f) => f.properties.type))
    expect([...types].some((t) => t.includes('Primaire'))).toBe(true)
    expect([...types].some((t) => t.includes('College'))).toBe(true)
    expect([...types].some((t) => t.includes('Lycee'))).toBe(true)
    expect([...types].some((t) => t.includes('Universite'))).toBe(true)
  })

  it('source attribution is OpenStreetMap', () => {
    for (const f of ECOLES) {
      expect(f.properties.source).toContain('OpenStreetMap')
    }
  })
})

describe('i18n ecoles section', () => {
  it('fr and en define ecoles section with same keys', async () => {
    const { I18N } = await import('../i18n')
    const frKeys = Object.keys(I18N.fr.ecoles).sort()
    expect(frKeys.length).toBeGreaterThan(5)
    expect(Object.keys(I18N.en.ecoles).sort()).toEqual(frKeys)
  })
})

describe('djiVilleBounds', () => {
  it('returns bounds within Djibouti-ville lon/lat range', () => {
    const b = djiVilleBounds()
    expect(b.x0).toBeGreaterThan(42.9)
    expect(b.x1).toBeLessThan(43.3)
    expect(b.y0).toBeGreaterThan(11.4)
    expect(b.y1).toBeLessThan(11.7)
    expect(b.sc).toBeGreaterThan(0)
    expect(b.k).toBeGreaterThan(0)
  })
})

describe('buildDjiboutiVilleMap', () => {
  it('returns 11 shapes for the 11 quartiers', () => {
    const m = buildDjiboutiVilleMap()
    expect(m.shapes).toHaveLength(11)
  })

  it('all shapes have non-empty d and name', () => {
    const m = buildDjiboutiVilleMap()
    for (const s of m.shapes) {
      expect(s.d.length).toBeGreaterThan(0)
      expect(s.name.length).toBeGreaterThan(0)
    }
  })

  it('includes Centre-ville quartier', () => {
    const m = buildDjiboutiVilleMap()
    expect(m.shapes.some((s) => s.name === 'Centre-ville')).toBe(true)
  })
})

describe('getQuartierForPoint', () => {
  it('returns null for a point outside Djibouti-ville', () => {
    // Obock region, far from Djibouti-ville
    expect(getQuartierForPoint(43.28, 11.98)).toBeNull()
  })

  it('Djibouti-district schools: majority fall within a quartier', () => {
    const dj = ECOLES.filter((f) => f.properties.district_adm2 === 'Djibouti')
    const matched = dj.filter((f) => getQuartierForPoint(f.geometry.coordinates[0], f.geometry.coordinates[1]) !== null)
    // at least half of the 51 Djibouti-district schools should land in a quartier polygon
    expect(matched.length).toBeGreaterThan(dj.length / 2)
  })
})
