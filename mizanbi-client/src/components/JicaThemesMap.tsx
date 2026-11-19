import { useEffect, useMemo, useState } from 'react'
import { apiFetch, isApiConfigured } from '../lib/api'
import GeoSources from './GeoSources'

// Couches thématiques JICA (hydrogéologie, climat, points d'eau) servies par /api/v1/geo/dj/{id}.
// Licence non confirmée : usage interne, avertissement affiché en permanence.

type Geom = { type: string; coordinates: unknown }
interface Feat { geometry: Geom; properties: Record<string, string | number | null> }

interface LayerDef { id: string; label: string; valueKey: string; labelKey: string; unit?: string }
const L = (id: string, label: string, valueKey = 'source_file', labelKey = valueKey, unit?: string): LayerDef => ({ id, label, valueKey, labelKey, unit })

// Les noms de couches et de classes sont PROVISOIRES (légendes de la JICA attendues) : les classes
// portent le nom du fichier d'origine tant que la JICA n'a pas fourni sa nomenclature.
export const JICA_GROUPS: { id: string; label: string; layers: LayerDef[] }[] = [
  { id: 'hydro', label: 'Hydrogéologie et climat', layers: [
    L('jica_pluie_moyenne', 'Pluie moyenne annuelle', 'Pluiemoyen', 'Pluiemoyen', 'mm'),
    L('jica_pluie_mai', 'Pluie moyenne — mai', 'Pluiemoyen', 'Pluiemoyen', 'mm'),
    L('jica_etp', 'ETP', 'ETP'), L('jica_etr', 'ETR', 'ETR'),
    L('jica_zones_climatiques', 'Zones climatiques', 'zoneclimat'),
    L('jica_systemes_aquiferes', 'Systèmes aquifères', 'SystAquif', 'Name'),
    L('jica_debit_aquiferes', 'Débit des aquifères', 'Debit', 'Name'),
    L('jica_points_eau', "Points d'eau", 'region', 'nom'),
    L('jica_formation_points_eau', "Formations de points d'eau", 'typepoint'),
    L('jica_zones_hydrogeo', 'Zones prioritaires / résistivité / recharge'),
    L('jica_alerte_crue', 'Stations d’alerte de crue'),
  ] },
  { id: 'geo', label: 'Géologie', layers: [
    L('jica_geologie_formations', 'Formations'), L('jica_failles', 'Failles'),
    L('jica_failles_favorables', 'Failles favorables'), L('jica_fracturation', 'Fracturation'),
    L('jica_sismicite', 'Sismicité', 'source_file', 'MAGCOR'),
  ] },
  { id: 'topo', label: 'Topographie et eau', layers: [
    L('jica_altimetrie', 'Altimétrie'), L('jica_points_cotes', 'Points cotés'),
    L('jica_hydrographie', 'Réseau hydrographique'), L('jica_plans_eau', 'Lacs, sebkhas, nappes saumâtres'),
  ] },
  { id: 'veg', label: 'Végétation et sols', layers: [
    L('jica_vegetation_regions', 'Végétation par région'), L('jica_agropastoral', 'Unités agropastorales'),
    L('jica_agropastoral_composite', 'Agropastoral — points', 'source_file', 'nom'),
    L('jica_forets', 'Forêts'), L('jica_sols_regions', 'Sols (Arta, Ali Sabieh)', 'Descriptio'),
  ] },
  { id: 'reseau', label: 'Réseau, localités, mer', layers: [
    L('jica_reseau_routier', 'Routes, pistes, rail'), L('jica_localites', 'Villages et localités', 'source_file', 'name'),
    L('jica_bathymetrie', 'Bathymétrie', 'source_file', 'bathy'), L('jica_iles', 'Îles'), L('jica_cote_frontieres', 'Côte et frontières'),
  ] },
]
export const JICA_LAYERS: LayerDef[] = JICA_GROUPS.flatMap(g => g.layers)

const W = 640
const LON0 = 41.7, LON1 = 43.5, LAT0 = 10.9, LAT1 = 12.8
const COS = Math.cos(((LAT0 + LAT1) / 2) * Math.PI / 180)
const H = Math.round(W * ((LAT1 - LAT0) / ((LON1 - LON0) * COS)))
const px = (lon: number, lat: number): [number, number] => [((lon - LON0) / (LON1 - LON0)) * W, ((LAT1 - lat) / (LAT1 - LAT0)) * H]
const pt = ([lon, lat]: number[], i: number) => { const [x, y] = px(lon, lat); return `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}` }

const line = (c: number[][]) => c.map(pt).join('')
const ring = (c: number[][]) => line(c) + 'Z'
function geomPath(g: Geom): string {
  const c = g.coordinates as never
  switch (g.type) {
    case 'Polygon': return (c as number[][][]).map(ring).join('')
    case 'MultiPolygon': return (c as number[][][][]).map(p => p.map(ring).join('')).join('')
    case 'LineString': return line(c as number[][])
    case 'MultiLineString': return (c as number[][][]).map(line).join('')
    case 'Point': { const [x, y] = px(...(c as [number, number])); return `M${x.toFixed(1)} ${y.toFixed(1)}h0` }
    case 'MultiPoint': return (c as number[][]).map(p => { const [x, y] = px(p[0], p[1]); return `M${x.toFixed(1)} ${y.toFixed(1)}h0` }).join('')
    default: return ''
  }
}
const kindOf = (g: Geom): 'poly' | 'line' | 'point' => /Polygon/.test(g.type) ? 'poly' : /Line/.test(g.type) ? 'line' : 'point'

// Couleurs : angle d'or en HSL, assez distinctes même pour ~30 classes ; classes numériques triées, « — » en dernier.
const colorAt = (i: number) => `hsl(${(i * 137.508) % 360} 70% 58%)`

export function classColors(values: (string | number | null)[]): Map<string, string> {
  const uniq = [...new Set(values.map(v => String(v ?? '—')))]
  const nums = uniq.every(u => u === '—' || !isNaN(Number(u)))
  const rank = (u: string) => (u === '—' ? 1 : 0)       // « — » (valeur absente) toujours en dernier
  uniq.sort((a, b) => rank(a) - rank(b) || (nums ? Number(a) - Number(b) : a.localeCompare(b)))
  return new Map(uniq.map((u, i) => [u, colorAt(i)]))
}

export default function JicaThemesMap() {
  const [group, setGroup] = useState(JICA_GROUPS[0])
  const [layer, setLayer] = useState<LayerDef>(JICA_GROUPS[0].layers[0])
  const [feats, setFeats] = useState<Feat[] | 'loading' | 'error'>('loading')

  useEffect(() => {
    if (!isApiConfigured()) { setFeats('error'); return }
    let alive = true
    setFeats('loading')
    apiFetch(`/api/v1/geo/dj/${layer.id}`).then(r => r.json())
      .then(fc => { if (alive) setFeats((fc as { features: Feat[] }).features) })
      .catch(() => { if (alive) setFeats('error') })
    return () => { alive = false }
  }, [layer])

  // Un seul <path> par classe : 10 000 lignes restent fluides.
  const drawn = useMemo(() => {
    if (!Array.isArray(feats)) return null
    const colors = classColors(feats.map(f => f.properties[layer.valueKey]))
    const by = new Map<string, { d: string; n: number; kind: 'poly' | 'line' | 'point' }>()
    for (const f of feats) {
      const k = String(f.properties[layer.valueKey] ?? '—')
      const e = by.get(k) ?? { d: '', n: 0, kind: kindOf(f.geometry) }
      e.d += geomPath(f.geometry); e.n += 1
      by.set(k, e)
    }
    return { colors, by }
  }, [feats, layer])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }} data-testid="jica-map">
      <div className="view-switch" role="tablist" aria-label="Thème">
        {JICA_GROUPS.map(g => (
          <button key={g.id} className={group.id === g.id ? 'active' : ''} onClick={() => { setGroup(g); setLayer(g.layers[0]) }}>{g.label}</button>
        ))}
      </div>
      <div className="view-switch" role="tablist" aria-label="Couche JICA" style={{ flexWrap: 'wrap' }}>
        {group.layers.map(l => (
          <button key={l.id} className={layer.id === l.id ? 'active' : ''} onClick={() => setLayer(l)}>{l.label}</button>
        ))}
      </div>
      <p style={{ fontSize: 12, color: 'var(--warn, #fbbf24)', margin: 0 }}>
        ⚠️ Licence JICA non confirmée : usage interne uniquement. Noms et classes provisoires (légendes JICA attendues). Données ~2007-2008.
      </p>
      {feats === 'loading' && <p className="muted">Chargement…</p>}
      {feats === 'error' && <p className="muted">Couche indisponible — elle nécessite l'API MizanBI (VITE_API_BASE).</p>}
      {drawn && Array.isArray(feats) && (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={layer.label} style={{ width: '100%', maxWidth: W, background: 'var(--surface-solid)', borderRadius: 12 }}>
            {[...drawn.by].map(([k, e]) => {
              const c = drawn.colors.get(k)
              if (e.kind === 'poly') return <path key={k} d={e.d} fill={c} fillOpacity={0.5} stroke="rgba(255,255,255,.35)" strokeWidth={0.4} />
              if (e.kind === 'line') return <path key={k} d={e.d} fill="none" stroke={c} strokeWidth={0.8} strokeLinejoin="round" />
              return <path key={k} d={e.d} fill="none" stroke={c} strokeWidth={3.5} strokeLinecap="round" opacity={0.85} />
            })}
          </svg>
          <div style={{ minWidth: 220, maxWidth: 300, fontSize: 12 }}>
            <strong>{layer.label}</strong>
            <ul style={{ listStyle: 'none', padding: 0, margin: '6px 0', maxHeight: 360, overflowY: 'auto' }}>
              {[...drawn.colors].map(([v, c]) => (
                <li key={v} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <span style={{ width: 12, height: 12, background: c, borderRadius: 3, display: 'inline-block', flex: 'none' }} />
                  <span>{v}{layer.unit && v !== '—' ? ` ${layer.unit}` : ''}</span>
                  <span className="muted" style={{ marginInlineStart: 'auto' }}>{drawn.by.get(v)?.n}</span>
                </li>
              ))}
            </ul>
            <p className="muted" style={{ margin: 0 }}>{feats.length} entités</p>
          </div>
        </div>
      )}
      <GeoSources layerIds={[layer.id]} note="Reprojeté depuis UTM 38N (EPSG:32638) ; géométries simplifiées (5-10 m)." />
    </div>
  )
}
