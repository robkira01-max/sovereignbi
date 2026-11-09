import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Dict } from '../lib/i18n'
import { DEMO_TABLES, FORECAST_2030, REGIONS, TOTAL_POPULATION, UNEMPLOYMENT_TREND, WEIGHTED_UNEMPLOYMENT, fmt } from '../data/demo'
import { apiJson, isApiConfigured } from '../lib/api'
import { currentTheme } from '../lib/theme'
import DjiboutiMap from '../components/DjiboutiMap'
import SourceAttribution from '../components/SourceAttribution'

interface Props {
  t: Dict
  go: (page: string) => void
}

export default function HomePage({ t, go }: Props) {
  const [selected, setSelected] = useState<string | null>(null)
  const th = currentTheme()
  const tickMuted = th.vars['--muted-2']
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => apiJson<{ tables?: string[] }>('/api/v1/health'),
    enabled: isApiConfigured(),
    retry: false,
    staleTime: 60_000,
  })
  const tables = health.data?.tables?.length ? health.data.tables : DEMO_TABLES
  const apiStatus = !isApiConfigured() ? t.off : health.isError ? t.off : health.data ? t.live : '…'

  return (
    <div>
      <div className="hero">
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span className="badge badge-demo">{t.demoBadge}</span>
          <span className="badge badge-ok">{t.loi25}</span>
          <span className="badge badge-ok">{t.offlineBadge}</span>
          <span className="badge badge-ok">{apiStatus}</span>
        </div>
        <h1>{t.slogan}</h1>
        <p style={{ margin: 0, color: 'var(--muted)', fontSize: 15 }}>{t.sloganSub}</p>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button className="btn" onClick={() => go('chat')}>{t.ask}</button>
          <button className="btn-ghost" onClick={() => go('dash')}>{t.rep}</button>
          <button className="btn-ghost" onClick={() => go('sig')}>{t.sig}</button>
          <button className="btn-ghost" onClick={() => go('bulletins')}>{t.bulletins}</button>
          <button className="btn-ghost" onClick={() => go('cert')}>{t.certificate}</button>
          <button className="btn-ghost" onClick={() => go('canada')}>{t.canada}</button>
        </div>
        {/* P-026 — Gel pilote + modèle commercial. */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 12 }}>
          <div style={{ padding: '12px 16px', borderRadius: 12, background: 'oklch(34% 0.08 55 / .5)', fontSize: 13, lineHeight: 1.6 }}>
            <b>{t.gelTitle}.</b> {t.gelText}
          </div>
          <div style={{ padding: '12px 16px', borderRadius: 12, background: 'oklch(30% 0.09 155 / .5)', fontSize: 13, lineHeight: 1.6 }}>
            <b>{t.licenceTitle}.</b> {t.licenceText}
          </div>
        </div>
      </div>

      <div className="bento">
        <div className="card-solid span2" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <span style={{ fontWeight: 600 }}>{t.mapTitle}</span>
            <span style={{ fontSize: 11, color: 'var(--muted)' }}>{apiStatus}</span>
          </div>
          <DjiboutiMap selected={selected} onSelect={setSelected} />
        </div>

        <div className="card-solid span2" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 600 }}>{t.trend}</span>
            <span style={{ color: 'oklch(78% 0.17 155)', fontWeight: 600 }}>▼ 5,4 pt</span>
          </div>
          <div dir="ltr" style={{ flex: 1, minHeight: 180 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={UNEMPLOYMENT_TREND}>
                <CartesianGrid stroke="oklch(25% 0.04 265)" strokeDasharray="3 3" />
                <XAxis dataKey="year" tick={{ fill: tickMuted, fontSize: 11 }} />
                <YAxis domain={[20, 30]} tick={{ fill: tickMuted, fontSize: 11 }} />
                <Tooltip contentStyle={{ background: th.vars['--surface-solid'], border: '1px solid var(--border)', borderRadius: 10, color: th.vars['--text'] }} formatter={(v) => [`${v} %`, 'Chômage']} />
                <Line type="monotone" dataKey="rate" stroke="#34d399" strokeWidth={2.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <SourceAttribution source="INSTAD / BIE" year="2026" />
        </div>

        <div className="card-solid">
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>{t.avgUnemployment}</div>
          <div className="kpi-value">{String(WEIGHTED_UNEMPLOYMENT).replace('.', ',')} %</div>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'oklch(72% 0.17 155)' }}>▼ 1,4 pt</div>
        </div>
        <div className="card-solid">
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>{t.population}</div>
          <div className="kpi-value">1,03 M</div>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'oklch(72% 0.19 55)' }}>▲ 2,1 %</div>
        </div>
        <div className="card-solid">
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>{t.tables}</div>
          <div className="kpi-value">{tables.length}</div>
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>{t.regions} : 6</div>
        </div>
        <div className="card-solid">
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>{t.dashboards}</div>
          <div className="kpi-value">2</div>
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>8 + 4 tuiles</div>
        </div>

        <div className="card-solid span4" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600 }}>{t.forecast}</span>
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>{t.forecastNote}</span>
          </div>
          <div style={{ display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ minWidth: 130 }}>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>2030</div>
              <div style={{ fontSize: 34, fontWeight: 700, letterSpacing: '-.02em', color: 'oklch(82% 0.15 65)' }}>{String(FORECAST_2030.value).replace('.', ',')} %</div>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>IC {String(FORECAST_2030.ciLow).replace('.', ',')} – {FORECAST_2030.ciHigh}</div>
            </div>
            <div dir="ltr" style={{ flex: 1, minWidth: 240, height: 110 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={[...UNEMPLOYMENT_TREND, { year: 2030, rate: FORECAST_2030.value }]}>
                  <CartesianGrid stroke="oklch(25% 0.04 265)" strokeDasharray="3 3" />
                  <XAxis dataKey="year" tick={{ fill: tickMuted, fontSize: 11 }} />
                  <YAxis domain={[18, 30]} tick={{ fill: tickMuted, fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: th.vars['--surface-solid'], border: '1px solid var(--border)', borderRadius: 10, color: th.vars['--text'] }} />
                  <Line type="monotone" dataKey="rate" stroke="#f59e0b" strokeWidth={2.5} strokeDasharray="6 5" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          <SourceAttribution source="INSTAD / BIE" year="2026" note="Prévision modèle linéaire" />
        </div>

        <div className="card-solid span4" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600 }}>{t.bie}</span>
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>{t.bieBadge}</span>
          </div>
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6 }}>{t.bieSub}</p>
          <div><button className="btn" onClick={() => go('bie')}>{t.bie} →</button></div>
        </div>

        <div className="card-solid span4" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600 }}>{t.bcd}</span>
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>{t.bcdBadge}</span>
          </div>
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6 }}>{t.bcdSub}</p>
          <div><button className="btn" onClick={() => go('bcd')}>{t.bcd} →</button></div>
        </div>

        <div className="card-solid span4" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600 }}>{t.canada}</span>
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>{t.statcanBadge}</span>
          </div>
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6 }}>{t.canadaSub}</p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button className="btn" onClick={() => go('canada')}>{t.canada} →</button>
            <button className="btn-ghost" onClick={() => go('canadanat')}>{t.canadaNational} →</button>
          </div>
        </div>

        <div className="card-solid span4" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ fontWeight: 600 }}>{t.tables}</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {tables.map((tb) => <span key={tb} className="pill">{tb}</span>)}
          </div>
          <div className="muted">
            {t.demoBadge} — {REGIONS.map((r) => `${r.name} ${fmt(r.population)} hab.`).join(' · ')} — Total : {fmt(TOTAL_POPULATION)} hab.
          </div>
        </div>
      </div>
    </div>
  )
}
