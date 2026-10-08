import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Dashboard, DashboardSummary, Tile } from '../api/client'
import { TileRenderer } from '../components/TileRenderer'

const TILE_TYPES = ['kpi', 'bar', 'line', 'pie', 'table']

export function DashboardPage() {
  const [summaries, setSummaries] = useState<DashboardSummary[]>([])
  const [selected, setSelected] = useState<Dashboard | null>(null)
  const [tiles, setTiles] = useState<Tile[]>([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [showAdd, setShowAdd] = useState(false)
  const [newTile, setNewTile] = useState({ id: '', type: 'kpi', title: '' })
  const dragIdx = useRef<number | null>(null)

  useEffect(() => {
    api.dashboards()
      .then(setSummaries)
      .catch(e => setError(e.message))
  }, [])

  const openDashboard = (id: string) => {
    api.getDashboard(id)
      .then(d => { setSelected(d); setTiles([...d.tiles].sort(byPosition)) })
      .catch(e => setError(e.message))
  }

  const byPosition = (a: Tile, b: Tile) => (a.position ?? 999) - (b.position ?? 999)

  // ── Drag & drop handlers ─────────────────────────────────────────────────────
  const onDragStart = (i: number) => { dragIdx.current = i }

  const onDrop = (i: number) => {
    const from = dragIdx.current
    if (from == null || from === i) return
    const next = [...tiles]
    const [moved] = next.splice(from, 1)
    next.splice(i, 0, moved)
    const reordered = next.map((t, idx) => ({ ...t, position: idx }))
    setTiles(reordered)
    dragIdx.current = null

    if (!selected) return
    setSaving(true)
    api.patchLayout(selected.id, reordered.map((t, idx) => ({ id: t.id, position: idx })))
      .catch(e => setError(e.message))
      .finally(() => setSaving(false))
  }

  // ── Remove tile ───────────────────────────────────────────────────────────────
  const removeTile = (tileId: string) => {
    if (!selected) return
    setSaving(true)
    api.removeTile(selected.id, tileId)
      .then(() => setTiles(prev => prev.filter(t => t.id !== tileId)))
      .catch(e => setError(e.message))
      .finally(() => setSaving(false))
  }

  // ── Add tile ──────────────────────────────────────────────────────────────────
  const submitAdd = () => {
    if (!selected || !newTile.id || !newTile.title) return
    setSaving(true)
    api.addTile(selected.id, { ...newTile, position: tiles.length })
      .then(() => {
        setTiles(prev => [...prev, { ...newTile, position: prev.length }])
        setNewTile({ id: '', type: 'kpi', title: '' })
        setShowAdd(false)
      })
      .catch(e => setError(e.message))
      .finally(() => setSaving(false))
  }

  return (
    <div style={{ maxWidth: '960px', margin: '32px auto', padding: '0 16px' }}>
      <h2>Tableaux de bord</h2>
      {error && (
        <p style={{ color: '#dc2626', background: '#fef2f2', padding: '8px 12px', borderRadius: '6px' }}>
          {error} <button onClick={() => setError('')} style={{ marginLeft: '8px', cursor: 'pointer' }}>×</button>
        </p>
      )}

      {!selected ? (
        <>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {summaries.length === 0 && <li style={{ color: '#6b7280' }}>Aucun tableau de bord.</li>}
            {summaries.map(d => (
              <li key={d.id} style={{ marginBottom: '8px' }}>
                <button
                  onClick={() => openDashboard(d.id)}
                  style={{ background: 'none', border: '1px solid #d1d5db', borderRadius: '6px', padding: '10px 16px', cursor: 'pointer', width: '100%', textAlign: 'left' }}
                >
                  <strong>{d.title}</strong>
                  <span style={{ marginLeft: '8px', fontSize: '0.8rem', color: '#6b7280' }}>{d.scope}</span>
                </button>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <button onClick={() => { setSelected(null); setShowAdd(false) }} style={{ cursor: 'pointer' }}>← Retour</button>
            <h3 style={{ margin: 0, flex: 1 }}>{selected.title}</h3>
            {saving && <span style={{ fontSize: '0.85rem', color: '#6b7280' }}>Enregistrement…</span>}
            <button
              onClick={() => setShowAdd(v => !v)}
              style={{ padding: '6px 14px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}
            >
              + Tuile
            </button>
          </div>

          {showAdd && (
            <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '16px', marginBottom: '16px', display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.85rem' }}>
                ID
                <input value={newTile.id} onChange={e => setNewTile(p => ({ ...p, id: e.target.value }))}
                  placeholder="ex: kpi_total" style={inputStyle} />
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.85rem' }}>
                Titre
                <input value={newTile.title} onChange={e => setNewTile(p => ({ ...p, title: e.target.value }))}
                  placeholder="ex: Total ventes" style={inputStyle} />
              </label>
              <label style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.85rem' }}>
                Type
                <select value={newTile.type} onChange={e => setNewTile(p => ({ ...p, type: e.target.value }))} style={inputStyle}>
                  {TILE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </label>
              <button onClick={submitAdd} disabled={!newTile.id || !newTile.title}
                style={{ padding: '6px 14px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                Ajouter
              </button>
              <button onClick={() => setShowAdd(false)} style={{ padding: '6px 14px', cursor: 'pointer' }}>Annuler</button>
            </div>
          )}

          <p style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '8px' }}>
            Faites glisser les tuiles pour les réordonner.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
            {tiles.map((tile, i) => (
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
                    onClick={() => removeTile(tile.id)}
                    title="Supprimer cette tuile"
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', fontSize: '1rem', padding: '0 4px', lineHeight: 1 }}
                    aria-label={`Supprimer ${tile.title}`}
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
                  data={{ columns: [], rows: [] }}
                />
              </div>
            ))}
            {tiles.length === 0 && (
              <p style={{ color: '#6b7280', gridColumn: '1/-1' }}>Aucune tuile. Cliquez « + Tuile » pour en ajouter.</p>
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
