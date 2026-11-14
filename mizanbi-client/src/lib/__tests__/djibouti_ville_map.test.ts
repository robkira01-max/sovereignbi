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
import OSM_VOIRIE from '../../data/osm_centre_voirie.json'
import QUARTIERS from '../../data/admin_quartiers.json'
import COMMUNES_ADMIN from '../../data/admin_communes.json'

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

// ── Centre-ville (OSM, hors couverture CERD) ──────────────────────────────────

describe('OSM centre-ville layers', () => {
  const voirie = asFC(OSM_VOIRIE)

  it('voirie: 1875 line features, all in the centre bbox (east of CERD Balbala)', () => {
    expect(voirie.features).toHaveLength(1875)
    function walk(c: unknown, cb: (x: number, y: number) => void) {
      if (Array.isArray(c) && typeof c[0] === 'number') cb(c[0] as number, c[1] as number)
      else if (Array.isArray(c)) c.forEach((i) => walk(i, cb))
    }
    for (const f of voirie.features) {
      expect(['LineString', 'MultiLineString']).toContain(f.geometry.type)
      walk(f.geometry.coordinates, (x, y) => {
        expect(x).toBeGreaterThanOrEqual(43.125)
        expect(x).toBeLessThanOrEqual(43.185)
        expect(y).toBeGreaterThanOrEqual(11.53)
        expect(y).toBeLessThanOrEqual(11.625)
      })
    }
  })

  it('voirie classes are the 4 styled ones', () => {
    const known = new Set(['primaire', 'secondaire', 'tertiaire', 'locale'])
    for (const f of voirie.features) expect(known.has(String(f.properties['classe']))).toBe(true)
  })
})

// ── Découpage officiel admin_pol ──────────────────────────────────────────────

describe('admin_pol official quartiers and communes', () => {
  const q = asFC(QUARTIERS)
  const c = asFC(COMMUNES_ADMIN)

  it('91 quartiers over the 3 communes, 3 communes', () => {
    expect(q.features).toHaveLength(91)
    expect(c.features.map((f) => f.properties['nom']).sort()).toEqual(['Balbala', 'Boulaos', 'Ras-Dika'])
    const per: Record<string, number> = {}
    for (const f of q.features) per[String(f.properties['commune'])] = (per[String(f.properties['commune'])] ?? 0) + 1
    expect(per).toEqual({ Boulaos: 46, Balbala: 37, 'Ras-Dika': 8 })
  })

  it('quartier names are cleaned and include the centre (not covered by CERD)', () => {
    const noms = q.features.map((f) => String(f.properties['nom']))
    for (const n of ['Quartier 7', 'Plateau du Serpent', 'Centre Commercial et Administratif', 'Haramous']) expect(noms).toContain(n)
    for (const n of noms) {
      expect(n).not.toMatch(/'\s/)
      expect(n).not.toContain('Admnistratif')
    }
  })

  it('quartiers reach east of CERD Balbala coverage (lon > 43.14)', () => {
    let maxLon = 0
    function walk(x: unknown) { if (Array.isArray(x) && typeof x[0] === 'number') maxLon = Math.max(maxLon, x[0] as number); else if (Array.isArray(x)) x.forEach(walk) }
    q.features.forEach((f) => walk(f.geometry.coordinates))
    expect(maxLon).toBeGreaterThan(43.14)
  })
})
