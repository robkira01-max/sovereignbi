import { useState } from 'react'
import type { Dict } from '../lib/i18n'
import { PROVENANCE, QUARTIERS, REGIONS, TRADE_FLOWS, fmt } from '../data/demo'
import DjiboutiMap from '../components/DjiboutiMap'
import EcolesMap from '../components/EcolesMap'
import { colorForValue, currentTheme, scaleFor, textOnFill, type IndicatorId } from '../lib/theme'

type Level = 'adm1' | 'adm2' | 'quartiers'

// P-028 : indicateur pilotant la carte et l'accent du dashboard (chômage /
// population / pauvreté). Les couleurs viennent des valeurs via colorForValue(),
// sur une échelle calculée sur les données affichées — plus de rampe fixe.
const INDICATORS: { id: IndicatorId; label: string; unit: string }[] = [
  { id: 'unemployment', label: 'Chômage', unit: '%' },
  { id: 'population', label: 'Population', unit: ' hab.' },
  { id: 'poverty', label: 'Pauvreté', unit: '%' },
]

export default function SigPage({ t, onIndicator, onAncient }: { t: Dict; onIndicator?: (i: IndicatorId) => void; onAncient?: () => void }) {
  const [level, setLevel] = useState<Level>('adm1')
  const [bivariate, setBivariate] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [indicator, setIndicator] = useState<IndicatorId>('unemployment')
  // P-025 : flux illustratifs masqués par défaut.
  const [showFlows, setShowFlows] = useState(false)

  const setInd = (i: IndicatorId) => { setIndicator(i); onIndicator?.(i) }
  const ind = INDICATORS.find((x) => x.id === indicator) ?? INDICATORS[0]
  const qScale = scaleFor(QUARTIERS.map((q) => q.unemployment), currentTheme(), '%', { reference: 25, referenceLabel: 'Seuil d’alerte chômage : 25 % (démo, 2024)' })

  const levelOf = (v: number, min: number, max: number) => (v < min + (max - min) / 3 ? 0 : v < min + (2 * (max - min)) / 3 ? 1 : 2)
  const bivColors = [
    ['oklch(35% 0.05 265)', 'oklch(40% 0.08 200)', 'oklch(45% 0.12 155)'],
    ['oklch(40% 0.08 300)', 'oklch(45% 0.08 265)', 'oklch(50% 0.12 155)'],
    ['oklch(45% 0.1 25)', 'oklch(50% 0.12 35)', 'oklch(55% 0.16 25)'],
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 1100 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, letterSpacing: '-.02em' }}>{t.mizansig}</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--muted)' }}>{t.voletSig} — {t.demoBadge}</p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span className="badge badge-volet2">Volet 2</span>
          <span className="badge badge-ok">{t.offlineBadge}</span>
        </div>
      </div>
      <div style={{ padding: '12px 16px', borderRadius: 12, background: 'var(--surface)', border: '1px solid var(--border)', fontSize: 13, lineHeight: 1.6 }}>
        {t.offlineNote}<br />{t.pwaNote}
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <div className="view-switch">
          <button className={level === 'adm1' ? 'active' : ''} onClick={() => setLevel('adm1')}>ADM1 — {t.regions}</button>
          <button className={level === 'adm2' ? 'active' : ''} onClick={() => setLevel('adm2')}>ADM2 — {t.districts}</button>
          <button className={level === 'quartiers' ? 'active' : ''} onClick={() => setLevel('quartiers')}>{t.quarters}</button>
        </div>
        <button className="btn-ghost" onClick={() => setBivariate((b) => !b)}>{t.bivariate} {bivariate ? '✓' : ''}</button>
        {onAncient && <button className="btn-ghost" onClick={onAncient}>🗺️ {t.ancientMaps} — importer un scan</button>}
        <div className="view-switch" role="tablist" aria-label="Indicateur">
          {INDICATORS.map((x) => (
            <button key={x.id} className={indicator === x.id ? 'active' : ''} onClick={() => setInd(x.id)}>{x.label}</button>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 380px), 1fr))', gap: 16 }}>
        <section className="card-solid">
          <h3>{level === 'quartiers' ? t.quarters : `${t.mapTitle} — ${ind.label}`}</h3>
          {level === 'quartiers' ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 6, marginTop: 12 }}>
              {QUARTIERS.map((q) => {
                const bg = colorForValue(q.unemployment, qScale)
                const fg = textOnFill(q.unemployment, qScale)
                return (
                  <div key={q.name} style={{ borderRadius: 10, padding: '12px 8px', textAlign: 'center', background: bg, color: fg }}>
                    <div style={{ fontSize: 11, opacity: 0.9 }}>{q.name}</div>
                    <div style={{ fontWeight: 700, fontSize: 16 }}>{String(q.unemployment).replace('.', ',')} %</div>
                  </div>
                )
              })}
            </div>
          ) : (
            <DjiboutiMap selected={selected} onSelect={setSelected} indicator={indicator} unit={ind.unit.trim() === 'hab.' ? 'hab.' : '%'} />
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--muted)', marginTop: 8 }}>
            <span>{level === 'quartiers' ? `${String(qScale.min).replace('.', ',')} %` : ind.label}</span>
            <span className="legend-bar" />
            <span>{level === 'quartiers' ? `${String(qScale.max).replace('.', ',')} %` : ''}</span>
          </div>
          <p className="muted" style={{ marginTop: 10 }}>
            {level === 'quartiers' ? t.approx : `${t.offlineTiles} — bbox Djibouti 41,7 / 10,9 – 43,6 / 12,8, environ 10–30 Mo.`}
          </p>
        </section>

        <section className="card-solid">
          <h3>{level === 'adm2' ? t.districts : level === 'quartiers' ? t.quarters : t.regions}</h3>
          <div className="table-wrap" style={{ marginTop: 12, maxHeight: 340 }}>
            <table className="data">
              <thead><tr><th>Nom</th><th>Population</th><th>Chômage</th><th>Pauvreté</th></tr></thead>
              <tbody>
                {(level === 'quartiers'
                  ? QUARTIERS.map((q) => [q.name, q.population, q.unemployment, '—'])
                  : REGIONS.map((r) => [r.name, r.population, r.unemployment, r.poverty ?? '—'])
                ).map((row, i) => (
                  <tr key={i}>{row.map((c, j) => <td key={j}>{typeof c === 'number' ? fmt(c) : c}{j === 2 && typeof c === 'number' ? ' %' : ''}{j === 3 && typeof c === 'number' ? ' %' : ''}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
          {level === 'adm2' && <p className="muted" style={{ marginTop: 8 }}>ADM2 : 6 districts enrichis (population, densité). Contours ADM2 à brancher sur data/geo/dj_adm2.geojson quand l’API les sert.</p>}
        </section>
      </div>

      {bivariate && (
        <section className="card-solid">
          <h3>{t.bivariate}</h3>
          <p className="muted">Pauvreté (lignes) × chômage (colonnes), terciles. {t.demoBadge}</p>
          <div dir="ltr" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, maxWidth: 560 }}>
            {REGIONS.map((r) => {
              const pr = levelOf(r.poverty ?? 0, 18, 39)
              const ch = levelOf(r.unemployment, 22, 30)
              return (
                <div key={r.name} style={{ borderRadius: 10, padding: 12, background: bivColors[pr][ch], textAlign: 'center' }}>
                  <div style={{ fontSize: 12 }}>{r.name}</div>
                  <b>{String(r.unemployment).replace('.', ',')} % / {String(r.poverty).replace('.', ',')} %</b>
                </div>
              )
            })}
          </div>
        </section>
      )}

      <section className="card-solid">
        <h3>{t.tradeTitle}</h3>
        <p className="muted">{t.comtradeTitle} — {t.comtradeText}</p>
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 12, fontSize: 13, cursor: 'pointer' }}>
          <input type="checkbox" checked={showFlows} onChange={(e) => setShowFlows(e.target.checked)} />
          {t.showIllustrative} (désactivé par défaut)
        </label>
        {showFlows && (
          <>
            <p className="muted" style={{ marginTop: 10 }}>Illustratif — à remplacer par les vraies valeurs UN Comtrade Plus. {t.demoBadge}</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 12 }}>
              {TRADE_FLOWS.map((f) => (
                <div key={f.to} style={{ display: 'grid', gridTemplateColumns: '140px 1fr 90px', gap: 12, alignItems: 'center' }}>
                  <span>{f.to}</span>
                  <div style={{ height: 14, borderRadius: 7, background: 'var(--surface-solid)', overflow: 'hidden' }}>
                    <div style={{ width: `${f.share}%`, height: '100%', background: 'linear-gradient(90deg, oklch(65% 0.22 265), oklch(68% 0.18 155))' }} />
                  </div>
                  <b style={{ textAlign: 'end' }}>{f.value} M$ · {f.share} %</b>
                </div>
              ))}
            </div>
          </>
        )}
      </section>
      <section className="card-solid" data-testid="ecoles-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
          <div>
            <h3 style={{ margin: 0 }}>{t.ecoles.title}</h3>
            <p className="muted" style={{ margin: '4px 0 0', fontSize: 12 }}>{t.ecoles.subtitle}</p>
          </div>
          <span className="badge badge-demo">OSM</span>
        </div>
        <EcolesMap t={t} />
        <p className="muted" style={{ marginTop: 10, fontSize: 12 }}>
          ⚠️ {t.ecoles.giga}
        </p>
      </section>

      <p className="muted">Source : {PROVENANCE.unemployment.table} (2024, démo) · {PROVENANCE.population.table} (2024, démo) · {t.loi25}</p>
    </div>
  )
}
