import { useMemo } from 'react'
import geoData from '../data/dji_adm1.geojson'
import {
  UNEMPLOY, TREND_YEARS, TREND_VALS,
  buildTrendPoints, buildAreaPoints, regionColor, buildMap,
} from '../data/employment_dj'
import { ScrollySection, type ScrollyStep } from '../components/ScrollySection'
import type { Page } from '../components/AppShell'

interface Props {
  onNavigate: (page: Exclude<Page, 'scrolly'>) => void
}

const PANEL: React.CSSProperties = {
  borderRadius: 16,
  padding: 20,
  background: 'oklch(17% 0.04 265)',
  border: '1px solid oklch(27% 0.05 265)',
}

function FigureTrend() {
  const trendPts = buildTrendPoints(TREND_VALS)
  const areaPts  = buildAreaPoints(TREND_VALS)
  return (
    <div style={PANEL} data-testid="figure-trend">
      <div style={{ fontSize: 12, color: 'oklch(72% 0.03 265)', marginBottom: 10 }}>
        Taux de chômage national (%)
      </div>
      <svg viewBox="0 0 300 120" style={{ direction: 'ltr', width: '100%', height: 150 }} preserveAspectRatio="none">
        <polygon points={areaPts} fill="oklch(68% 0.18 155 / 0.2)" />
        <polyline points={trendPts} fill="none" stroke="oklch(68% 0.18 155)" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
      </svg>
      <div dir="ltr" style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'oklch(68% 0.03 265)' }}>
        {TREND_YEARS.map(y => <span key={y}>{y}</span>)}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 14, flexWrap: 'wrap', gap: 8 }}>
        <div>
          <div style={{ fontSize: 11, color: 'oklch(72% 0.03 265)' }}>2009</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'oklch(68% 0.18 265)' }}>60,2 %</div>
        </div>
        <div style={{ color: 'oklch(78% 0.17 155)', fontSize: 22, fontWeight: 700, alignSelf: 'center' }}>▼ 34 pt</div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 11, color: 'oklch(72% 0.03 265)' }}>2024</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'oklch(68% 0.18 155)' }}>25,8 %</div>
        </div>
      </div>
    </div>
  )
}

function FigureChoropleth({ highlightRegion }: { highlightRegion?: string }) {
  const { viewBox, ratio, shapes } = useMemo(
    () => buildMap(geoData.features as GeoJSON.Feature[]),
    []
  )
  return (
    <div style={PANEL} data-testid="figure-choropleth">
      <div style={{ fontSize: 12, color: 'oklch(72% 0.03 265)', marginBottom: 10 }}>
        Chômage par région (REGV 2024)
      </div>
      <div style={{ position: 'relative', width: '100%', maxWidth: 280, margin: '0 auto', aspectRatio: String(ratio) }}>
        <svg viewBox={viewBox} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
          {shapes.map(s => (
            <path
              key={s.name}
              d={s.d}
              fill={s.fill}
              stroke={s.name === highlightRegion ? 'oklch(80% 0.22 55)' : 'oklch(85% 0.03 265)'}
              strokeWidth={s.name === highlightRegion ? '2' : '0.8'}
              strokeLinejoin="round"
            />
          ))}
        </svg>
        {shapes.map(s => (
          <div key={s.name} style={{
            position: 'absolute', left: s.lx, top: s.ly,
            transform: 'translate(-50%, -50%)',
            pointerEvents: 'none', textAlign: 'center',
            fontSize: 9, lineHeight: 1.15, fontWeight: 600, color: '#fff',
            textShadow: '0 1px 3px oklch(10% 0.04 265), 0 0 6px oklch(10% 0.04 265)',
          }}>
            {s.name}<br />
            <b style={{ fontSize: 11, color: s.name === highlightRegion ? 'oklch(90% 0.22 55)' : '#fff' }}>
              {s.val}%
            </b>
          </div>
        ))}
      </div>
    </div>
  )
}

function FigureBar() {
  const sorted = Object.entries(UNEMPLOY).sort(([, a], [, b]) => a - b)
  const max = Math.max(...Object.values(UNEMPLOY))
  return (
    <div style={PANEL} data-testid="figure-bar">
      <div style={{ fontSize: 12, color: 'oklch(72% 0.03 265)', marginBottom: 14 }}>
        Taux de chômage par région (%)
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {sorted.map(([name, val]) => (
          <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 72, fontSize: 11, color: 'oklch(85% 0.03 265)', textAlign: 'right', flexShrink: 0 }}>
              {name}
            </div>
            <div style={{ flex: 1, height: 18, borderRadius: 4, background: 'oklch(22% 0.04 265)', overflow: 'hidden' }}>
              <div style={{
                width: `${(val / max) * 100}%`,
                height: '100%',
                borderRadius: 4,
                background: regionColor(val),
              }} />
            </div>
            <div style={{ width: 36, fontSize: 11, fontWeight: 600, color: 'oklch(88% 0.03 265)', flexShrink: 0 }}>
              {val}%
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function FigureYouth() {
  const data = [
    { label: 'National',      val: 25.8, color: 'oklch(68% 0.18 155)' },
    { label: 'Femmes (est.)', val: 36.4, color: 'oklch(72% 0.19 55)' },
    { label: '15–24 ans',     val: 42.0, color: 'oklch(65% 0.22 25)' },
  ]
  const maxVal = 50
  return (
    <div style={PANEL} data-testid="figure-youth">
      <div style={{ fontSize: 12, color: 'oklch(72% 0.03 265)', marginBottom: 14 }}>
        Chômage par groupe — estimation INSTAD 2024
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', height: 160, paddingBottom: 8 }}>
        {data.map(d => (
          <div key={d.label} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, flex: 1 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: d.color }}>{d.val}%</div>
            <div style={{
              width: 40,
              height: `${(d.val / maxVal) * 120}px`,
              background: d.color,
              borderRadius: '4px 4px 0 0',
            }} />
            <div style={{ fontSize: 10, color: 'oklch(72% 0.03 265)', textAlign: 'center', lineHeight: 1.3 }}>
              {d.label}
            </div>
          </div>
        ))}
      </div>
      <div style={{ fontSize: 10, color: 'oklch(55% 0.03 265)', marginTop: 8 }}>
        * Estimations basées sur les tendances REGV 2024
      </div>
    </div>
  )
}

function FigureForecast() {
  return (
    <div style={PANEL} data-testid="figure-forecast">
      <div style={{ fontSize: 12, color: 'oklch(72% 0.03 265)', marginBottom: 10 }}>
        Prévision tendancielle 2030
      </div>
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 11, color: 'oklch(72% 0.03 265)' }}>Estimation 2030</div>
        <div style={{ fontSize: 32, fontWeight: 700, letterSpacing: '-0.02em', color: 'oklch(82% 0.15 65)' }}>
          23,1 %
        </div>
        <div style={{ fontSize: 12, color: 'oklch(72% 0.03 265)' }}>IC 20,5 – 26 %</div>
      </div>
      <svg viewBox="0 0 400 100" preserveAspectRatio="none" style={{ direction: 'ltr', width: '100%', height: 100 }}>
        <polygon points="285,55 400,45 400,88" fill="oklch(72% 0.19 55 / 0.22)" />
        <line x1="285" y1="0" x2="285" y2="100" stroke="oklch(45% 0.05 265)" strokeDasharray="4 4" vectorEffect="non-scaling-stroke" />
        <polyline points="0,20 57,30 133,39 209,32 247,45 285,55" fill="none" stroke="oklch(68% 0.18 155)" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
        <polyline points="285,55 342,61 400,68" fill="none" stroke="oklch(75% 0.19 55)" strokeWidth="2.5" strokeDasharray="6 5" vectorEffect="non-scaling-stroke" />
      </svg>
      <div dir="ltr" style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'oklch(68% 0.03 265)', marginTop: 4 }}>
        <span>2009</span><span>2024</span><span>2030</span>
      </div>
    </div>
  )
}

const STEPS: ScrollyStep[] = [
  {
    title: 'Une décennie de transformation',
    body: 'Le chômage à Djibouti a reculé de 60 % à 25,8 % entre 2009 et 2024 — une baisse de 34 points en quinze ans. Derrière ce chiffre, une économie en mutation : port en expansion, investissements massifs en infrastructure, montée des services et de la logistique.',
  },
  {
    title: 'Des disparités régionales profondes',
    body: "La région d'Obock affiche un taux de 33,2 %, contre 22,3 % pour Ali Sabieh — un écart de près de 11 points. Les régions intérieures (Dikhil, Tadjourah, Arta) restent bien au-dessus de la capitale, faute d'un tissu économique diversifié.",
  },
  {
    title: "La capitale, moteur de l'emploi",
    body: "Djibouti-ville concentre plus de 70 % des emplois formels du pays. Son taux (24,1 %) reste en dessous de la moyenne nationale de 27,9 %. L'activité portuaire, les zones franches et les services financiers y absorbent la majeure partie des nouveaux entrants.",
  },
  {
    title: 'Jeunes et femmes : les plus exposés',
    body: "Le chômage des 15–24 ans atteint environ 42 % en 2024, soit 1,6 fois la moyenne nationale. Les femmes représentent plus de 65 % des chômeurs longue durée. L'économie formelle n'absorbe pas encore la nouvelle génération en nombre suffisant.",
  },
  {
    title: 'Perspectives 2030 : vers 23 %',
    body: "Selon le modèle tendanciel de l'INSTAD, le taux devrait atteindre 23,1 % d'ici 2030 (intervalle de confiance : 20,5 – 26 %). Cela suppose le maintien du rythme actuel des investissements portuaires et industriels — une hypothèse contingente aux conditions régionales.",
  },
]

export function ScrollyPage({ onNavigate }: Props) {
  return (
    <div data-testid="scrolly-report" style={{ maxWidth: 920, paddingBottom: 80 }}>
      <button
        onClick={() => onNavigate('home')}
        style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'oklch(72% 0.03 265)', fontSize: 13, padding: '0 0 20px',
          display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'inherit',
        }}
        data-testid="scrolly-back"
      >
        ← Accueil
      </button>

      <div style={{ marginBottom: 48 }}>
        <div style={{ fontSize: 12, color: 'oklch(65% 0.22 265)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
          Rapport narratif · INSTAD / MizanBI
        </div>
        <h1 style={{ margin: '0 0 12px', fontSize: 32, fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text)', lineHeight: 1.15 }}>
          Chômage à Djibouti
        </h1>
        <p style={{ margin: '0 0 16px', fontSize: 18, color: 'oklch(78% 0.03 265)', lineHeight: 1.5 }}>
          Tendances et perspectives 2009–2030
        </p>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 12, color: 'oklch(65% 0.03 265)' }}>
          <span>Données : REGV 2024</span>
          <span>·</span>
          <span>Source : INSTAD Djibouti</span>
          <span>·</span>
          <span>Modèle : MizanBI</span>
        </div>
      </div>

      <ScrollySection
        steps={STEPS}
        figureWidth="44%"
        figure={activeIdx => {
          if (activeIdx === 0) return <FigureTrend />
          if (activeIdx === 1) return <FigureChoropleth highlightRegion="Obock" />
          if (activeIdx === 2) return <FigureBar />
          if (activeIdx === 3) return <FigureYouth />
          return <FigureForecast />
        }}
      />

      <div style={{
        marginTop: 48, padding: 16, borderRadius: 10,
        background: 'oklch(17% 0.04 265 / 0.6)',
        border: '1px solid oklch(27% 0.05 265)',
        fontSize: 12, color: 'oklch(65% 0.03 265)', lineHeight: 1.6,
      }}>
        ⚠ Données illustratives à des fins de démonstration. Se référer à l'édition officielle du REGV pour tout usage officiel. Ce rapport n'est pas un conseil économique.
      </div>
    </div>
  )
}
