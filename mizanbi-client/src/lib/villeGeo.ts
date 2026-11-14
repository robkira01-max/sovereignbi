import COMMUNES_GEO from '../data/cerd_communes.json'
import OSM_VOIRIE_GEO from '../data/osm_centre_voirie.json'

export type Coord = [number, number]
type Rings = Coord[][]
export type GeoFeature = { type: 'Feature'; geometry: { type: string; coordinates: unknown }; properties: Record<string, unknown> }

export interface Bounds { x0: number; x1: number; y0: number; y1: number; sc: number; H: number }

export const VILLE_W = 700
export const VILLE_PAD = 10

export const OSM_ROAD_STYLE: Record<string, { color: string; w: number; label: string }> = {
  primaire:   { color: 'oklch(80% 0.12 200)', w: 1.2, label: 'Primaire' },
  secondaire: { color: 'oklch(68% 0.10 200)', w: 0.8, label: 'Secondaire' },
  tertiaire:  { color: 'oklch(58% 0.07 200)', w: 0.55, label: 'Tertiaire' },
  locale:     { color: 'oklch(45% 0.04 200)', w: 0.35, label: 'Locale' },
}

function walkCoords(c: unknown, cb: (pt: Coord) => void) {
  if (Array.isArray(c) && c.length >= 2 && typeof c[0] === 'number') cb(c as Coord)
  else if (Array.isArray(c)) c.forEach(x => walkCoords(x, cb))
}

export function makeBounds(features: GeoFeature[], W = VILLE_W): Bounds {
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9
  features.forEach(f => walkCoords(f.geometry.coordinates, ([x, y]) => {
    x0 = Math.min(x0, x); x1 = Math.max(x1, x)
    y0 = Math.min(y0, y); y1 = Math.max(y1, y)
  }))
  const k = Math.cos(((y0 + y1) / 2) * (Math.PI / 180))
  const sc = W / ((x1 - x0) * k)
  return { x0, x1, y0, y1, sc, H: (y1 - y0) * sc }
}

export function px(lon: number, b: Bounds) { return (lon - b.x0) * Math.cos(((b.y0 + b.y1) / 2) * Math.PI / 180) * b.sc }
export function py(lat: number, b: Bounds) { return (b.y1 - lat) * b.sc }

export function polygonPath(coords: unknown, b: Bounds): string {
  const rings: Rings = []
  if (Array.isArray(coords) && Array.isArray(coords[0]) && Array.isArray(coords[0][0])) {
    if (typeof coords[0][0][0] === 'number') rings.push(...(coords as Rings))
    else (coords as Rings[]).forEach(mp => rings.push(...mp))
  }
  return rings.map(ring =>
    'M' + ring.map(([x, y]) => `${px(x, b).toFixed(1)} ${py(y, b).toFixed(1)}`).join('L') + 'Z'
  ).join('')
}

export function linePath(coords: unknown, b: Bounds): string {
  if (!Array.isArray(coords) || coords.length === 0) return ''
  // LineString: [[lon,lat], ...] — MultiLineString: [[[lon,lat], ...], ...]
  const lines: Coord[][] = Array.isArray(coords[0][0])
    ? (coords as Coord[][])
    : [coords as Coord[]]
  return lines.map(pts =>
    'M' + pts.map(([x, y]) => `${px(x, b).toFixed(1)} ${py(y, b).toFixed(1)}`).join('L')
  ).join('')
}

export function centroidOfPolygon(coords: unknown): Coord {
  const rings: Rings = []
  if (Array.isArray(coords) && Array.isArray(coords[0]) && Array.isArray(coords[0][0])) {
    if (typeof coords[0][0][0] === 'number') rings.push(coords[0] as Rings[0])
    else rings.push((coords as Rings[])[0][0])
  }
  if (!rings.length) return [0, 0]
  const ring = rings[0]
  const xs = ring.map(p => p[0])
  const ys = ring.map(p => p[1])
  return [xs.reduce((a, b) => a + b, 0) / xs.length, ys.reduce((a, b) => a + b, 0) / ys.length]
}

// Emprise fixe : communes CERD (Balbala) + voirie OSM du centre
export const VILLE_BOUNDS: Bounds = makeBounds([
  ...(COMMUNES_GEO as unknown as { features: GeoFeature[] }).features,
  ...(OSM_VOIRIE_GEO as unknown as { features: GeoFeature[] }).features,
])

export const VILLE_VIEWBOX = `-${VILLE_PAD} -${VILLE_PAD} ${VILLE_W + VILLE_PAD * 2} ${VILLE_BOUNDS.H + VILLE_PAD * 2}`
export const VILLE_RATIO = `${VILLE_W + VILLE_PAD * 2} / ${VILLE_BOUNDS.H + VILLE_PAD * 2}`

export function projectVille(lon: number, lat: number): { x: number; y: number } {
  return { x: px(lon, VILLE_BOUNDS), y: py(lat, VILLE_BOUNDS) }
}

export function inVilleBounds(lon: number, lat: number): boolean {
  return lon >= VILLE_BOUNDS.x0 && lon <= VILLE_BOUNDS.x1 && lat >= VILLE_BOUNDS.y0 && lat <= VILLE_BOUNDS.y1
}
