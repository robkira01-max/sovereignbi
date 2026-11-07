import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import type { Page } from '../components/AppShell'
import geoData from '../data/dji_adm1.geojson'
import { TradeFlowMap } from '../components/TradeFlowMap'
import {
  UNEMPLOY, TREND_YEARS, TREND_VALS,
  buildTrendPoints, buildAreaPoints, buildMap,
} from '../data/employment_dj'

interface HomePageProps {
  onNavigate: (page: Exclude<Page, 'home'>) => void
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
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, color: 'oklch(72% 0.03 265)' }}>Modèle tendanciel — INSTAD / MizanBI</span>
              <button
                onClick={() => onNavigate('scrolly')}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                  fontSize: 12, color: 'var(--brand)', fontFamily: 'inherit',
                }}
              >
                Lire l'analyse →
              </button>
            </div>
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

        {/* ── Flux commerciaux (span 4) ── */}
        <div style={{ ...tile, gridColumn: 'span 4' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 8 }}>
            <span style={{ fontWeight: 600 }}>Flux commerciaux — Port de Djibouti</span>
            <span style={{ fontSize: 12, color: 'oklch(72% 0.03 265)' }}>Corridor DJ → Éthiopie</span>
          </div>
          <TradeFlowMap />
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
