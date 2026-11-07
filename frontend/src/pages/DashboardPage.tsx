import { useEffect, useRef, useState, useCallback } from 'react'
import { api, apiFetch, getApiBase, getKey } from '../api/client'

type InsightResponse = { insight: string; tile_id: string; cached: boolean }
import type { Dashboard, DashboardSummary, Tile } from '../api/client'
import { TileRenderer } from '../components/TileRenderer'
import { useLocale } from '../hooks/useLocale'

const TILE_TYPES = ['kpi', 'bar', 'line', 'pie', 'table', 'map']

type TileData = { columns: string[]; rows: unknown[][] }
type TileDataMap = Record<string, TileData>
type InsightMap = Record<string, string>

export function DashboardPage() {
  const { t } = useLocale()
  const [summaries, setSummaries] = useState<DashboardSummary[]>([])
  const [selected, setSelected] = useState<Dashboard | null>(null)
  const [tiles, setTiles] = useState<Tile[]>([])
  const [tileData, setTileData] = useState<TileDataMap>({})
  const [insights, setInsights] = useState<InsightMap>({})
  const [loadingInsights, setLoadingInsights] = useState<Record<string, boolean>>({})
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [newTile, setNewTile] = useState({ id: '', type: 'kpi', title: '' })
  const dragIdx = useRef<number | null>(null)

  useEffect(() => {
    api.dashboards()
      .then(setSummaries)
      .catch(e => setError(e.message))
  }, [])

  const byPosition = (a: Tile, b: Tile) => (a.position ?? 999) - (b.position ?? 999)

  // Load all tile data in parallel
  const loadTileData = useCallback(async (dashId: string, tileList: Tile[]) => {
    const results = await Promise.allSettled(
      tileList.map(async tile => {
        const data = await apiFetch<TileData>(`/dashboards/${dashId}/tiles/${tile.id}/data`)
        return { id: tile.id, data }
      })
    )
    const map: TileDataMap = {}
    for (const res of results) {
      if (res.status === 'fulfilled') {
        map[res.value.id] = res.value.data
      }
    }
    setTileData(map)
  }, [])

  // Load insights sequentially to avoid LLM overload (non-blocking)
  const loadInsights = useCallback(async (dashId: string, tileList: Tile[]) => {
    for (const tile of tileList) {
      if (tile.type === 'kpi') continue // number speaks for itself
      setLoadingInsights(prev => ({ ...prev, [tile.id]: true }))
      try {
        const json = await apiFetch<InsightResponse>(`/dashboards/${dashId}/tiles/${tile.id}/insight`)
        if (json.insight) {
          setInsights(prev => ({ ...prev, [tile.id]: json.insight }))
        }
      } catch {
        // LLM unavailable — skip silently
      } finally {
        setLoadingInsights(prev => ({ ...prev, [tile.id]: false }))
      }
    }
  }, [])

  const exportBulletin = async () => {
    if (!selected) return
    setExporting(true)
    try {
      const key = getKey()
      const res = await fetch(
        `${getApiBase()}/dashboards/${selected.id}/export/bulletin`,
        { headers: { 'X-Api-Key': key, 'Authorization': key ? `Bearer ${key}` : '' } }
      )
      if (!res.ok) throw new Error(`${res.status}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.target = '_blank'
      a.download = `${selected.id}-bulletin.html`
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 10000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur export bulletin')
    } finally {
      setExporting(false)
    }
  }

  const exportPptx = async () => {
    if (!selected) return
    setExporting(true)
    try {
      const key = getKey()
      const res = await fetch(
        `${getApiBase()}/dashboards/${selected.id}/export/pptx`,
        { headers: { 'X-Api-Key': key, 'Authorization': key ? `Bearer ${key}` : '' } }
      )
      if (!res.ok) throw new Error(`${res.status}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${selected.id}.pptx`
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 10000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur export PPTX')
    } finally {
      setExporting(false)
    }
  }

  const exportTileCsv = async (tileId: string) => {
    if (!selected) return
    try {
      const key = getKey()
      const res = await fetch(
        `${getApiBase()}/dashboards/${selected.id}/tiles/${tileId}/export/csv`,
        { headers: { 'X-Api-Key': key, 'Authorization': key ? `Bearer ${key}` : '' } }
      )
      if (!res.ok) throw new Error(`${res.status}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${selected.id}-${tileId}.csv`
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 10000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur export CSV')
    }
  }

  const cloneDashboard = async () => {
    if (!selected) return
    try {
      const key = getKey()
      const res = await fetch(
        `${getApiBase()}/dashboards/${selected.id}/clone`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Api-Key': key, 'Authorization': key ? `Bearer ${key}` : '' },
          body: JSON.stringify({}),
        }
      )
      if (!res.ok) throw new Error(`${res.status}`)
      const data = await res.json()
      // Refresh summary list so the clone appears
      api.dashboards().then(setSummaries).catch(() => undefined)
      alert(`Dashboard cloné : ${data.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur clonage')
    }
  }

  const openDashboard = (id: string) => {
    api.getDashboard(id)
      .then(d => {
        const sorted = [...d.tiles].sort(byPosition)
        setSelected(d)
        setTiles(sorted)
        setTileData({})
        setInsights({})
        loadTileData(id, sorted)
        // Start insight loading after data is fetched (small delay)
        setTimeout(() => loadInsights(id, sorted), 300)
      })
      .catch(e => setError(e.message))
  }

  const onDragStart = (i: number) => { dragIdx.current = i }

  const onDrop = (i: number) => {
    const from = dragIdx.current
    if (from == null || from === i) return
    const next = [...tiles]
    const [moved] = next.splice(from, 1)
    next.splice(i, 0, moved)
    const reordered = next.map((tile, idx) => ({ ...tile, position: idx }))
    setTiles(reordered)
    dragIdx.current = null
    if (!selected) return
    setSaving(true)
    api.patchLayout(selected.id, reordered.map((tile, idx) => ({ id: tile.id, position: idx })))
      .catch(e => setError(e.message))
      .finally(() => setSaving(false))
  }

  const removeTile = (tileId: string) => {
    if (!selected) return
    setSaving(true)
    api.removeTile(selected.id, tileId)
      .then(() => {
        setTiles(prev => prev.filter(tile => tile.id !== tileId))
        setTileData(prev => { const n = { ...prev }; delete n[tileId]; return n })
        setInsights(prev => { const n = { ...prev }; delete n[tileId]; return n })
      })
      .catch(e => setError(e.message))
      .finally(() => setSaving(false))
  }

  const submitAdd = () => {
    if (!selected || !newTile.id || !newTile.title) return
    setSaving(true)
    api.addTile(selected.id, { ...newTile, position: tiles.length })
      .then(() => {
        const added = { ...newTile, position: tiles.length }
        setTiles(prev => [...prev, added])
        setNewTile({ id: '', type: 'kpi', title: '' })
        setShowAdd(false)
      })
      .catch(e => setError(e.message))
      .finally(() => setSaving(false))
  }

  return (
    <div style={{ maxWidth: '960px', margin: '32px auto', padding: '0 16px' }}>
      <h2>{t('dashboard.title')}</h2>
      {error && (
        <p style={{ color: '#dc2626', background: '#fef2f2', padding: '8px 12px', borderRadius: '6px' }}>
          {error} <button onClick={() => setError('')} style={{ marginInlineStart: '8px', cursor: 'pointer' }}>×</button>
        </p>
      )}

      {!selected ? (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {summaries.length === 0 && <li style={{ color: '#6b7280' }}>{t('dashboard.no_dashboards')}</li>}
          {summaries.map(d => (
            <li key={d.id} style={{ marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                onClick={() => openDashboard(d.id)}
                style={{ background: 'none', border: '1px solid #d1d5db', borderRadius: '6px', padding: '10px 16px', cursor: 'pointer', flex: 1, textAlign: 'start' }}
              >
                <strong>{d.title}</strong>
                <span style={{ marginInlineStart: '8px', fontSize: '0.8rem', color: '#6b7280' }}>{d.scope}</span>
              </button>
              <button
                data-testid={`fav-${d.id}`}
                onClick={() => api.toggleFavorite(d.id).then(res => setSummaries(prev => prev.map(s => s.id === d.id ? { ...s, is_favorite: res.is_favorite } : s)))}
                title={d.is_favorite ? t('dashboard.unfavorite') : t('dashboard.favorite')}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.1rem', padding: '4px', lineHeight: 1, color: d.is_favorite ? '#f59e0b' : '#d1d5db' }}
                aria-label={`${d.is_favorite ? t('dashboard.unfavorite') : t('dashboard.favorite')} ${d.title}`}
              >
                ★
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <button onClick={() => { setSelected(null); setShowAdd(false) }} style={{ cursor: 'pointer' }}>{t('dashboard.back')}</button>
            <h3 style={{ margin: 0, flex: 1 }}>{selected.title}</h3>
            {saving && <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>{t('dashboard.saving')}</span>}
            <button
              onClick={exportBulletin}
              disabled={exporting}
              style={{ padding: '6px 14px', background: '#065f46', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', opacity: exporting ? 0.6 : 1 }}
            >
              {exporting ? '…' : t('dashboard.export_bulletin')}
            </button>
            <button
              data-testid="clone-dashboard-btn"
              onClick={cloneDashboard}
              style={{ padding: '6px 14px', background: '#0891b2', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
            >
              {t('dashboard.clone')}
            </button>
            <button
              data-testid="export-pptx-btn"
              onClick={exportPptx}
              disabled={exporting}
              style={{ padding: '6px 14px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', opacity: exporting ? 0.6 : 1 }}
            >
              {exporting ? '…' : t('dashboard.export_pptx')}
            </button>
            <button
              onClick={() => setShowAdd(v => !v)}
              style={{ padding: '6px 14px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
            >
              {t('dashboard.add_tile')}
            </button>
          </div>

          {showAdd && (
            <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px', marginBottom: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.85rem' }}>
                {t('dashboard.id_label')}
                <input value={newTile.id} onChange={e => setNewTile(p => ({ ...p, id: e.target.value }))}
                  placeholder={t('dashboard.tile_id_placeholder')} style={inputStyle} />
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.85rem' }}>
                {t('dashboard.title_label')}
                <input value={newTile.title} onChange={e => setNewTile(p => ({ ...p, title: e.target.value }))}
                  placeholder={t('dashboard.tile_title_placeholder')} style={inputStyle} />
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.85rem' }}>
                {t('dashboard.type_label')}
                <select value={newTile.type} onChange={e => setNewTile(p => ({ ...p, type: e.target.value }))} style={inputStyle}>
                  {TILE_TYPES.map(tp => <option key={tp} value={tp}>{tp}</option>)}
                </select>
              </label>
              <button onClick={submitAdd} disabled={!newTile.id || !newTile.title}
                style={{ padding: '6px 14px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                {t('dashboard.add')}
              </button>
              <button onClick={() => setShowAdd(false)} style={{ padding: '6px 14px', cursor: 'pointer' }}>{t('dashboard.cancel')}</button>
            </div>
          )}

          <p style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '8px' }}>
            {t('dashboard.drag_hint')}
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
            {tiles.map((tile, i) => {
              const data = tileData[tile.id] ?? { columns: [], rows: [] }
              const insight = insights[tile.id]
              const insightLoading = loadingInsights[tile.id]
              return (
                <div
                  key={tile.id}
                  draggable
                  onDragStart={() => onDragStart(i)}
                  onDragOver={e => e.preventDefault()}
                  onDrop={() => onDrop(i)}
                  data-tile-id={tile.id}
                  style={{
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                    padding: '12px',
                    background: '#fff',
                    cursor: 'grab',
                    position: 'relative',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                    <h4 style={{ margin: 0, fontSize: '0.9rem', color: '#374151', flex: 1 }}>{tile.title}</h4>
                    <button
                      data-testid={`export-csv-${tile.id}`}
                      onClick={() => exportTileCsv(tile.id)}
                      title={t('dashboard.export_csv')}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6b7280', fontSize: '0.7rem', padding: '0 4px', lineHeight: 1 }}
                      aria-label={`${t('dashboard.export_csv')} ${tile.title}`}
                    >
                      ↓ CSV
                    </button>
                    <button
                      onClick={() => removeTile(tile.id)}
                      title={t('dashboard.delete_tile')}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', fontSize: '1rem', padding: '0 4px', lineHeight: 1 }}
                      aria-label={`${t('dashboard.delete_tile')} ${tile.title}`}
                    >
                      ×
                    </button>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginBottom: '8px' }}>
                    {tile.type}{tile.position != null ? ` · pos ${tile.position}` : ''}
                  </div>
                  <TileRenderer
                    type={tile.type}
                    title={tile.title}
                    data={data}
                    options={tile.options}
                  />
                  {/* AI insight badge */}
                  {insightLoading && tile.type !== 'kpi' && (
                    <div style={insightLoadingStyle}>✦ …</div>
                  )}
                  {insight && (
                    <div style={insightStyle}><span style={insightBadge}>IA</span> {insight}</div>
                  )}
                </div>
              )
            })}
            {tiles.length === 0 && (
              <p style={{ color: '#6b7280', gridColumn: '1/-1' }}>{t('dashboard.no_tiles')}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  padding: '6px 8px',
  border: '1px solid #d1d5db',
  borderRadius: '4px',
  fontSize: '0.85rem',
}

const insightStyle: React.CSSProperties = {
  marginTop: '10px',
  fontSize: '0.75rem',
  color: '#374151',
  lineHeight: 1.5,
  borderTop: '1px solid #f3f4f6',
  paddingTop: '8px',
}

const insightBadge: React.CSSProperties = {
  display: 'inline-block',
  background: '#ede9fe',
  color: '#7c3aed',
  borderRadius: '4px',
  padding: '1px 5px',
  fontSize: '0.65rem',
  fontWeight: 700,
  marginInlineEnd: '5px',
  letterSpacing: '0.03em',
}

const insightLoadingStyle: React.CSSProperties = {
  marginTop: '10px',
  fontSize: '0.75rem',
  color: '#9ca3af',
  borderTop: '1px solid #f3f4f6',
  paddingTop: '8px',
}
