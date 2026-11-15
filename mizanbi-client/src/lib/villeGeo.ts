import COMMUNES_GEO from '../data/cerd_communes.json'
import QUARTIERS_GEO from '../data/admin_quartiers.json'
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

// Emprise fixe : quartiers officiels (admin_pol) + communes CERD (Balbala) + voirie OSM du centre
export const VILLE_BOUNDS: Bounds = makeBounds([
  ...(QUARTIERS_GEO as unknown as { features: GeoFeature[] }).features,
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

export const COMMUNE_FILL: Record<string, string> = {
  'Ras-Dika': 'oklch(24% 0.05 230)',
  'Boulaos':  'oklch(22% 0.04 265)',
  'Balbala':  'oklch(21% 0.04 300)',
}

/** Libellé d'un quartier assez grand pour être affiché sans encombrer la carte. */
export function quartierLabel(nom: string, superficieHa: number): string | null {
  if (superficieHa < 6 || nom === 'Sans nom') return null
  return nom.length > 20 ? nom.slice(0, 19) + '…' : nom
}

/** Mer : fond uniforme de toute la carte (le polygone « ligne côtière » du levé, découpé par feuilles, n'est pas utilisé). */
export const SEA_FILL = 'oklch(30% 0.06 225)'
export const SEA_RECT = { x: -VILLE_PAD, y: -VILLE_PAD, width: VILLE_W + VILLE_PAD * 2, height: VILLE_BOUNDS.H + VILLE_PAD * 2 }

/** Terre hors levé : le coin sud-ouest du cadre (sud de Balbala, lon < 43,094 / lat < 11,522) est de la terre
 *  mais n'est couvert ni par les communes ni par le levé ; sans ce rectangle il apparaîtrait en mer.
 *  (Les limites régionales GADM ont été essayées : trop grossières, elles débordent en mer sur la côte est.) */
export const LAND_FILL = 'oklch(19% 0.03 290)'
export const LAND_PATCH = (() => {
  const x0 = -VILLE_PAD
  const x1 = px(43.105, VILLE_BOUNDS)
  const y0 = py(11.5445, VILLE_BOUNDS)
  const y1 = VILLE_BOUNDS.H + VILLE_PAD
  return { x: x0, y: y0, width: Math.max(0, x1 - x0), height: Math.max(0, y1 - y0) }
})()
