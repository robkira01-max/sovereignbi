import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Dict } from '../lib/i18n'
import { STATCAN_CHOMAGE, STATCAN_IPC, STATCAN_POPULATION, STATCAN_SNAPSHOT_DATE, provinceFr, statcanAttribution } from '../lib/statcan'
import { Provenance } from '../components/Proof'
import { fmt } from '../data/demo'
import { colorForValue, currentTheme, scaleFor, textOnFill, type IndicatorId } from '../lib/theme'

// P-027 — Template Canada (Statistique Canada, données RÉELLES, snapshot local).
// Séparé du dashboard INSTAD Djibouti : aucune série ne mélange les chiffres
// canadiens et les chiffres démo de Djibouti (1 030 000 hab. / 23,5 %).
// Chaque tuile porte sa provenance complète (table, date, licence).
// Aucune requête réseau au chargement : lecture du snapshot local uniquement.
// P-028 : indicateur pilotant les couleurs (chômage / population / IPC) ;
// chaque province est colorée par sa valeur via colorForValue(), sur une
// échelle calculée sur les valeurs affichées, avec légende dynamique.
const INDICATORS: { id: IndicatorId; label: string }[] = [
  { id: 'unemployment', label: 'Chômage' },
  { id: 'population', label: 'Population' },
  { id: 'cpi', label: 'IPC' },
]

export default function CanadaPage({ t, onIndicator }: { t: Dict; onIndicator?: (i: IndicatorId) => void }) {
  const [indicator, setIndicator] = useState<IndicatorId>('unemployment')
  const th = currentTheme()
  const tickMuted = th.vars['--muted-2']
  const tickText = th.vars['--text']
  const setInd = (i: IndicatorId) => { setIndicator(i); onIndicator?.(i) }
  const ch = STATCAN_CHOMAGE
  const pop = STATCAN_POPULATION
  const cpi = STATCAN_IPC
  const prev = new Map(ch.by_province_previous_year.map((r) => [r.province, r.value]))
  const rows = ch.by_province_latest.map((r) => {
    const p = pop.by_province_latest.find((x) => x.province === r.province)
    return { province: provinceFr(r.province), chomage: r.value, chomageAnneeDerniere: prev.get(r.province) ?? null, population: p?.value ?? null }
  })
  // Valeur affichée par province selon l'indicateur (IPC : valeur nationale,
  // pas de ventilation provinciale dans le snapshot — la carte reste sur le chômage).
  const indValues = indicator === 'population' ? rows.map((r) => r.population ?? 0) : rows.map((r) => r.chomage)
  const indUnit = indicator === 'population' ? ' hab.' : ' %'
  const scale = scaleFor(indValues, currentTheme(), indUnit, indicator === 'unemployment'
    ? { reference: ch.canada_latest, referenceLabel: `Référence nationale : ${String(ch.canada_latest).replace('.', ',')} % (oct. 2026, réel)` }
    : { reference: null, referenceLabel: '' })
  const barData = rows.map((r) => ({
    province: r.province,
    taux: indicator === 'population' ? (r.population ?? 0) : r.chomage,
    fill: colorForValue(indicator === 'population' ? (r.population ?? 0) : r.chomage, scale),
  }))

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span className="badge badge-ok">{t.statcanBadge}</span>
          <span className="badge badge-ok">{t.loi25}</span>
          <span className="badge badge-ok">{t.offlineBadge}</span>
        </div>
        <h1 style={{ margin: '8px 0 0', fontSize: 26, fontWeight: 700, letterSpacing: '-.02em' }}>{t.canada}</h1>
        <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 14, lineHeight: 1.6 }}>{t.canadaSub}</p>
        <p style={{ margin: '8px 0 0', fontSize: 13, lineHeight: 1.6, padding: '10px 14px', borderRadius: 12, background: 'oklch(30% 0.09 155 / .5)' }}>
          {t.canadaNote}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 12 }}>
        <div className="card-solid">
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>{t.canadaUnemployment} — oct. 2026</div>
          <div className="kpi-value">{String(ch.canada_latest).replace('.', ',')} %</div>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'oklch(72% 0.17 155)' }}>▼ {(ch.canada_previous_year - ch.canada_latest).toFixed(1).replace('.', ',')} pt vs oct. 2025 ({String(ch.canada_previous_year).replace('.', ',')} %)</div>
          <Provenance table="14-10-0287-01" year={2026} sourceNote={statcanAttribution(ch.title_fr, 'octobre 2026')} />
        </div>
        <div className="card-solid">
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>{t.canadaPopulation} — 1er juill. 2026</div>
          <div className="kpi-value">{fmt(pop.canada_latest)}</div>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'oklch(72% 0.19 55)' }}>▲ {fmt(pop.canada_latest - pop.canada_previous_year)} vs 1er juill. 2025</div>
          <Provenance table="17-10-0009-01" year={2026} sourceNote={statcanAttribution(pop.title_fr, '1er juillet 2026')} />
        </div>
        <div className="card-solid">
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>{t.canadaCpi} — sept. 2026</div>
          <div className="kpi-value">{String(cpi.canada_latest).replace('.', ',')}</div>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'oklch(72% 0.19 55)' }}>▲ {String(cpi.yoy_pct).replace('.', ',')} % sur un an (sept. 2025 : {String(cpi.canada_previous_year).replace('.', ',')})</div>
          <Provenance table="18-10-0004-01" year={2026} sourceNote={statcanAttribution(cpi.title_fr, 'septembre 2026')} />
        </div>
      </div>

      <section className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ fontWeight: 600 }}>{t.canadaByProvince} — {indicator === 'population' ? 'population, 1er juill. 2026' : 'chômage, oct. 2026 (désaisonnalisé)'}</div>
          <div className="view-switch" role="tablist" aria-label="Indicateur">
            {INDICATORS.map((x) => (
              <button key={x.id} className={indicator === x.id ? 'active' : ''} onClick={() => setInd(x.id)}>{x.label}</button>
            ))}
          </div>
        </div>
        {indicator === 'cpi' && <p className="muted" style={{ margin: 0 }}>IPC : pas de ventilation provinciale dans le snapshot (table 18-10-0004-01, Canada seulement) — la carte ci-dessous reste sur le chômage par province.</p>}
        <div dir="ltr" style={{ height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={barData} layout="vertical" margin={{ left: 8, right: 16 }}>
              <CartesianGrid stroke="oklch(25% 0.04 265)" strokeDasharray="3 3" />
              <XAxis type="number" domain={indicator === 'population' ? ['auto', 'auto'] : [0, 10]} tick={{ fill: tickMuted, fontSize: 11 }} />
              <YAxis type="category" dataKey="province" width={150} tick={{ fill: tickText, fontSize: 11 }} />
              <Tooltip contentStyle={{ background: th.vars['--surface-solid'], border: '1px solid var(--border)', borderRadius: 10, color: th.vars['--text'] }} formatter={(v) => [`${fmt(Number(v))}${indUnit}`, indicator === 'population' ? 'Population' : 'Chômage']} />
              <Bar dataKey="taux" radius={[0, 6, 6, 0]}>
                {barData.map((d) => <Cell key={d.province} fill={d.fill} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--muted)' }}>
          <span>{fmt(scale.min)}{indUnit}</span>
          <span className="legend-bar" />
          <span>{fmt(scale.max)}{indUnit}</span>
          <span style={{ marginInlineStart: 8 }}>Médiane : {fmt(scale.median)}{indUnit}{scale.reference !== null ? ` · ${scale.referenceLabel}` : ''}</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 6 }}>
          {rows.map((r) => {
            const v = indicator === 'population' ? (r.population ?? 0) : r.chomage
            return (
              <div key={r.province} style={{ borderRadius: 10, padding: '10px 8px', textAlign: 'center', background: colorForValue(v, scale), color: textOnFill(v, scale) }}>
                <div style={{ fontSize: 11, opacity: 0.9 }}>{r.province}</div>
                <div style={{ fontWeight: 700, fontSize: 15 }}>{fmt(v)}{indUnit}</div>
              </div>
            )
          })}
        </div>
        <Provenance table="14-10-0287-01" year={2026} sourceNote={`${statcanAttribution(ch.title_fr, 'octobre 2026')} · Enquête sur la population active, taux de chômage, 15 ans et plus, désaisonnalisé.`} />
      </section>

      <section className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ fontWeight: 600 }}>{t.canadaTrend} — Canada, oct. 2025 → oct. 2026</div>
        <div dir="ltr" style={{ height: 180 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={ch.trend_canada}>
              <CartesianGrid stroke="oklch(25% 0.04 265)" strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fill: tickMuted, fontSize: 11 }} />
              <YAxis domain={[6, 7.2]} tick={{ fill: tickMuted, fontSize: 11 }} />
              <Tooltip contentStyle={{ background: th.vars['--surface-solid'], border: '1px solid var(--border)', borderRadius: 10, color: th.vars['--text'] }} formatter={(v) => [`${v} %`, 'Chômage']} />
              <Line type="monotone" dataKey="value" stroke="#34d399" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div style={{ fontWeight: 600 }}>{t.canadaCpi} — Canada, sept. 2025 → sept. 2026 (2002 = 100)</div>
        <div dir="ltr" style={{ height: 180 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={cpi.trend_canada}>
              <CartesianGrid stroke="oklch(25% 0.04 265)" strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fill: tickMuted, fontSize: 11 }} />
              <YAxis domain={[164, 171]} tick={{ fill: tickMuted, fontSize: 11 }} />
              <Tooltip contentStyle={{ background: th.vars['--surface-solid'], border: '1px solid var(--border)', borderRadius: 10, color: th.vars['--text'] }} formatter={(v) => [`${v}`, 'IPC']} />
              <Line type="monotone" dataKey="value" stroke="#f59e0b" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <Provenance table="18-10-0004-01" year={2026} sourceNote={`${statcanAttribution(cpi.title_fr, 'septembre 2026')} · Ensemble, Canada, 2002 = 100, non désaisonnalisé.`} />
      </section>

      <section className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ fontWeight: 600 }}>{t.canadaByProvince} — détail</div>
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th>Province</th><th>Chômage oct. 2026 (%)</th><th>Chômage oct. 2025 (%)</th><th>Population 1er juill. 2026</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.province}>
                  <td>{r.province}</td>
                  <td>{String(r.chomage).replace('.', ',')}</td>
                  <td>{r.chomageAnneeDerniere === null ? '—' : String(r.chomageAnneeDerniere).replace('.', ',')}</td>
                  <td>{r.population === null ? '—' : fmt(r.population)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Provenance table="14-10-0287-01 / 17-10-0009-01" year={2026} sourceNote="Sources : Statistique Canada, Caractéristiques de la population active, données mensuelles désaisonnalisées et la tendance-cycle, octobre 2026 ; Statistique Canada, Estimations de la population, trimestrielles, 1er juillet 2026. Licence ouverte de Statistique Canada." />
        <p className="muted">
          Snapshot local du {STATCAN_SNAPSHOT_DATE} — à rafraîchir (voir README, section Statistique Canada). Les chiffres canadiens ci-dessus ne sont jamais mélangés aux chiffres démo de Djibouti. Reproduits fidèlement, sans modification ; toute adaptation future sera marquée « Adapté de Statistique Canada ». Statistique Canada n'approuve ni ne cautionne MizanBI.
        </p>
      </section>
    </div>
  )
}
