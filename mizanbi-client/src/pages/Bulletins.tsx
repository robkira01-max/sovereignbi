import { useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Dict } from '../lib/i18n'
import { REGIONS, UNEMPLOYMENT_TREND, WEEKLY_BULLETIN } from '../data/demo'
import { currentTheme } from '../lib/theme'
import { Provenance } from '../components/Proof'
import {
  bieBulletinSection, bcdBulletinSection, statcanBulletinSection,
  renderBulletinHtml, type BulletinSection,
} from '../lib/bulletins'

// P-024 — Digests proactifs : bulletin narratif hebdomadaire démo.
// P-034 — Bulletins enrichis multi-sources : BIE / BCD / StatCan.
// Toutes les fonctions de génération sont dans lib/bulletins.ts (pures, testables).

type Tab = 'weekly' | 'bie' | 'bcd' | 'statcan'

const TREND_COLOR: Record<string, string> = {
  up: 'oklch(72% 0.17 155)',
  down: 'oklch(70% 0.18 25)',
  stable: 'var(--muted)',
}
const TREND_SYM: Record<string, string> = { up: '▲', down: '▼', stable: '→' }

function SectionView({ section }: { section: BulletinSection }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {section.points.map((p) => (
        <div key={p.title} style={{ padding: '12px 16px', borderRadius: 10, background: 'oklch(22% 0.04 265 / .6)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, fontSize: 15 }}>{p.title}</span>
            {p.value && p.trend && (
              <span style={{ fontWeight: 700, color: TREND_COLOR[p.trend], fontSize: 14 }}>
                {TREND_SYM[p.trend]} {p.value}
              </span>
            )}
          </div>
          <p style={{ margin: '4px 0 0', fontSize: 13, lineHeight: 1.7, color: 'var(--muted)' }}>{p.text}</p>
        </div>
      ))}
      <Provenance table={section.id} year={new Date(section.snapshotDate).getFullYear()}
        sourceNote={section.attribution} />
    </div>
  )
}

const TABS: { id: Tab; label: string }[] = [
  { id: 'weekly', label: 'Hebdomadaire (démo)' },
  { id: 'bie', label: 'Économie DJ' },
  { id: 'bcd', label: 'Banques DJ' },
  { id: 'statcan', label: 'Canada' },
]

export default function BulletinsPage({ t }: { t: Dict }) {
  const [tab, setTab] = useState<Tab>('weekly')
  const [exported, setExported] = useState(false)
  const th = currentTheme()
  const tickMuted = th.vars['--muted-2']

  // Build sections lazily (pure — no side effects)
  const sections: BulletinSection[] = [bieBulletinSection(), bcdBulletinSection(), statcanBulletinSection()]
  const activeSection = tab !== 'weekly' ? sections.find((s) => s.id === tab) : null

  const exportAll = () => {
    const html = renderBulletinHtml(sections)
    const url = URL.createObjectURL(new Blob([html], { type: 'text/html' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `bulletin-mizanbi-${new Date().toISOString().slice(0, 10)}.html`
    a.click()
    URL.revokeObjectURL(url)
    setExported(true)
  }

  const exportWeekly = () => {
    const points = WEEKLY_BULLETIN.points.map((p) => `<h2>${p.title}</h2><p>${p.text}</p>`).join('')
    const html = `<!doctype html><html lang="fr"><meta charset="utf-8"><title>MizanBI — Bulletin ${WEEKLY_BULLETIN.week}</title><body style="font-family:system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px"><h1>MizanBI — Bulletin hebdomadaire</h1><p>${WEEKLY_BULLETIN.week} — ${t.demoBadge}.</p>${points}<p><small>Sources : emploi_region, population_region (2024, démo). Conformité Loi 25.</small></p></body></html>`
    const url = URL.createObjectURL(new Blob([html], { type: 'text/html' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'bulletin-mizanbi-weekly.html'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, letterSpacing: '-.02em' }}>{t.bulletins}</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 13 }}>
            Bulletins analytiques multi-sources · {t.loi25}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn-ghost" onClick={tab === 'weekly' ? exportWeekly : exportAll}>
            ↓ {tab === 'weekly' ? t.bulletin : 'Exporter tout'}
          </button>
        </div>
      </div>

      {exported && (
        <div style={{ color: 'oklch(82% 0.15 155)', fontSize: 13 }}>
          ✓ Bulletin HTML téléchargé (auto-suffisant, ouvrable hors ligne).
        </div>
      )}

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        {TABS.map((tb) => (
          <button
            key={tb.id}
            onClick={() => setTab(tb.id)}
            className={tab === tb.id ? 'btn' : 'btn-ghost'}
            style={{ fontSize: 13, padding: '5px 14px' }}
          >
            {tb.label}
          </button>
        ))}
      </div>

      {/* Weekly tab (original) */}
      {tab === 'weekly' && (
        <>
          <section className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <h3 style={{ margin: 0 }}>En trois points — {WEEKLY_BULLETIN.week}</h3>
            {WEEKLY_BULLETIN.points.map((p) => (
              <div key={p.title}>
                <div style={{ fontWeight: 600, fontSize: 15 }}>{p.title}</div>
                <p style={{ margin: '4px 0 0', fontSize: 14, lineHeight: 1.7, color: 'oklch(78% 0.03 265)' }}>{p.text}</p>
              </div>
            ))}
          </section>
          <section className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <h3 style={{ margin: 0 }}>Chômage par région (démo, 2024)</h3>
            <div dir="ltr" style={{ height: 200 }}>
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
            <div className="table-wrap">
              <table className="data">
                <thead><tr><th>Région</th><th>Chômage</th></tr></thead>
                <tbody>
                  {[...REGIONS].sort((a, b) => b.unemployment - a.unemployment).map((r) => (
                    <tr key={r.name}><td>{r.name}</td><td>{String(r.unemployment).replace('.', ',')} %</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted">Sources : emploi_region, population_region (2024, démo). {t.loi25}.</p>
          </section>
        </>
      )}

      {/* Analytics tabs */}
      {activeSection && (
        <section className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <h3 style={{ margin: 0 }}>{activeSection.title}</h3>
          <SectionView section={activeSection} />
        </section>
      )}

      {/* Summary of all data sources */}
      {tab !== 'weekly' && (
        <div className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ fontWeight: 600, fontSize: 14 }}>Toutes les sources ({sections.length} bulletins)</div>
          {sections.map((s) => (
            <div key={s.id} style={{ fontSize: 13, display: 'flex', gap: 8, alignItems: 'baseline' }}>
              <span style={{ fontWeight: 600, minWidth: 90 }}>{s.id.toUpperCase()}</span>
              <span style={{ color: 'var(--muted)' }}>{s.title} · {s.points.length} indicateurs · snapshot {s.snapshotDate}</span>
            </div>
          ))}
          <button className="btn-ghost" style={{ alignSelf: 'flex-start', fontSize: 13 }} onClick={exportAll}>
            ↓ Exporter les {sections.length} bulletins en HTML
          </button>
        </div>
      )}
    </div>
  )
}
