import geojson from '../data/dj_adm1.json'
import { REGIONS } from '../data/demo'

export interface GeoShape {
  name: string
  key: string
  d: string
  x: number // centroid x in viewBox units
  y: number // centroid y in viewBox units
  unemployment: number | null
}

export interface GeoMap {
  shapes: GeoShape[]
  view: string
  ratio: string
  w: number
  h: number
}

type Position = [number, number]
type Ring = Position[]
type PolygonCoords = Ring[]

function polys(geometry: { type: string; coordinates: unknown }): PolygonCoords[] {
  const coords = geometry.coordinates as number[][][] | number[][][][]
  // A Polygon is one list of rings; a MultiPolygon is a list of polygons.
  if (geometry.type === 'Polygon') return [coords as PolygonCoords]
  return coords as PolygonCoords[]
}

// P-029 — projection lon/lat <-> coordonnées de la carte SVG de référence
// (mêmes formules que buildDjiboutiMap : équirectangulaire, k = cos(lat moy.)).
// La carte de référence est Djibouti ADM1 (geoBoundaries, licence ouverte).
export interface LonLatBounds { x0: number; x1: number; y0: number; y1: number; k: number; sc: number }

export function djiboutiBounds(): LonLatBounds {
  const features = (geojson as unknown as { features: { geometry: { coordinates: unknown } }[] }).features
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9
  const walk = (c: unknown) => {
    if (Array.isArray(c) && typeof c[0] === 'number') {
      const [x, y] = c as [number, number]
      x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y)
    } else if (Array.isArray(c)) { c.forEach(walk) }
  }
  features.forEach((f) => walk(f.geometry.coordinates))
  const k = Math.cos(((y0 + y1) / 2) * (Math.PI / 180))
  const sc = 300 / ((x1 - x0) * k)
  return { x0, x1, y0, y1, k, sc }
}

/** lon/lat -> coordonnées viewBox (P, Q) de la carte de référence. */
export function projectLonLat(lon: number, lat: number, b: LonLatBounds = djiboutiBounds()): { x: number; y: number } {
  return { x: (lon - b.x0) * b.k * b.sc, y: (b.y1 - lat) * b.sc }
}

/** Coordonnées viewBox -> lon/lat (clic sur la carte de référence). */
export function unprojectView(x: number, y: number, b: LonLatBounds = djiboutiBounds()): { lon: number; lat: number } {
  return { lon: b.x0 + x / (b.k * b.sc), lat: b.y1 - y / b.sc }
}

/** La cible est-elle dans l'emprise de la carte de référence Djibouti ? */
export function inDjiboutiBounds(lon: number, lat: number, b: LonLatBounds = djiboutiBounds()): boolean {
  return lon >= b.x0 - 0.5 && lon <= b.x1 + 0.5 && lat >= b.y0 - 0.5 && lat <= b.y1 + 0.5
}

export function buildDjiboutiMap(): GeoMap {
  const features = (geojson as unknown as { features: { properties: { shapeName: string }; geometry: { type: string; coordinates: unknown } }[] }).features
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9
  const walk = (c: unknown) => {
    if (Array.isArray(c) && typeof c[0] === 'number') {
      const [x, y] = c as [number, number]
      x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y)
    } else if (Array.isArray(c)) {
      c.forEach(walk)
    }
  }
  features.forEach((f) => walk(f.geometry.coordinates))
  const k = Math.cos(((y0 + y1) / 2) * (Math.PI / 180))
  const sc = 300 / ((x1 - x0) * k)
  const W = 300
  const H = (y1 - y0) * sc
  const P = (x: number) => (x - x0) * k * sc
  const Q = (y: number) => (y1 - y) * sc
  const norm = (n: string) => n.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()

  const shapes: GeoShape[] = features.map((f) => {
    const name = f.properties.shapeName
    const region = REGIONS.find((r) => norm(r.name).startsWith(norm(name).slice(0, 4)) || norm(name).startsWith(norm(r.name).slice(0, 4)))
    let area = -1
    let cx = 0
    let cy = 0
    const d = polys(f.geometry)
      .map((poly) => {
        poly.forEach((ring, i) => {
          if (i === 0) {
            let mx0 = 1e9, mx1 = -1e9, my0 = 1e9, my1 = -1e9
            ring.forEach(([x, y]) => { mx0 = Math.min(mx0, x); mx1 = Math.max(mx1, x); my0 = Math.min(my0, y); my1 = Math.max(my1, y) })
            const a = (mx1 - mx0) * (my1 - my0)
            if (a > area) { area = a; cx = P((mx0 + mx1) / 2); cy = Q((my0 + my1) / 2) }
          }
        })
        return poly.map((ring) => 'M' + ring.map(([x, y]) => `${P(x).toFixed(1)} ${Q(y).toFixed(1)}`).join('L') + 'Z').join('')
      })
      .join('')
    return { name, key: norm(name), d, x: cx, y: cy, unemployment: region ? region.unemployment : null }
  })
  return { shapes, view: `-6 -6 ${W + 12} ${H + 12}`, ratio: `${W + 12} / ${H + 12}`, w: W + 12, h: H + 12 }
}

// P-028 : compatibilité conservée — la couleur vient désormais de l'échelle
// calculée sur les valeurs affichées (voir theme.ts, colorForValue).
// Ancienne rampe fixe 21–30 % remplacée par min/max réels des 6 régions.
import { colorForValue, currentTheme, scaleFor } from './theme'

export function fillForRate(rate: number | null): string {
  if (rate === null) return 'oklch(30% 0.04 265)'
  const scale = scaleFor(REGIONS.map((r) => r.unemployment), currentTheme(), '%')
  return colorForValue(rate, scale)
}
