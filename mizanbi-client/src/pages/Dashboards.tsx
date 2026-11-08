import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { Dict } from '../lib/i18n'
import { DEMO_DASHBOARDS, PROVENANCE, type Dashboard } from '../data/demo'
import { apiFetch, apiJson, isApiConfigured } from '../lib/api'
import TileRenderer from '../components/TileRenderer'
import { Provenance } from '../components/Proof'

export default function DashboardsPage({ t }: { t: Dict }) {
  const [active, setActive] = useState<Dashboard | null>(null)
  const [exportMsg, setExportMsg] = useState('')
  const q = useQuery({
    queryKey: ['dashboards'],
    queryFn: () => apiJson<Dashboard[] | { dashboards: Dashboard[] }>('/dashboards'),
    enabled: isApiConfigured(),
    retry: false,
  })
  const list: Dashboard[] = q.data ? (Array.isArray(q.data) ? q.data : q.data.dashboards || []) : DEMO_DASHBOARDS
  const dashboards = list.length ? list : DEMO_DASHBOARDS

  const exportBulletin = async () => {
    if (!active) return
    setExportMsg('')
    try {
      const res = await apiFetch(`/dashboards/${active.id}/export/bulletin`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `bulletin-${active.id}.html`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setExportMsg(t.exportFail)
    }
  }

  if (active) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button className="btn-ghost" onClick={() => setActive(null)}>← {t.back}</button>
            <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, letterSpacing: '-.02em' }}>{active.title}</h1>
            <span className="badge badge-demo">{t.demoBadge}</span>
          </div>
          <button className="btn btn-green" onClick={exportBulletin}>↓ {t.bulletin}</button>
        </div>
        {exportMsg && <div style={{ color: 'oklch(72% 0.19 55)' }}>{exportMsg}</div>}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 16 }}>
          {active.tiles.map((tile) => (
            <section key={tile.id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8 }}>
                <h3>{tile.title}</h3>
                <span style={{ fontSize: 11, color: 'oklch(62% 0.03 265)', textTransform: 'uppercase', letterSpacing: '.06em' }}>{tile.type}</span>
              </div>
              <TileRenderer tile={tile} />
              {/* P-023 — provenance sous chaque tuile. */}
              <Provenance
                table={/pauvret/i.test(tile.title) ? PROVENANCE.poverty.table : /population/i.test(tile.title) ? PROVENANCE.population.table : PROVENANCE.unemployment.table}
                year={2024}
                sql={/pauvret/i.test(tile.title) ? PROVENANCE.poverty.sql : /population/i.test(tile.title) ? PROVENANCE.population.sql : PROVENANCE.unemployment.sql}
                confidence="medium"
              />
            </section>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1000, display: 'flex', flexDirection: 'column', gap: 20 }}>
      <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, letterSpacing: '-.02em' }}>{t.dashboards}</h1>
      {!isApiConfigured() && <div style={{ fontSize: 12, color: 'oklch(72% 0.12 55)' }}>{t.offDash}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
        {dashboards.map((d) => (
          <button key={d.id} onClick={() => setActive(d)} className="card" style={{ cursor: 'pointer', textAlign: 'start', color: 'var(--text)', font: 'inherit', display: 'flex', flexDirection: 'column', gap: 8 }}>
            <span style={{ fontWeight: 600, fontSize: 16 }}>{d.title}</span>
            <span style={{ color: 'var(--muted)', fontSize: 13 }}>{d.description}</span>
            <span className="muted">{d.tiles.length} tuiles</span>
          </button>
        ))}
      </div>
    </div>
  )
}
