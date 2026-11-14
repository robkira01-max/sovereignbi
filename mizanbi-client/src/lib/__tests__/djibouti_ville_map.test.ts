/**
 * Tests for DjiboutiVilleMap data layer integration.
 * Verifies that all CERD SIG GeoJSON files have the expected structure
 * and that the new column names match what the components expect.
 */
import { describe, it, expect } from 'vitest'
import COMMUNES from '../../data/cerd_communes.json'
import SECTEURS from '../../data/cerd_secteurs.json'
import TYPOLOGIES from '../../data/cerd_typologies.json'
import EQUIPEMENTS from '../../data/cerd_equipements_sociaux.json'
import ECOLES from '../../data/cerd_ecoles.json'
import VOIRIE from '../../data/cerd_voirie.json'
import LIGNES_BUS from '../../data/cerd_lignes_bus.json'
import TERMINUS from '../../data/cerd_terminus_bus.json'

type FC = { type: string; features: { type: string; geometry: { type: string; coordinates: unknown }; properties: Record<string, unknown> }[] }

function asFC(raw: unknown): FC { return raw as FC }

// ── Feature counts ─────────────────────────────────────────────────────────────

describe('CERD GeoJSON feature counts', () => {
  it('communes: 2 features', () => {
    expect(asFC(COMMUNES).features).toHaveLength(2)
  })
  it('secteurs: 14 features', () => {
    expect(asFC(SECTEURS).features).toHaveLength(14)
  })
  it('typologies: 27 features', () => {
    expect(asFC(TYPOLOGIES).features).toHaveLength(27)
  })
  it('equipements sociaux: 81 features', () => {
    expect(asFC(EQUIPEMENTS).features).toHaveLength(81)
  })
  it('ecoles: 31 features', () => {
    expect(asFC(ECOLES).features).toHaveLength(31)
  })
  it('voirie: 1447 features', () => {
    expect(asFC(VOIRIE).features).toHaveLength(1447)
  })
  it('lignes bus: 5 features', () => {
    expect(asFC(LIGNES_BUS).features).toHaveLength(5)
  })
  it('terminus bus: 6 features', () => {
    expect(asFC(TERMINUS).features).toHaveLength(6)
  })
})

// ── WGS84 coordinates (lon ~43, lat ~11 for Djibouti-ville) ───────────────────

describe('CERD GeoJSON WGS84 coordinates', () => {
  function firstCoord(geo: { type: string; coordinates: unknown }): [number, number] {
    function walk(c: unknown): [number, number] | null {
      if (Array.isArray(c) && c.length >= 2 && typeof c[0] === 'number') return c as [number, number]
      if (Array.isArray(c)) { for (const x of c) { const r = walk(x); if (r) return r } }
      return null
    }
    return walk(geo.coordinates) ?? [0, 0]
  }

  for (const [name, raw] of [['communes', COMMUNES], ['secteurs', SECTEURS], ['typologies', TYPOLOGIES], ['equipements', EQUIPEMENTS], ['ecoles', ECOLES], ['voirie', VOIRIE]] as [string, unknown][]) {
    it(`${name}: first coordinate is in Djibouti-ville bbox`, () => {
      const fc = asFC(raw)
      const [lon, lat] = firstCoord(fc.features[0].geometry as { type: string; coordinates: unknown })
      expect(lon, `${name} lon`).toBeGreaterThan(42.9)
      expect(lon, `${name} lon`).toBeLessThan(43.5)
      expect(lat, `${name} lat`).toBeGreaterThan(11.3)
      expect(lat, `${name} lat`).toBeLessThan(11.8)
    })
  }
})

// ── Property key names (match what components expect) ─────────────────────────

describe('CERD GeoJSON property keys', () => {
  it('communes has nom_commun', () => {
    const p = asFC(COMMUNES).features[0].properties
    expect(p).toHaveProperty('nom_commun')
  })

  it('secteurs has nom', () => {
    const p = asFC(SECTEURS).features[0].properties
    expect(p).toHaveProperty('nom')
  })

  it('typologies has type_quart and nom', () => {
    const p = asFC(TYPOLOGIES).features[0].properties
    expect(p).toHaveProperty('type_quart')
    expect(p).toHaveProperty('nom')
    expect(['spontané dense', 'cité-lotissement', 'spontané tramé en cours de densification', 'trame acceuil', "trame d'acceuil en cours de densification"]).toContain(p['type_quart'])
  })

  it('equipements has categorie, sous_categ, nom', () => {
    const p = asFC(EQUIPEMENTS).features[0].properties
    expect(p).toHaveProperty('categorie')
    expect(p).toHaveProperty('sous_categ')
    expect(p).toHaveProperty('nom')
  })

  it('equipements categories are known values', () => {
    const known = new Set(['equipement scolaire', 'equipement sanitaire', 'equipement marchand', 'equipement religieux', 'equipement social', 'administration', 'equipement sportif', 'Zone militaire'])
    for (const f of asFC(EQUIPEMENTS).features) {
      expect(known.has(String(f.properties['categorie']))).toBe(true)
    }
  })

  it('ecoles has sous_categ (not sous_categorie)', () => {
    const p = asFC(ECOLES).features[0].properties
    expect(p).toHaveProperty('sous_categ')
    expect(p).not.toHaveProperty('sous_categorie')
  })

  it('ecoles has code_prima (not code_primaire)', () => {
    const p = asFC(ECOLES).features[0].properties
    expect(p).toHaveProperty('code_prima')
    expect(p).not.toHaveProperty('code_primaire')
  })

  it('voirie has hierachie and revetement', () => {
    const p = asFC(VOIRIE).features[0].properties
    expect(p).toHaveProperty('hierachie')
    expect(p).toHaveProperty('revetement')
  })

  it('voirie hierarchies are known values', () => {
    const known = new Set(['Reseau national', 'Axe structurant revetu', 'route secondaire revetue', null, ''])
    for (const f of asFC(VOIRIE).features) {
      expect(known.has(f.properties['hierachie'] as string | null)).toBe(true)
    }
  })

  it('lignes_bus has ligne and terminus', () => {
    const p = asFC(LIGNES_BUS).features[0].properties
    expect(p).toHaveProperty('ligne')
    expect(p).toHaveProperty('terminus')
  })
})

// ── Geometry types ─────────────────────────────────────────────────────────────

describe('CERD GeoJSON geometry types', () => {
  it('communes are Polygon or MultiPolygon', () => {
    for (const f of asFC(COMMUNES).features) {
      expect(['Polygon', 'MultiPolygon']).toContain(f.geometry.type)
    }
  })
  it('typologies are Polygon or MultiPolygon', () => {
    for (const f of asFC(TYPOLOGIES).features) {
      expect(['Polygon', 'MultiPolygon']).toContain(f.geometry.type)
    }
  })
  it('voirie features are LineString or MultiLineString', () => {
    for (const f of asFC(VOIRIE).features) {
      expect(['LineString', 'MultiLineString']).toContain(f.geometry.type)
    }
  })
  it('terminus_bus features are Point', () => {
    for (const f of asFC(TERMINUS).features) {
      expect(f.geometry.type).toBe('Point')
    }
  })
})
