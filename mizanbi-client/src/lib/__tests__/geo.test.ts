// Régression : toutes les régions ADM1 sont des Polygon ; traiter leurs coordonnées comme
// un MultiPolygon faisait planter buildDjiboutiMap (et donc toute la page d'accueil).
import { describe, expect, it } from 'vitest'
import { buildDjiboutiMap } from '../geo'

describe('buildDjiboutiMap', () => {
  const map = buildDjiboutiMap()

  it('builds one shape per region with a drawable path and a centroid', () => {
    expect(map.shapes).toHaveLength(6)
    for (const s of map.shapes) {
      expect(s.d.startsWith('M'), s.name).toBe(true)
      expect(s.d).not.toContain('NaN')
      expect(Number.isFinite(s.x) && Number.isFinite(s.y), s.name).toBe(true)
    }
  })

  it('matches every region to demo unemployment data', () => {
    expect(map.shapes.every((s) => s.unemployment !== null)).toBe(true)
  })

  it('has a finite viewBox', () => {
    expect(map.view).not.toContain('NaN')
    expect(map.h).toBeGreaterThan(0)
  })
})
