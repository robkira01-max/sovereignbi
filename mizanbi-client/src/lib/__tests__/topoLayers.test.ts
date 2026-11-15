import { describe, it, expect } from 'vitest'
import { BUILDING_CATS, TOPO_LAYERS, groupByStyle, styleKey, type TopoId } from '../topoLayers'
import ATTR from '../../data/geo_attribution.json'
import type { GeoFeature } from '../villeGeo'

const feat = (properties: Record<string, unknown>): GeoFeature => ({
  type: 'Feature', geometry: { type: 'Polygon', coordinates: [[[43.1, 11.5], [43.11, 11.5], [43.11, 11.51], [43.1, 11.5]]] }, properties,
})

describe('CERD topographic layer styles', () => {
  it('every layer is a catalogue layer with CERD attribution', () => {
    const attr = ATTR as Record<string, { provider: string }>
    for (const l of TOPO_LAYERS) {
      expect(attr[l.id], l.id).toBeDefined()
      expect(attr[l.id].provider).toContain('CERD')
    }
  })

  it('draw order is strictly increasing and unique (buildings above roads, rail on top)', () => {
    const order = TOPO_LAYERS.map(l => l.order)
    expect(new Set(order).size).toBe(order.length)
    expect([...order].sort((a, b) => a - b)).toEqual(order)
    const ids = TOPO_LAYERS.map(l => l.id as TopoId)
    expect(ids.indexOf('cerd_batiments')).toBeGreaterThan(ids.indexOf('cerd_routes'))
    expect(ids[ids.length - 1]).toBe('cerd_rail')
  })

  it('public-service buildings are more opaque than housing', () => {
    const b = TOPO_LAYERS.find(l => l.id === 'cerd_batiments')!
    const op = (s: string | undefined) => Number(s?.match(/,\s*([0-9.]+)\)$/)?.[1])
    expect(op(b.style({ cat: 'sante' }).fill)).toBeGreaterThan(op(b.style({ cat: 'habitat' }).fill))
  })

  it('every building category used by the converter has a legend entry', () => {
    for (const c of ['habitat', 'habitat_dur', 'education', 'sante', 'administration', 'commerce', 'religion', 'industrie', 'reseaux', 'culture', 'ruine']) {
      expect(BUILDING_CATS[c], c).toBeDefined()
    }
  })

  it('paved roads are styled differently from unpaved ones', () => {
    const r = TOPO_LAYERS.find(l => l.id === 'cerd_routes')!
    expect(styleKey(r.style({ revetue: 'oui' }))).not.toBe(styleKey(r.style({ revetue: 'non' })))
  })

  it('groupByStyle batches features sharing a style (one canvas path per group)', () => {
    const b = TOPO_LAYERS.find(l => l.id === 'cerd_batiments')!
    const groups = groupByStyle([feat({ cat: 'habitat' }), feat({ cat: 'habitat' }), feat({ cat: 'sante' })], b.style)
    expect(groups.size).toBe(2)
    expect([...groups.values()].map(g => g.features.length).sort()).toEqual([1, 2])
  })
})
