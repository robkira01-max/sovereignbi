import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Dashboard } from '../api/client'
import { TileRenderer } from '../components/TileRenderer'

export function DashboardPage() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([])
  const [selected, setSelected] = useState<Dashboard | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.dashboards()
      .then(setDashboards)
      .catch(e => setError(e.message))
  }, [])

  const openDashboard = (id: string) => {
    api.getDashboard(id)
      .then(setSelected)
      .catch(e => setError(e.message))
  }

  return (
    <div style={{ maxWidth: '900px', margin: '32px auto', padding: '0 16px' }}>
      <h2>Tableaux de bord</h2>
      {error && <p style={{ color: '#dc2626' }}>{error}</p>}

      {!selected ? (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {dashboards.length === 0 && <li style={{ color: '#6b7280' }}>Aucun tableau de bord.</li>}
          {dashboards.map(d => (
            <li key={d.id} style={{ marginBottom: '8px' }}>
              <button
                onClick={() => openDashboard(d.id)}
                style={{ background: 'none', border: '1px solid #d1d5db', borderRadius: '6px', padding: '10px 16px', cursor: 'pointer', width: '100%', textAlign: 'left' }}
              >
                {d.title}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div>
          <button onClick={() => setSelected(null)} style={{ marginBottom: '16px', cursor: 'pointer' }}>← Retour</button>
          <h3>{selected.title}</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
            {selected.tiles.map(tile => (
              <div key={tile.id} style={{ border: '1px solid #e5e7eb', borderRadius: '8px', padding: '12px' }}>
                <h4 style={{ marginTop: 0, marginBottom: '8px', fontSize: '0.9rem', color: '#374151' }}>{tile.title}</h4>
                <TileRenderer
                  type={tile.type}
                  title={tile.title}
                  data={{ columns: [], rows: [] }}
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
