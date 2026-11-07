import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import type { Page } from '../components/AppShell'
import geoData from '../data/dji_adm1.geojson'

interface HomePageProps {
  onNavigate: (page: Exclude<Page, 'home'>) => void
}

// REGV 2024 unemployment rates by region
const UNEMPLOY: Record<string, number> = {
  'Obock':      33.2,
  'Dikhil':     31.5,
  'Tadjourah':  29.0,
  'Arta':       27.4,
  'Djibouti':   24.1,
  'Ali Sabieh': 22.3,
}

function regionColor(val: number): string {
  const t = (val - 22) / 11
  const l = 32 + t * 30
  const c = 0.12 + t * 0.08
  return `oklch(${l}% ${c} 265)`
}

// Equirectangular projection with cosine-latitude correction
function buildMap(features: GeoJSON.Feature[]) {
  const W = 300
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity
  features.forEach(f => {
    const coords = (f.geometry as GeoJSON.Polygon).coordinates[0]
    coords.forEach(([x, y]) => {
      if (x < x0) x0 = x; if (x > x1) x1 = x
      if (y < y0) y0 = y; if (y > y1) y1 = y
    })
  })
  const midLat = (y0 + y1) / 2
  const k = Math.cos(midLat * Math.PI / 180)
  const sc = W / ((x1 - x0) * k)
  const H = (y1 - y0) * sc
  const px = (x: number) => (x - x0) * k * sc
  const py = (y: number) => (y1 - y) * sc
  const viewBox = `-6 -6 ${W + 12} ${H + 12}`
  const ratio = (W + 12) / (H + 12)

  const shapes = features.map(f => {
    const name = (f.properties as { shapeName: string }).shapeName
    const coords = (f.geometry as GeoJSON.Polygon).coordinates[0]
    const d = coords.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${px(x).toFixed(1)},${py(y).toFixed(1)}`).join(' ') + 'Z'
    // centroid approx
    const cx = coords.reduce((s, [x]) => s + x, 0) / coords.length
    const cy = coords.reduce((s, [, y]) => s + y, 0) / coords.length
    const lx = `${(px(cx) / (W + 12) * 100).toFixed(1)}%`
    const ly = `${(py(cy) / (H + 12) * 100).toFixed(1)}%`
    const val = UNEMPLOY[name] ?? 25
    return { name, d, lx, ly, val, fill: regionColor(val) }
  })

  return { viewBox, ratio, shapes }
}

// Historical unemployment data 2009–2024 (approximate REGV)
const TREND_YEARS = [2009, 2012, 2015, 2017, 2019, 2021, 2024]
const TREND_VALS  = [60.2, 54.8, 48.3, 40.1, 35.7, 29.6, 25.8]

function buildTrendPoints(vals: number[], W = 300, H = 120): string {
  const mn = Math.min(...vals) - 2
  const mx = Math.max(...vals) + 2
  return vals.map((v, i) => {
    const x = (i / (vals.length - 1)) * W
    const y = H - ((v - mn) / (mx - mn)) * H
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}

function buildAreaPoints(vals: number[], W = 300, H = 120): string {
  const mn = Math.min(...vals) - 2
  const mx = Math.max(...vals) + 2
  const pts = vals.map((v, i) => {
    const x = (i / (vals.length - 1)) * W
    const y = H - ((v - mn) / (mx - mn)) * H
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return `0,${H} ${pts.join(' ')} ${W},${H}`
}

export function HomePage({ onNavigate }: HomePageProps) {
  const [tables, setTables] = useState<string[]>([])
  const [loadingTables, setLoadingTables] = useState(true)

  useEffect(() => {
    api.health()
      .then((data: unknown) => setTables((data as { tables?: string[] }).tables ?? []))
      .catch(() => {})
      .finally(() => setLoadingTables(false))
  }, [])

  const { viewBox, ratio, shapes } = useMemo(
    () => buildMap(geoData.features as GeoJSON.Feature[]),
    []
  )

  const trendPts = buildTrendPoints(TREND_VALS)
  const areaPts  = buildAreaPoints(TREND_VALS)
  const avgUnemploy = (Object.values(UNEMPLOY).reduce((a, b) => a + b, 0) / Object.values(UNEMPLOY).length).toFixed(1)

  const tile: React.CSSProperties = {
    borderRadius: 18, padding: 18,
    background: 'oklch(17% 0.04 265)',
    border: '1px solid oklch(27% 0.05 265)',
    display: 'flex', flexDirection: 'column', gap: 10,
  }

  const label: React.CSSProperties = {
    fontSize: 12, color: 'oklch(72% 0.03 265)',
  }

  return (
    <div style={{ maxWidth: 1000 }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
        gridAutoRows: 'minmax(120px, auto)',
        gap: 14,
      }}>

        {/* ── Choropleth map (2×2) ── */}
        <div style={{ ...tile, gridColumn: 'span 2', gridRow: 'span 2' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <span style={{ fontWeight: 600 }}>Chômage par région</span>
            <span style={{ fontSize: 11, color: 'oklch(72% 0.03 265)' }}>REGV 2024</span>
          </div>
          <div dir="ltr" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 230 }}>
            <div style={{ position: 'relative', width: '100%', maxWidth: 340, aspectRatio: String(ratio) }}>
              <svg viewBox={viewBox} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
                {shapes.map(s => (
                  <path key={s.name} d={s.d} fill={s.fill}
                    stroke="oklch(85% 0.03 265)" strokeWidth="0.8" strokeLinejoin="round" />
                ))}
              </svg>
              {shapes.map(s => (
                <div key={s.name} style={{
                  position: 'absolute', left: s.lx, top: s.ly,
                  transform: 'translate(-50%, -50%)',
                  pointerEvents: 'none', textAlign: 'center',
                  fontSize: 10, lineHeight: 1.15, fontWeight: 600, color: '#fff',
                  textShadow: '0 1px 3px oklch(10% 0.04 265), 0 0 6px oklch(10% 0.04 265)',
                }}>
                  {s.name}<br />
                  <b style={{ fontSize: 12 }}>{s.val}%</b>
                </div>
              ))}
            </div>
          </div>
          {/* Legend */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'oklch(72% 0.03 265)' }}>
            <span>22 %</span>
            <span style={{ flex: 1, height: 6, borderRadius: 3, background: 'linear-gradient(90deg, oklch(32% 0.12 265), oklch(62% 0.2 265))' }} />
            <span>33 %</span>
          </div>
        </div>

        {/* ── Trend chart (2×2) ── */}
        <div style={{ ...tile, gridColumn: 'span 2', gridRow: 'span 2' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 600 }}>Évolution du chômage</span>
            <span style={{ color: 'oklch(78% 0.17 155)', fontWeight: 600 }}>▼ 4,5 pt</span>
          </div>
          <svg dir="ltr" viewBox="0 0 300 120" style={{ flex: 1, width: '100%', minHeight: 120 }} preserveAspectRatio="none">
            <polygon points={areaPts} fill="oklch(68% 0.18 155 / 0.2)" />
            <polyline points={trendPts} fill="none" stroke="oklch(68% 0.18 155)" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
          </svg>
          <div dir="ltr" style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'oklch(68% 0.03 265)' }}>
            {TREND_YEARS.map(y => <span key={y}>{y}</span>)}
          </div>
        </div>

        {/* ── KPI chômage moyen ── */}
        <div style={tile}>
          <div style={label}>Chômage moyen</div>
          <div style={{ fontSize: 30, fontWeight: 700, letterSpacing: '-0.02em', color: 'oklch(80% 0.17 155)' }}>
            {avgUnemploy} %
          </div>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'oklch(72% 0.03 265)' }}>Toutes régions</div>
        </div>

        {/* ── KPI population ── */}
        <div style={tile}>
          <div style={label}>Population</div>
          <div style={{ fontSize: 30, fontWeight: 700, letterSpacing: '-0.02em', color: 'oklch(80% 0.17 155)' }}>
            1,1 M
          </div>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'oklch(72% 0.19 55)' }}>+2,3 % / an</div>
        </div>

        {/* ── Forecast 2030 (span 4) ── */}
        <div style={{ ...tile, gridColumn: 'span 4' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600 }}>Prévision chômage 2030</span>
            <span style={{ fontSize: 12, color: 'oklch(72% 0.03 265)' }}>Modèle tendanciel — INSTAD / MizanBI</span>
          </div>
          <div style={{ display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 130 }}>
              <div style={{ fontSize: 12, color: 'oklch(72% 0.03 265)' }}>2030</div>
              <div style={{ fontSize: 34, fontWeight: 700, letterSpacing: '-0.02em', color: 'oklch(82% 0.15 65)' }}>23,1 %</div>
              <div style={{ fontSize: 12, color: 'oklch(72% 0.03 265)' }}>IC 20,5 – 26</div>
            </div>
            <svg dir="ltr" viewBox="0 0 600 120" preserveAspectRatio="none" style={{ flex: 1, minWidth: 240, height: 120 }}>
              {/* Uncertainty cone */}
              <polygon points="428.6,65.5 600,55.5 600,105.5" fill="oklch(72% 0.19 55 / 0.22)" />
              {/* Dashed separator */}
              <line x1="428.6" y1="0" x2="428.6" y2="120" stroke="oklch(45% 0.05 265)" strokeDasharray="4 4" vectorEffect="non-scaling-stroke" />
              {/* Historical */}
              <polyline points="0,24.5 85.7,36.4 200,47.3 314.3,39.1 371.4,53.6 428.6,65.5"
                fill="none" stroke="oklch(68% 0.18 155)" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
              {/* Forecast */}
              <polyline points="428.6,65.5 514.3,73.6 600,81.8"
                fill="none" stroke="oklch(75% 0.19 55)" strokeWidth="2.5" strokeDasharray="6 5" vectorEffect="non-scaling-stroke" />
            </svg>
          </div>
          <div dir="ltr" style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'oklch(68% 0.03 265)' }}>
            <span>2009</span><span>2024</span><span>2030</span>
          </div>
        </div>

        {/* ── Tables chargées (span 4) ── */}
        <div style={{ ...tile, gridColumn: 'span 4' }}>
          <div style={{ fontWeight: 600 }}>Tables chargées</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {loadingTables ? (
              <span style={{ color: 'oklch(62% 0.03 265)', fontSize: 12 }}>…</span>
            ) : tables.length > 0 ? (
              tables.map(tb => (
                <span key={tb} style={{
                  font: '500 12px \'JetBrains Mono\', monospace',
                  padding: '4px 10px', borderRadius: 999,
                  background: 'oklch(30% 0.09 155)',
                  color: 'oklch(88% 0.12 155)',
                }}>{tb}</span>
              ))
            ) : (
              <button
                onClick={() => onNavigate('data')}
                style={{
                  font: '500 12px inherit', background: 'none', border: 'none',
                  color: 'var(--brand)', cursor: 'pointer', padding: 0,
                }}
              >+ Importer des données →</button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
