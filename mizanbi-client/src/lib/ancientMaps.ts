// P-029 — Cartes anciennes scannées : géoréférencement côté client, hors ligne.
// Principe : l'utilisateur place des points de contrôle (un repère sur le scan
// + ses coordonnées lon/lat). Une transformation affine (3 points exacts,
// 4+ points par moindres carrés) cale le scan sur la carte de référence.
// Les contours d'origine sont préservés : rien n'est retracé, le scan est
// affiché tel quel, en couche par-dessus la carte de référence.
// Limites : l'affine ne corrige pas les déformations du papier ni les
// projections anciennes très différentes ; 4+ points bien répartis conseillés.
// Aucun envoi serveur : fichiers et métadonnées restent sur la machine.

export interface ControlPoint {
  id: string
  /** Coordonnées en pixels dans l'image source (scan). */
  sx: number
  sy: number
  /** Coordonnées géographiques de référence. */
  lon: number
  lat: number
  label?: string
}

export interface AncientMapMeta {
  id: string
  title: string
  year: string
  source: string
  zone: string
  scale: string
  notes: string
  fileName: string
  /** Image du scan, data URL JPEG compressée (max ~1600 px). */
  image: string
  imgWidth: number
  imgHeight: number
  points: ControlPoint[]
  createdAt: string
  updatedAt: string
  demo?: boolean
  /** Nombre de pages du PDF d'origine (1 pour une image). Page rendue = 1 par défaut. */
  pdfPages?: number
  pdfPage?: number
}

export interface Affine {
  a: number; b: number; c: number
  d: number; e: number; f: number
}

export interface FitResult {
  affine: Affine | null
  /** Erreur résiduelle par point, en km (approx., 111 km / degré). */
  residualsKm: { id: string; km: number }[]
  rmsKm: number
  maxKm: number
  /** Points presque alignés (aire du triangle trop petite) : affine non fiable. */
  collinear: boolean
  /** Déterminant proche de 0 : transformation dégénérée. */
  degenerate: boolean
}

const STORAGE_KEY = 'mizan_ancient_maps_v1'

export const REFERENCE_PLACES: { name: string; lon: number; lat: number }[] = [
  { name: 'Djibouti-ville', lon: 43.15, lat: 11.59 },
  { name: 'Tadjourah', lon: 42.88, lat: 11.78 },
  { name: 'Obock', lon: 43.29, lat: 11.97 },
  { name: 'Ali Sabieh', lon: 42.71, lat: 11.16 },
  { name: 'Dikhil', lon: 42.38, lat: 11.52 },
  { name: 'Arta', lon: 42.85, lat: 11.53 },
]

export function uid(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

// --- Résolution d'un système linéaire 3x3 (élimination de Gauss) ---
function solve3(m: number[][], rhs: number[]): number[] | null {
  const a = m.map((row, i) => [...row, rhs[i]])
  for (let col = 0; col < 3; col++) {
    let piv = col
    for (let r = col + 1; r < 3; r++) if (Math.abs(a[r][col]) > Math.abs(a[piv][col])) piv = r
    if (Math.abs(a[piv][col]) < 1e-12) return null
    ;[a[col], a[piv]] = [a[piv], a[col]]
    for (let r = 0; r < 3; r++) {
      if (r === col) continue
      const f = a[r][col] / a[col][col]
      for (let c = col; c < 4; c++) a[r][c] -= f * a[col][c]
    }
  }
  return a.map((row, i) => row[3] / row[i])
}

/** Moindres carrés : résout [u v 1] * coef = cible, pour x puis pour y. */
function leastSquares(points: ControlPoint[], getTarget: (p: ControlPoint) => number): number[] | null {
  // Équations normales : (AᵀA) coef = Aᵀb
  const ata = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
  const atb = [0, 0, 0]
  for (const p of points) {
    const row = [p.sx, p.sy, 1]
    const b = getTarget(p)
    for (let i = 0; i < 3; i++) {
      atb[i] += row[i] * b
      for (let j = 0; j < 3; j++) ata[i][j] += row[i] * row[j]
    }
  }
  return solve3(ata, atb)
}

export function fitAffine(points: ControlPoint[]): FitResult {
  const empty: FitResult = { affine: null, residualsKm: [], rmsKm: 0, maxKm: 0, collinear: false, degenerate: false }
  if (points.length < 3) return empty
  // Aire du triangle des 3 premiers points (source) : presque alignés ?
  const [p1, p2, p3] = points
  const area = Math.abs((p2.sx - p1.sx) * (p3.sy - p1.sy) - (p3.sx - p1.sx) * (p2.sy - p1.sy)) / 2
  // Aire relative à l'emprise des points : < 1 % = quasi alignés.
  const xs = points.map((p) => p.sx); const ys = points.map((p) => p.sy)
  const span = (Math.max(...xs) - Math.min(...xs)) * (Math.max(...ys) - Math.min(...ys))
  const collinear = span > 0 && area / span < 0.01
  const cx = leastSquares(points, (p) => p.lon)
  const cy = leastSquares(points, (p) => p.lat)
  if (!cx || !cy) return { ...empty, collinear, degenerate: true }
  const affine: Affine = { a: cx[0], b: cx[1], c: cx[2], d: cy[0], e: cy[1], f: cy[2] }
  const det = affine.a * affine.e - affine.b * affine.d
  if (Math.abs(det) < 1e-12) return { ...empty, collinear, degenerate: true }
  const meanLat = points.reduce((s, p) => s + p.lat, 0) / points.length
  const kx = 111.32 * Math.cos((meanLat * Math.PI) / 180) // km par degré de longitude
  const ky = 111.32 // km par degré de latitude
  const residualsKm = points.map((p) => {
    const plon = affine.a * p.sx + affine.b * p.sy + affine.c
    const plat = affine.d * p.sx + affine.e * p.sy + affine.f
    const km = Math.hypot((plon - p.lon) * kx, (plat - p.lat) * ky)
    return { id: p.id, km }
  })
  const rmsKm = Math.sqrt(residualsKm.reduce((s, r) => s + r.km * r.km, 0) / residualsKm.length)
  const maxKm = Math.max(...residualsKm.map((r) => r.km))
  return { affine, residualsKm, rmsKm, maxKm, collinear, degenerate: false }
}

export function applyAffine(a: Affine, sx: number, sy: number): { lon: number; lat: number } {
  return { lon: a.a * sx + a.b * sy + a.c, lat: a.d * sx + a.e * sy + a.f }
}

// --- Images : lecture + compression côté client ---
export function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader()
    r.onload = () => resolve(String(r.result))
    r.onerror = () => reject(new Error('Lecture du fichier impossible'))
    r.readAsDataURL(file)
  })
}

export function imageSize(dataUrl: string): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight })
    img.onerror = () => reject(new Error('Image illisible'))
    img.src = dataUrl
  })
}

/** Compresse un scan en JPEG (max 1600 px de côté) pour tenir dans localStorage. */
export function compressImage(dataUrl: string, maxDim = 1600): Promise<{ dataUrl: string; width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const k = Math.min(1, maxDim / Math.max(img.naturalWidth, img.naturalHeight))
      const w = Math.max(1, Math.round(img.naturalWidth * k))
      const h = Math.max(1, Math.round(img.naturalHeight * k))
      const canvas = document.createElement('canvas')
      canvas.width = w; canvas.height = h
      const ctx = canvas.getContext('2d')
      if (!ctx) { reject(new Error('Canvas indisponible')); return }
      ctx.fillStyle = '#ffffff'; ctx.fillRect(0, 0, w, h)
      ctx.drawImage(img, 0, 0, w, h)
      resolve({ dataUrl: canvas.toDataURL('image/jpeg', 0.85), width: w, height: h })
    }
    img.onerror = () => reject(new Error('Image illisible'))
    img.src = dataUrl
  })
}

// --- PDF : rendu de la page choisie (1 par défaut) en image, 100 % local ---
// pdf.js est chargé à la demande (import dynamique) pour ne pas gonfler le
// bundle principal ; le worker est embarqué localement, aucune dépendance CDN.
export async function renderPdfPage(file: File, pageNum = 1): Promise<{ dataUrl: string; width: number; height: number; pages: number }> {
  const pdfjs = await import('pdfjs-dist')
  const { default: workerUrl } = await import('pdfjs-dist/build/pdf.worker.min.mjs?url')
  pdfjs.GlobalWorkerOptions.workerSrc = workerUrl
  const buf = await file.arrayBuffer()
  const pdf = await pdfjs.getDocument({ data: buf }).promise
  const page = await pdf.getPage(Math.min(Math.max(1, pageNum), pdf.numPages))
  const viewport = page.getViewport({ scale: 1 })
  const scale = Math.min(2.5, 2000 / Math.max(viewport.width, viewport.height))
  const vp = page.getViewport({ scale })
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(vp.width); canvas.height = Math.round(vp.height)
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Canvas indisponible')
  await page.render({ canvasContext: ctx, viewport: vp }).promise
  const dataUrl = canvas.toDataURL('image/jpeg', 0.9)
  return { dataUrl, width: canvas.width, height: canvas.height, pages: pdf.numPages }
}

// --- Stockage local (localStorage, métadonnées + points + image compressée) ---
export function loadMaps(): AncientMapMeta[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as AncientMapMeta[]
    return Array.isArray(parsed) ? parsed : []
  } catch { return [] }
}

export function saveMaps(maps: AncientMapMeta[]): { ok: boolean; error?: string } {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(maps))
    return { ok: true }
  } catch {
    return { ok: false, error: 'Stockage local plein : image trop lourde. La fiche est gardée sans l’image (réimportez le scan pour la revoir).' }
  }
}

export function exportMapJson(map: AncientMapMeta): string {
  const { image, ...fiche } = map
  return JSON.stringify({ ...fiche, imageIncluse: false, note: 'Image du scan non incluse dans cet export (conservée localement).' }, null, 2)
}

// --- Carte d'exemple DÉMO (schéma, pas une vraie carte ancienne) ---
export function demoMapImage(): { dataUrl: string; width: number; height: number } {
  const w = 1200; const h = 800
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
<rect width="${w}" height="${h}" fill="#e8dcc0"/>
<rect x="20" y="20" width="${w - 40}" height="${h - 40}" fill="none" stroke="#8a6d3b" stroke-width="3"/>
<text x="600" y="90" text-anchor="middle" font-family="serif" font-size="44" fill="#5a3e1b">DJIBOUTI — CARTE ANCIENNE (DÉMO)</text>
<text x="600" y="130" text-anchor="middle" font-family="serif" font-size="22" fill="#7a5a2e">Schéma de démonstration — pas une vraie carte ancienne</text>
${Array.from({ length: 11 }, (_, i) => `<line x1="${100 + i * 100}" y1="160" x2="${100 + i * 100}" y2="740" stroke="#b09a6a" stroke-width="1"/>`).join('')}
${Array.from({ length: 6 }, (_, i) => `<line x1="60" y1="${180 + i * 110}" x2="1140" y2="${180 + i * 110}" stroke="#b09a6a" stroke-width="1"/>`).join('')}
<path d="M80 700 Q 300 520 520 560 T 900 420 T 1140 300" fill="none" stroke="#4a7a9a" stroke-width="10" stroke-linecap="round"/>
<path d="M150 300 Q 400 380 650 300 T 1050 380" fill="none" stroke="#8a6d3b" stroke-width="2" stroke-dasharray="8 6"/>
<text x="180" y="690" font-family="serif" font-size="24" fill="#4a7a9a">Golfe de Tadjourah</text>
<circle cx="300" cy="500" r="14" fill="#b03030"/><text x="322" y="508" font-family="sans-serif" font-size="24" font-weight="bold" fill="#5a1a1a">Djibouti-ville</text>
<circle cx="700" cy="300" r="14" fill="#b03030"/><text x="722" y="308" font-family="sans-serif" font-size="24" font-weight="bold" fill="#5a1a1a">Tadjourah</text>
<circle cx="950" cy="550" r="14" fill="#b03030"/><text x="972" y="558" font-family="sans-serif" font-size="24" font-weight="bold" fill="#5a1a1a">Obock</text>
<text x="600" y="770" text-anchor="middle" font-family="serif" font-size="18" fill="#7a5a2e">Échelle inconnue — 3 repères fictifs pour tester le géoréférencement</text>
</svg>`
  return { dataUrl: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`, width: w, height: h }
}

export function demoMap(): AncientMapMeta {
  const img = demoMapImage()
  const now = new Date().toISOString()
  return {
    id: `demo-${uid()}`,
    title: 'Exemple démo — carte ancienne de Djibouti (schéma)',
    year: '—',
    source: 'Schéma généré pour la démo — pas une vraie carte ancienne',
    zone: 'Djibouti-ville, Tadjourah, Obock',
    scale: 'Inconnue',
    notes: 'Exemple pour tester le géoréférencement sans scan. Les 3 repères sont fictifs : ne pas utiliser pour une vraie carte.',
    fileName: 'demo-ancienne-djibouti.svg',
    image: img.dataUrl,
    imgWidth: img.width,
    imgHeight: img.height,
    points: [
      { id: uid(), sx: 300, sy: 500, lon: 43.15, lat: 11.59, label: 'Djibouti-ville' },
      { id: uid(), sx: 700, sy: 300, lon: 42.88, lat: 11.78, label: 'Tadjourah' },
      { id: uid(), sx: 950, sy: 550, lon: 43.29, lat: 11.97, label: 'Obock' },
    ],
    createdAt: now,
    updatedAt: now,
    demo: true,
  }
}
