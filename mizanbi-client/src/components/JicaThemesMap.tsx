import { useEffect, useMemo, useState } from 'react'
import { apiFetch, isApiConfigured } from '../lib/api'
import GeoSources from './GeoSources'

// Couches thématiques JICA (hydrogéologie, climat, points d'eau) servies par /api/v1/geo/dj/{id}.
// Licence non confirmée : usage interne, avertissement affiché en permanence.

type Geom = { type: string; coordinates: unknown }
interface Feat { geometry: Geom; properties: Record<string, string | number | null> }

interface LayerDef { id: string; label: string; valueKey: string; labelKey: string; unit?: string }
export const JICA_LAYERS: LayerDef[] = [
  { id: 'jica_pluie_moyenne', label: 'Pluie moyenne annuelle', valueKey: 'Pluiemoyen', labelKey: 'Pluiemoyen', unit: 'mm' },
  { id: 'jica_etp', label: 'Évapotranspiration potentielle (ETP)', valueKey: 'ETP', labelKey: 'ETP' },
  { id: 'jica_etr', label: 'Évapotranspiration réelle (ETR)', valueKey: 'ETR', labelKey: 'ETR' },
  { id: 'jica_zones_climatiques', label: 'Zones climatiques', valueKey: 'zoneclimat', labelKey: 'zoneclimat' },
  { id: 'jica_systemes_aquiferes', label: 'Systèmes aquifères', valueKey: 'SystAquif', labelKey: 'Name' },
  { id: 'jica_debit_aquiferes', label: 'Débit des aquifères (classes)', valueKey: 'Debit', labelKey: 'Name' },
  { id: 'jica_points_eau', label: "Points d'eau", valueKey: 'region', labelKey: 'nom' },
]

const W = 640
const LON0 = 41.7, LON1 = 43.5, LAT0 = 10.9, LAT1 = 12.8
const COS = Math.cos(((LAT0 + LAT1) / 2) * Math.PI / 180)
const H = Math.round(W * ((LAT1 - LAT0) / ((LON1 - LON0) * COS)))
const px = (lon: number, lat: number): [number, number] => [((lon - LON0) / (LON1 - LON0)) * W, ((LAT1 - lat) / (LAT1 - LAT0)) * H]

function ringPath(ring: number[][]): string {
  return ring.map(([lon, lat], i) => { const [x, y] = px(lon, lat); return `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}` }).join('') + 'Z'
}
function geomPath(g: Geom): string {
  const c = g.coordinates as number[][][] | number[][][][]
  if (g.type === 'Polygon') return (c as number[][][]).map(ringPath).join('')
  if (g.type === 'MultiPolygon') return (c as number[][][][]).map(p => p.map(ringPath).join('')).join('')
  return ''
}

const PALETTE = ['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#c084fc', '#22d3ee', '#fb923c', '#a3e635', '#f472b6', '#94a3b8']

export function classColors(values: (string | number | null)[]): Map<string, string> {
  const uniq = [...new Set(values.map(v => String(v ?? '—')))]
  const nums = uniq.every(u => u === '—' || !isNaN(Number(u)))
  const rank = (u: string) => (u === '—' ? 1 : 0)       // « — » (valeur absente) toujours en dernier
  uniq.sort((a, b) => rank(a) - rank(b) || (nums ? Number(a) - Number(b) : a.localeCompare(b)))
  return new Map(uniq.map((u, i) => [u, PALETTE[i % PALETTE.length]]))
}

export default function JicaThemesMap() {
  const [layer, setLayer] = useState<LayerDef>(JICA_LAYERS[0])
  const [feats, setFeats] = useState<Feat[] | 'loading' | 'error'>('loading')
  const [hover, setHover] = useState<Feat | null>(null)

  useEffect(() => {
    if (!isApiConfigured()) { setFeats('error'); return }
    let alive = true
    setFeats('loading'); setHover(null)
    apiFetch(`/api/v1/geo/dj/${layer.id}`).then(r => r.json())
      .then(fc => { if (alive) setFeats((fc as { features: Feat[] }).features) })
      .catch(() => { if (alive) setFeats('error') })
    return () => { alive = false }
  }, [layer])

  const colors = useMemo(() => Array.isArray(feats) ? classColors(feats.map(f => f.properties[layer.valueKey])) : new Map<string, string>(), [feats, layer])
  const isPoints = layer.id === 'jica_points_eau'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }} data-testid="jica-map">
      <div className="view-switch" role="tablist" aria-label="Thème JICA" style={{ flexWrap: 'wrap' }}>
        {JICA_LAYERS.map(l => (
          <button key={l.id} className={layer.id === l.id ? 'active' : ''} onClick={() => setLayer(l)}>{l.label}</button>
        ))}
      </div>
      <p style={{ fontSize: 12, color: 'var(--warn, #fbbf24)', margin: 0 }}>
        ⚠️ Licence JICA non confirmée : usage interne uniquement, données ~2007-2008, ne pas diffuser avant accord écrit.
      </p>
      {feats === 'loading' && <p className="muted">Chargement…</p>}
      {feats === 'error' && <p className="muted">Couche indisponible — elle nécessite l'API MizanBI (VITE_API_BASE).</p>}
      {Array.isArray(feats) && (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={layer.label} style={{ width: '100%', maxWidth: W, background: 'var(--surface-solid)', borderRadius: 12 }}>
            {feats.map((f, i) => {
              const fill = colors.get(String(f.properties[layer.valueKey] ?? '—'))
              if (isPoints && f.geometry.type === 'Point') {
                const [lon, lat] = f.geometry.coordinates as number[]
                const [x, y] = px(lon, lat)
                return <circle key={i} cx={x} cy={y} r={2.2} fill={fill} opacity={0.85} onMouseEnter={() => setHover(f)} onMouseLeave={() => setHover(null)} />
              }
              return <path key={i} d={geomPath(f.geometry)} fill={fill} fillOpacity={0.55} stroke="rgba(255,255,255,.35)" strokeWidth={0.4}
                onMouseEnter={() => setHover(f)} onMouseLeave={() => setHover(null)} />
            })}
          </svg>
          <div style={{ minWidth: 200, fontSize: 12 }}>
            <strong>{isPoints ? 'Région' : layer.label}</strong>
            <ul style={{ listStyle: 'none', padding: 0, margin: '6px 0' }}>
              {[...colors].map(([v, c]) => (
                <li key={v} style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <span style={{ width: 12, height: 12, background: c, borderRadius: 3, display: 'inline-block' }} />{v}{layer.unit && v !== '—' ? ` ${layer.unit}` : ''}
                </li>
              ))}
            </ul>
            <p className="muted" style={{ margin: 0 }}>{feats.length} entités{hover ? ` · ${String(hover.properties[layer.labelKey] ?? '—')}` : ''}</p>
          </div>
        </div>
      )}
      <GeoSources layerIds={[layer.id]} note="Reprojeté depuis UTM 38N (EPSG:32638) ; polygones simplifiés à 5 m." />
    </div>
  )
}
