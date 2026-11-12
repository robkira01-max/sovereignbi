/**
 * DashboardsPage — P-051.
 * Demo mode (no VITE_API_BASE): DEMO_DASHBOARDS + demo TileRenderer (read-only).
 * Live mode: full CRUD — tile drag/reorder, add, delete, notes, source, tags,
 *            favourites, freshness indicator, AI insights, bulletin/PPTX/CSV exports.
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import type { Dict } from '../lib/i18n'
import {
  api, apiFetch, apiJson, authHeaders, getApiBase, isApiConfigured,
  type Dashboard, type DashboardSummary, type Tile, type TileData,
} from '../lib/api'
import { DEMO_DASHBOARDS } from '../data/demo'
import DemoTileRenderer from '../components/TileRenderer'
import { LiveTileRenderer } from '../components/LiveTileRenderer'
import { tileDataToCsv, dashboardToBulletinHtml, triggerDownload } from '../lib/exports'

const TILE_TYPES = ['kpi', 'bar', 'line', 'pie', 'table', 'map', 'map-adm2', 'map-bivariate', 'heatmap', 'grid']

type TileDataMap = Record<string, TileData>
type InsightMap = Record<string, string>
type InsightResponse = { insight: string; tile_id: string; cached: boolean }

const byPosition = (a: Tile, b: Tile) => (a.position ?? 999) - (b.position ?? 999)

// ── Demo mode (no API) ────────────────────────────────────────────────────────

function DemoDashboardsList({ t, onOpen }: { t: Dict; onOpen: (d: (typeof DEMO_DASHBOARDS)[0]) => void }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
      {DEMO_DASHBOARDS.map(d => (
        <button key={d.id} onClick={() => onOpen(d)} className="card"
          style={{ cursor: 'pointer', textAlign: 'start', color: 'var(--text)', font: 'inherit', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <span style={{ fontWeight: 600, fontSize: 15 }}>{d.title}</span>
          <span style={{ color: 'var(--muted)', fontSize: 13 }}>{d.description}</span>
          <span className="muted">{d.tiles.length} tuiles</span>
        </button>
      ))}
    </div>
  )
}

function DemoDashboardDetail({ t, dash, onBack }: {
  t: Dict
  dash: (typeof DEMO_DASHBOARDS)[0]
  onBack: () => void
}) {
  const exportBulletin = () => {
    const html = dashboardToBulletinHtml(dash.title, dash.tiles)
    triggerDownload(html, `bulletin-${dash.id}.html`, 'text/html;charset=utf-8')
  }

  const exportTileCsv = (tile: (typeof dash.tiles)[0]) => {
    if (!tile.data) return
    const csv = tileDataToCsv(tile.title, tile.data)
    triggerDownload(csv, `${tile.id}.csv`, 'text/csv;charset=utf-8', true)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn-ghost" onClick={onBack}>← {t.back}</button>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{dash.title}</h1>
          <span className="badge badge-demo">{t.demoBadge}</span>
        </div>
        <button className="btn btn-green" onClick={exportBulletin}>↓ {t.bulletin}</button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%,300px),1fr))', gap: 16 }}>
        {dash.tiles.map(tile => (
          <section key={tile.id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8 }}>
              <h3 style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>{tile.title}</h3>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <span style={{ fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase' }}>{tile.type}</span>
                {tile.data && (
                  <button className="btn-ghost" style={{ fontSize: 10, padding: '2px 6px' }}
                    onClick={() => exportTileCsv(tile)} title="Télécharger CSV">
                    CSV
                  </button>
                )}
              </div>
            </div>
            <DemoTileRenderer tile={tile} />
          </section>
        ))}
      </div>
    </div>
  )
}

// ── Live mode (API available) ─────────────────────────────────────────────────

function LiveDashboardPage({ t }: { t: Dict }) {
  const [summaries, setSummaries] = useState<DashboardSummary[]>([])
  const [selected, setSelected] = useState<Dashboard | null>(null)
  const [tiles, setTiles] = useState<Tile[]>([])
  const [tileData, setTileData] = useState<TileDataMap>({})
  const [insights, setInsights] = useState<InsightMap>({})
  const [loadingInsights, setLoadingInsights] = useState<Record<string, boolean>>({})
  const [freshness, setFreshness] = useState<Record<string, { age_seconds: number | null; stale: boolean }>>({})
  const [noteEditing, setNoteEditing] = useState<Record<string, boolean>>({})
  const [noteText, setNoteText] = useState<Record<string, string>>({})
  const [tagFilter, setTagFilter] = useState('')
  const [tagEditing, setTagEditing] = useState(false)
  const [tagInput, setTagInput] = useState('')
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [newTile, setNewTile] = useState({ id: '', type: 'kpi', title: '' })
  const dragIdx = useRef<number | null>(null)

  useEffect(() => {
    api.dashboards().then(setSummaries).catch(e => setError((e as Error).message))
  }, [])

  const loadTileData = useCallback(async (dashId: string, tileList: Tile[], region?: string | null) => {
    const MAP_TYPES = new Set(['map', 'map-adm2', 'map-bivariate', 'trade-flow-map'])
    const results = await Promise.allSettled(
      tileList.map(async tile => {
        const qs = region && !MAP_TYPES.has(tile.type) ? `?region=${encodeURIComponent(region)}` : ''
        const data = await apiJson<TileData>(`/dashboards/${dashId}/tiles/${tile.id}/data${qs}`)
        return { id: tile.id, data }
      })
    )
    const map: TileDataMap = {}
    for (const res of results) {
      if (res.status === 'fulfilled') map[res.value.id] = res.value.data
    }
    setTileData(map)
    // freshness — best-effort, non-blocking
    Promise.allSettled(
      tileList.map(async tile => {
        const f = await apiJson<{ age_seconds: number | null; stale: boolean }>(`/dashboards/${dashId}/tiles/${tile.id}/freshness`)
        return { id: tile.id, f }
      })
    ).then(res => {
      const fm: Record<string, { age_seconds: number | null; stale: boolean }> = {}
      for (const r of res) { if (r.status === 'fulfilled') fm[r.value.id] = r.value.f }
      setFreshness(fm)
    }).catch(() => undefined)
  }, [])

  const loadInsights = useCallback(async (dashId: string, tileList: Tile[]) => {
    for (const tile of tileList) {
      if (tile.type === 'kpi') continue
      setLoadingInsights(prev => ({ ...prev, [tile.id]: true }))
      try {
        const json = await apiJson<InsightResponse>(`/dashboards/${dashId}/tiles/${tile.id}/insight`)
        if (json.insight) setInsights(prev => ({ ...prev, [tile.id]: json.insight }))
      } catch { /* LLM indisponible */ }
      finally { setLoadingInsights(prev => ({ ...prev, [tile.id]: false })) }
    }
  }, [])

  const exportBulletin = async () => {
    if (!selected) return
    setExporting(true)
    try {
      const res = await fetch(`${getApiBase()}/dashboards/${selected.id}/export/bulletin`, { headers: authHeaders() })
      if (!res.ok) throw new Error(`${res.status}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.target = '_blank'
      a.download = `${selected.id}-bulletin.html`; a.click()
      setTimeout(() => URL.revokeObjectURL(url), 10000)
    } catch (e) { setError(e instanceof Error ? e.message : 'Erreur export bulletin') }
    finally { setExporting(false) }
  }

  const exportPptx = async () => {
    if (!selected) return
    setExporting(true)
    try {
      const res = await fetch(`${getApiBase()}/dashboards/${selected.id}/export/pptx`, { headers: authHeaders() })
      if (!res.ok) throw new Error(`${res.status}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = `${selected.id}.pptx`; a.click()
      setTimeout(() => URL.revokeObjectURL(url), 10000)
    } catch (e) { setError(e instanceof Error ? e.message : 'Erreur export PPTX') }
    finally { setExporting(false) }
  }

  const exportTileCsv = async (tileId: string) => {
    if (!selected) return
    try {
      const res = await fetch(`${getApiBase()}/dashboards/${selected.id}/tiles/${tileId}/export/csv`, { headers: authHeaders() })
      if (!res.ok) throw new Error(`${res.status}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = `${selected.id}-${tileId}.csv`; a.click()
      setTimeout(() => URL.revokeObjectURL(url), 10000)
    } catch (e) { setError(e instanceof Error ? e.message : 'Erreur export CSV') }
  }

  const cloneDashboard = async () => {
    if (!selected) return
    try {
      const res = await fetch(`${getApiBase()}/dashboards/${selected.id}/clone`,
        { method: 'POST', headers: { 'Content-Type': 'application/json', ...authHeaders() }, body: '{}' })
      if (!res.ok) throw new Error(`${res.status}`)
      const data = await res.json() as { id: string }
      api.dashboards().then(setSummaries).catch(() => undefined)
      alert(`Dashboard cloné : ${data.id}`)
    } catch (e) { setError(e instanceof Error ? e.message : 'Erreur clonage') }
  }

  useEffect(() => {
    if (!selected || tiles.length === 0) return
    loadTileData(selected.id, tiles, selectedRegion)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRegion])

  const openDashboard = (id: string) => {
    api.getDashboard(id)
      .then(d => {
        const sorted = [...d.tiles].sort(byPosition)
        setSelected(d); setTiles(sorted); setTileData({}); setInsights({}); setSelectedRegion(null)
        loadTileData(id, sorted)
        setTimeout(() => loadInsights(id, sorted), 300)
      })
      .catch(e => setError((e as Error).message))
  }

  const onDragStart = (i: number) => { dragIdx.current = i }
  const onDrop = (i: number) => {
    const from = dragIdx.current
    if (from == null || from === i) return
    const next = [...tiles]
    const [moved] = next.splice(from, 1)
    next.splice(i, 0, moved)
    const reordered = next.map((tile, idx) => ({ ...tile, position: idx }))
    setTiles(reordered); dragIdx.current = null
    if (!selected) return
    setSaving(true)
    api.patchLayout(selected.id, reordered.map((tile, idx) => ({ id: tile.id, position: idx })))
      .catch(e => setError((e as Error).message))
      .finally(() => setSaving(false))
  }

  const removeTile = (tileId: string) => {
    if (!selected) return
    setSaving(true)
    api.removeTile(selected.id, tileId)
      .then(() => {
        setTiles(prev => prev.filter(t => t.id !== tileId))
        setTileData(prev => { const n = { ...prev }; delete n[tileId]; return n })
        setInsights(prev => { const n = { ...prev }; delete n[tileId]; return n })
      })
      .catch(e => setError((e as Error).message))
      .finally(() => setSaving(false))
  }

  const submitAdd = () => {
    if (!selected || !newTile.id || !newTile.title) return
    setSaving(true)
    api.addTile(selected.id, { ...newTile, position: tiles.length })
      .then(() => {
        setTiles(prev => [...prev, { ...newTile, position: tiles.length }])
        setNewTile({ id: '', type: 'kpi', title: '' }); setShowAdd(false)
      })
      .catch(e => setError((e as Error).message))
      .finally(() => setSaving(false))
  }

  const startNoteEdit = (tileId: string, current: string | null | undefined) => {
    setNoteText(prev => ({ ...prev, [tileId]: current ?? '' }))
    setNoteEditing(prev => ({ ...prev, [tileId]: true }))
  }

  const saveTileNote = (tileId: string) => {
    if (!selected) return
    api.setTileNote(selected.id, tileId, noteText[tileId] ?? '')
      .then(res => {
        setTiles(prev => prev.map(t => t.id === tileId ? { ...t, note: res.note } : t))
        setNoteEditing(prev => ({ ...prev, [tileId]: false }))
      })
      .catch(e => setError(e instanceof Error ? e.message : 'Erreur note'))
  }

  const saveTags = () => {
    if (!selected) return
    const tags = tagInput.split(',').map(s => s.trim()).filter(Boolean)
    api.setDashboardTags(selected.id, tags)
      .then(res => {
        setSummaries(prev => prev.map(s => s.id === selected.id ? { ...s, tags: res.tags } : s))
        setTagEditing(false)
      })
      .catch(e => setError(e instanceof Error ? e.message : 'Erreur tags'))
  }

  const filteredSummaries = tagFilter
    ? summaries.filter(d => (d.tags ?? []).includes(tagFilter.trim()))
    : summaries

  // ── List view ───────────────────────────────────────────────────────────────
  if (!selected) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, letterSpacing: '-.02em' }}>{t.dashboard.title}</h1>
        {error && (
          <div style={{ background: 'oklch(18% 0.06 25 / 0.7)', border: '1px solid var(--danger)', borderRadius: 10, padding: '8px 14px', fontSize: 13, color: 'oklch(85% 0.12 25)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>{error}</span>
            <button onClick={() => setError('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 16 }}>×</button>
          </div>
        )}
        <input
          data-testid="tag-filter-input"
          className="input"
          type="text"
          value={tagFilter}
          onChange={e => setTagFilter(e.target.value)}
          placeholder={t.dashboard.tagsFilterPlaceholder}
          style={{ maxWidth: 320 }}
        />
        {filteredSummaries.length === 0 && (
          <div style={{ color: 'var(--muted)', fontSize: 13 }}>{t.dashboard.noDashboards}</div>
        )}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
          {filteredSummaries.map(d => (
            <div key={d.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
              <button onClick={() => openDashboard(d.id)} className="card"
                style={{ cursor: 'pointer', textAlign: 'start', color: 'var(--text)', font: 'inherit', display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
                <span style={{ fontWeight: 600, fontSize: 15 }}>{d.title}</span>
                <span style={{ color: 'var(--muted)', fontSize: 12 }}>{d.scope}</span>
                {(d.tags ?? []).length > 0 && (
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {(d.tags ?? []).map(tag => (
                      <span key={tag} data-testid={`tag-chip-${d.id}-${tag}`}
                        onClick={e => { e.stopPropagation(); setTagFilter(tag) }}
                        style={{ padding: '1px 7px', background: 'oklch(25% 0.08 265 / 0.6)', color: 'oklch(72% 0.15 265)', borderRadius: 999, fontSize: 10, cursor: 'pointer' }}>
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </button>
              <button
                data-testid={`fav-${d.id}`}
                onClick={() => api.toggleFavorite(d.id).then(res => setSummaries(prev => prev.map(s => s.id === d.id ? { ...s, is_favorite: res.is_favorite } : s)))}
                title={d.is_favorite ? t.dashboard.unfavorite : t.dashboard.favorite}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem', padding: '10px 4px', lineHeight: 1, color: d.is_favorite ? 'oklch(72% 0.19 55)' : 'var(--muted)', flexShrink: 0 }}
              >★</button>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // ── Detail view ─────────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <button className="btn-ghost" onClick={() => { setSelected(null); setShowAdd(false) }}>← {t.back}</button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>{selected.title}</h2>
          {/* Tags row */}
          {tagEditing ? (
            <div style={{ display: 'flex', gap: 6, marginTop: 4, alignItems: 'center' }}>
              <input data-testid="tag-edit-input" className="input" value={tagInput}
                onChange={e => setTagInput(e.target.value)} placeholder={t.dashboard.tagsPlaceholder}
                style={{ fontSize: 11, padding: '3px 8px', flex: 1, maxWidth: 220 }} />
              <button onClick={saveTags} className="btn" style={{ fontSize: 11, padding: '3px 10px' }}>{t.dashboard.save}</button>
              <button onClick={() => setTagEditing(false)} className="btn-ghost" style={{ fontSize: 11, padding: '3px 8px' }}>{t.dashboard.cancel}</button>
            </div>
          ) : (
            <div style={{ marginTop: 4, display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
              {summaries.find(s => s.id === selected.id)?.tags?.map(tag => (
                <span key={tag} style={{ padding: '1px 7px', background: 'oklch(25% 0.08 265 / 0.6)', color: 'oklch(72% 0.15 265)', borderRadius: 999, fontSize: 10 }}>{tag}</span>
              ))}
              <button data-testid="tag-edit-btn"
                onClick={() => { const tags = summaries.find(s => s.id === selected.id)?.tags ?? []; setTagInput(tags.join(', ')); setTagEditing(true) }}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 10, padding: '2px 0' }}>
                ✎ {t.dashboard.tagsLabel}
              </button>
            </div>
          )}
        </div>
        {saving && <span style={{ fontSize: 11, color: 'var(--muted)' }}>{t.dashboard.saving}</span>}
        <button onClick={exportBulletin} disabled={exporting} className="btn btn-green" style={{ fontSize: 12, padding: '6px 14px', opacity: exporting ? 0.6 : 1 }}>
          {exporting ? '…' : t.dashboard.exportBulletin}
        </button>
        <button data-testid="clone-dashboard-btn" onClick={cloneDashboard} className="btn" style={{ fontSize: 12, padding: '6px 14px', background: 'oklch(50% 0.15 200)' }}>
          {t.dashboard.clone}
        </button>
        <button data-testid="export-pptx-btn" onClick={exportPptx} disabled={exporting} className="btn" style={{ fontSize: 12, padding: '6px 14px', background: 'oklch(48% 0.17 295)', opacity: exporting ? 0.6 : 1 }}>
          {exporting ? '…' : t.dashboard.exportPptx}
        </button>
        <button onClick={() => setShowAdd(v => !v)} className="btn" style={{ fontSize: 12, padding: '6px 14px' }}>
          {t.dashboard.addTile}
        </button>
      </div>

      {error && (
        <div style={{ background: 'oklch(18% 0.06 25 / 0.7)', border: '1px solid var(--danger)', borderRadius: 10, padding: '8px 14px', fontSize: 13, color: 'oklch(85% 0.12 25)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{error}</span>
          <button onClick={() => setError('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 16 }}>×</button>
        </div>
      )}

      {/* Add tile form */}
      {showAdd && (
        <div className="card-solid" style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12 }}>
            {t.dashboard.idLabel}
            <input className="input" value={newTile.id} onChange={e => setNewTile(p => ({ ...p, id: e.target.value }))}
              placeholder={t.dashboard.tileIdPlaceholder} style={{ fontSize: 12, padding: '5px 8px' }} />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12 }}>
            {t.dashboard.titleLabel}
            <input className="input" value={newTile.title} onChange={e => setNewTile(p => ({ ...p, title: e.target.value }))}
              placeholder={t.dashboard.tileTitlePlaceholder} style={{ fontSize: 12, padding: '5px 8px' }} />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12 }}>
            {t.dashboard.typeLabel}
            <select className="input" value={newTile.type} onChange={e => setNewTile(p => ({ ...p, type: e.target.value }))} style={{ fontSize: 12, padding: '5px 8px' }}>
              {TILE_TYPES.map(tp => <option key={tp} value={tp}>{tp}</option>)}
            </select>
          </label>
          <button onClick={submitAdd} disabled={!newTile.id || !newTile.title} className="btn btn-green" style={{ fontSize: 12, padding: '7px 14px' }}>
            {t.dashboard.save}
          </button>
          <button onClick={() => setShowAdd(false)} className="btn-ghost" style={{ fontSize: 12, padding: '7px 10px' }}>{t.dashboard.cancel}</button>
        </div>
      )}

      {/* Region filter badge */}
      {selectedRegion && (
        <div data-testid="region-filter-badge" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '4px 12px', background: 'oklch(22% 0.07 265 / 0.6)', border: '1px solid oklch(50% 0.15 265 / 0.5)', borderRadius: 999, fontSize: 11, color: 'oklch(72% 0.15 265)' }}>
          <span>📍 {t.dashboard.regionFilter.replace('{region}', selectedRegion)}</span>
          <button data-testid="region-filter-clear" onClick={() => setSelectedRegion(null)} title={t.dashboard.regionFilterClear}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', padding: 0, lineHeight: 1, fontSize: 13 }}>×</button>
        </div>
      )}

      <div style={{ fontSize: 11, color: 'var(--muted)' }}>{t.dashboard.dragHint}</div>

      {/* Tile grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
        {tiles.map((tile, i) => {
          const data = tileData[tile.id] ?? { columns: [], rows: [] }
          const insight = insights[tile.id]
          const insightLoading = loadingInsights[tile.id]
          const tileAge = freshness[tile.id]
          const freshnessColor = !tileAge ? 'var(--muted)'
            : tileAge.stale ? 'var(--danger)'
            : (tileAge.age_seconds ?? 9999) < 300 ? 'oklch(68% 0.18 155)'
            : 'oklch(72% 0.19 55)'
          const freshnessTitle = !tileAge ? t.dashboard.freshnessUnknown
            : tileAge.stale ? t.dashboard.freshnessStale
            : `${Math.round(tileAge.age_seconds ?? 0)}s`

          return (
            <div key={tile.id} draggable
              onDragStart={() => onDragStart(i)}
              onDragOver={e => e.preventDefault()}
              onDrop={() => onDrop(i)}
              data-tile-id={tile.id}
              className="card"
              style={{ cursor: 'grab', display: 'flex', flexDirection: 'column', gap: 10, position: 'relative' }}
            >
              {/* Tile header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <h4 style={{ margin: 0, fontSize: 12, fontWeight: 600, flex: 1, color: 'var(--text)' }}>{tile.title}</h4>
                <span data-testid={`freshness-dot-${tile.id}`} title={freshnessTitle}
                  style={{ display: 'inline-block', width: 7, height: 7, borderRadius: '50%', background: freshnessColor, margin: '3px 4px 0', flexShrink: 0 }} />
                <button data-testid={`export-csv-${tile.id}`} onClick={() => exportTileCsv(tile.id)}
                  title={t.dashboard.exportCsv}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 10, padding: '0 3px', lineHeight: 1 }}>
                  ↓ CSV
                </button>
                <button onClick={() => removeTile(tile.id)} title={t.dashboard.deleteTile}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 15, padding: '0 3px', lineHeight: 1 }}>×</button>
              </div>
              <div style={{ fontSize: 10, color: 'var(--muted-2)' }}>{tile.type}{tile.position != null ? ` · pos ${tile.position}` : ''}</div>

              <LiveTileRenderer
                type={tile.type}
                title={tile.title}
                data={data}
                options={tile.options}
                onRegionSelect={name => setSelectedRegion(prev => prev === name ? null : name)}
                selectedRegion={selectedRegion}
              />

              {/* AI insight */}
              {insightLoading && tile.type !== 'kpi' && (
                <div style={{ fontSize: 11, color: 'var(--muted)', borderTop: '1px solid var(--border)', paddingTop: 6, marginTop: 2 }}>✦ …</div>
              )}
              {insight && (
                <div style={{ fontSize: 11, color: 'var(--text)', lineHeight: 1.5, borderTop: '1px solid var(--border)', paddingTop: 6, marginTop: 2 }}>
                  <span style={{ display: 'inline-block', background: 'oklch(28% 0.1 265)', color: 'oklch(72% 0.18 265)', borderRadius: 4, padding: '1px 5px', fontSize: 9, fontWeight: 700, marginInlineEnd: 5, letterSpacing: '0.03em' }}>IA</span>
                  {insight}
                </div>
              )}

              {/* Analyst note */}
              {noteEditing[tile.id] ? (
                <div data-testid={`note-editor-${tile.id}`} style={{ marginTop: 4 }}>
                  <textarea data-testid={`note-textarea-${tile.id}`}
                    value={noteText[tile.id] ?? ''}
                    onChange={e => setNoteText(prev => ({ ...prev, [tile.id]: e.target.value }))}
                    placeholder={t.dashboard.tileNotePlaceholder}
                    maxLength={1000} rows={3}
                    className="input" style={{ width: '100%', fontSize: 11, resize: 'vertical', boxSizing: 'border-box' }} />
                  <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                    <button onClick={() => saveTileNote(tile.id)} className="btn" style={{ fontSize: 11, padding: '3px 10px' }}>{t.dashboard.save}</button>
                    <button onClick={() => setNoteEditing(prev => ({ ...prev, [tile.id]: false }))} className="btn-ghost" style={{ fontSize: 11, padding: '3px 8px' }}>{t.dashboard.cancel}</button>
                  </div>
                </div>
              ) : (
                <div style={{ marginTop: 4 }}>
                  {tile.source && (
                    <p data-testid={`tile-source-${tile.id}`} style={{ fontSize: 10, color: 'var(--muted-2)', margin: '0 0 2px', lineHeight: 1.4 }}>
                      <strong>{t.dashboard.sourceLabel}</strong> {tile.source}
                    </p>
                  )}
                  {tile.note && (
                    <p data-testid={`tile-note-${tile.id}`} style={{ fontSize: 11, color: 'var(--muted)', margin: 0, lineHeight: 1.4, fontStyle: 'italic' }}>
                      {tile.note}
                    </p>
                  )}
                  <button data-testid={`note-edit-btn-${tile.id}`} onClick={() => startNoteEdit(tile.id, tile.note)}
                    title={t.dashboard.tileNoteEdit}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', fontSize: 10, padding: '2px 0', marginTop: 2 }}>
                    ✎ {t.dashboard.tileNote}
                  </button>
                </div>
              )}
            </div>
          )
        })}
        {tiles.length === 0 && (
          <div style={{ color: 'var(--muted)', gridColumn: '1/-1', fontSize: 13 }}>{t.dashboard.noTiles}</div>
        )}
      </div>
    </div>
  )
}

// ── Page entry point ──────────────────────────────────────────────────────────

export default function DashboardsPage({ t }: { t: Dict }) {
  const live = isApiConfigured()
  const [demoActive, setDemoActive] = useState<(typeof DEMO_DASHBOARDS)[0] | null>(null)

  if (!live) {
    if (demoActive) {
      return <DemoDashboardDetail t={t} dash={demoActive} onBack={() => setDemoActive(null)} />
    }
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700 }}>{t.dashboard.title}</h1>
        <div style={{ fontSize: 12, color: 'var(--warning)' }}>{t.offDash}</div>
        <DemoDashboardsList t={t} onOpen={d => setDemoActive(d)} />
      </div>
    )
  }

  return <LiveDashboardPage t={t} />
}
