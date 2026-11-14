import { describe, it, expect } from 'vitest'
import { VILLE_BOUNDS, VILLE_W, inVilleBounds, projectVille, linePath, polygonPath } from '../villeGeo'
import SANTE from '../../data/dj_structures_sante.json'
import CERD_ECOLES from '../../data/cerd_ecoles.json'

type Pt = { geometry: { coordinates: [number, number] }; properties: Record<string, unknown> }

describe('villeGeo frame', () => {
  it('covers Balbala (CERD) and the centre (OSM) in one frame', () => {
    expect(VILLE_BOUNDS.x0).toBeLessThan(43.07)
    expect(VILLE_BOUNDS.x1).toBeGreaterThan(43.17)
    expect(VILLE_BOUNDS.y0).toBeLessThan(11.54)
    expect(VILLE_BOUNDS.y1).toBeGreaterThan(11.62)
  })

  it('projects frame corners inside the viewBox', () => {
    const tl = projectVille(VILLE_BOUNDS.x0, VILLE_BOUNDS.y1)
    const br = projectVille(VILLE_BOUNDS.x1, VILLE_BOUNDS.y0)
    expect(tl.x).toBeCloseTo(0, 5)
    expect(tl.y).toBeCloseTo(0, 5)
    expect(br.x).toBeCloseTo(VILLE_W, 3)
    expect(br.y).toBeCloseTo(VILLE_BOUNDS.H, 3)
  })

  it('inVilleBounds: Peltier hospital in, PK20 out', () => {
    expect(inVilleBounds(43.1535, 11.6083)).toBe(true)
    expect(inVilleBounds(43.0103, 11.5526)).toBe(false)
  })

  it('health: all Djibouti-ville structures but PK20 fall inside the frame', () => {
    const ville = (SANTE as unknown as { features: Pt[] }).features.filter(f => f.properties.region === 'djibouti_ville')
    const out = ville.filter(f => !inVilleBounds(f.geometry.coordinates[0], f.geometry.coordinates[1]))
    expect(ville).toHaveLength(22)
    expect(out.map(f => String(f.properties.structure))).toEqual(['CSC-PK20'])
  })

  it('CERD schools are all inside the frame', () => {
    const feats = (CERD_ECOLES as unknown as { features: { geometry: { coordinates: number[][][] } }[] }).features
    for (const f of feats) {
      const [lon, lat] = f.geometry.coordinates[0][0]
      expect(inVilleBounds(lon, lat)).toBe(true)
    }
  })
})

describe('villeGeo paths', () => {
  it('linePath handles LineString and MultiLineString identically', () => {
    const ls = [[43.1, 11.56], [43.11, 11.57]]
    expect(linePath([ls], VILLE_BOUNDS)).toBe(linePath(ls, VILLE_BOUNDS))
    expect(linePath(ls, VILLE_BOUNDS)).not.toMatch(/NaN/)
  })
  it('polygonPath closes rings', () => {
    const d = polygonPath([[[43.1, 11.56], [43.11, 11.56], [43.11, 11.57], [43.1, 11.56]]], VILLE_BOUNDS)
    expect(d.endsWith('Z')).toBe(true)
  })
})
