import type { GeoFeature } from './villeGeo'

// Levé topographique CERD 1/2 500 (2014), servi à la demande par l'API (fichiers gzip) :
// jamais embarqué dans le client. Chaque couche = un id du catalogue géospatial.
export type TopoId = 'cerd_batiments' | 'cerd_routes' | 'cerd_hydro' | 'cerd_rail' | 'cerd_sites'

export interface TopoStyle { fill?: string; stroke?: string; width?: number; dash?: number[] }

export interface TopoLayerDef {
  id: TopoId
  label: string
  /** Ordre de dessin : sites < hydro < routes < bâtiments < rail. */
  order: number
  style: (p: Record<string, unknown>) => TopoStyle
}

export const BUILDING_CATS: Record<string, { label: string; color: string }> = {
  habitat:        { label: 'Habitat',                  color: '#94a3b8' },
  habitat_dur:    { label: 'Bâtiment en dur (étages)', color: '#cbd5e1' },
  education:      { label: 'Éducation',                color: '#60a5fa' },
  sante:          { label: 'Santé',                    color: '#f87171' },
  administration: { label: 'Administration',           color: '#22d3ee' },
  commerce:       { label: 'Commerce, hôtellerie',     color: '#fb923c' },
  religion:       { label: 'Culte',                    color: '#c084fc' },
  industrie:      { label: 'Industrie, entrepôts',     color: '#a3a3a3' },
  reseaux:        { label: 'Réseaux, énergie, eau',    color: '#facc15' },
  culture:        { label: 'Culture',                  color: '#34d399' },
  ruine:          { label: 'Ruines',                   color: '#64748b' },
}

const alpha = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${a})`
}

export const TOPO_LAYERS: TopoLayerDef[] = [
  {
    id: 'cerd_sites', label: 'Sites (cimetières, stades…)', order: 0,
    style: p => ({ fill: String(p.type) === 'Cimetière' ? 'rgba(167, 139, 250, 0.22)' : 'rgba(163, 230, 53, 0.10)', stroke: 'rgba(163, 230, 53, 0.25)', width: 0.3 }),
  },
  {
    id: 'cerd_hydro', label: 'Hydrographie', order: 1,
    style: () => ({ fill: 'rgba(56, 189, 248, 0.30)', stroke: 'rgba(56, 189, 248, 0.85)', width: 0.4 }),
  },
  {
    id: 'cerd_routes', label: 'Routes (CERD 2014)', order: 2,
    style: p => (p.revetue === 'oui'
      ? { fill: 'rgba(148, 163, 184, 0.40)', stroke: 'rgba(203, 213, 225, 0.55)', width: 0.3 }
      : { fill: 'rgba(180, 140, 90, 0.28)', stroke: 'rgba(180, 140, 90, 0.45)', width: 0.3 }),
  },
  {
    id: 'cerd_batiments', label: 'Bâtiments (CERD 2014)', order: 3,
    style: p => {
      const cat = BUILDING_CATS[String(p.cat)]
      const color = cat?.color ?? '#94a3b8'
      const habitat = p.cat === 'habitat' || p.cat === 'habitat_dur' || p.cat === 'ruine'
      return { fill: alpha(color, habitat ? 0.30 : 0.80), stroke: alpha(color, habitat ? 0.55 : 1), width: 0.25 }
    },
  },
  {
    id: 'cerd_rail', label: 'Voie ferrée', order: 4,
    style: () => ({ stroke: '#fde68a', width: 0.9, dash: [3, 2] }),
  },
]

export const TOPO_BY_ID: Record<TopoId, TopoLayerDef> = Object.fromEntries(TOPO_LAYERS.map(l => [l.id, l])) as Record<TopoId, TopoLayerDef>

export type TopoStatus = GeoFeature[] | 'loading' | 'error' | undefined

/** Clé de regroupement : les entités de même style sont tracées en un seul chemin (un fill/stroke par groupe). */
export function styleKey(s: TopoStyle): string {
  return `${s.fill ?? ''}|${s.stroke ?? ''}|${s.width ?? 0}|${(s.dash ?? []).join(',')}`
}

export function groupByStyle(features: GeoFeature[], styleOf: TopoLayerDef['style']): Map<string, { style: TopoStyle; features: GeoFeature[] }> {
  const groups = new Map<string, { style: TopoStyle; features: GeoFeature[] }>()
  for (const f of features) {
    const s = styleOf(f.properties)
    const k = styleKey(s)
    const g = groups.get(k)
    if (g) g.features.push(f)
    else groups.set(k, { style: s, features: [f] })
  }
  return groups
}
