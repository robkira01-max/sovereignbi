import { describe, it, expect } from 'vitest'
import ATTR from '../../data/geo_attribution.json'

// Les ids déclarés par les pieds de carte GeoSources doivent exister dans
// l'attribution générée depuis data/geo/catalog.yaml.
const USED = [
  'admin_communes', 'admin_quartiers', 'cerd_secteurs_adressage', 'cerd_typologies_urbaines',
  'cerd_voirie', 'cerd_equipements_sociaux', 'cerd_equipements_scolaires', 'cerd_lignes_bus',
  'cerd_terminus_bus', 'osm_centre_voirie', 'dj_structures_sante', 'dj_adm1', 'osm_batiments',
]

describe('geo_attribution.json (généré depuis catalog.yaml)', () => {
  const attr = ATTR as Record<string, { name: string; provider: string; license: string }>

  it('contient tous les ids utilisés par les cartes', () => {
    for (const id of USED) {
      expect(attr[id], id).toBeDefined()
      expect(attr[id].name.length).toBeGreaterThan(0)
      expect(attr[id].provider.length).toBeGreaterThan(0)
      expect(attr[id].license.length).toBeGreaterThan(0)
    }
  })

  it('attribue admin_pol au CERD et les routes du centre à OSM', () => {
    expect(attr['admin_quartiers'].provider).toBe('CERD')
    expect(attr['osm_centre_voirie'].provider).toContain('OpenStreetMap')
  })
})
