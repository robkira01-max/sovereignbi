import { useState, useMemo } from 'react'
import { buildDjiboutiMap, buildDjiboutiVilleMap, projectLonLat, djiboutiBounds, djiVilleBounds } from '../lib/geo'
import SANTE_GEO from '../data/dj_structures_sante.json'

interface SanteFeature {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: {
    region: string
    structure: string
    type: string
    total_personnel: number | null
    medecins: number | null
    infirmiers: number | null
    sages_femmes: number | null
  }
}

const STRUCTURES: SanteFeature[] = (
  SANTE_GEO as unknown as { features: SanteFeature[] }
).features

const TYPE_CONFIG: Record<string, { color: string; label: string }> = {
  hôpital:      { color: '#f87171', label: 'Hôpital' },
  centre_sante: { color: '#60a5fa', label: 'Centre de santé' },
  poste_sante:  { color: '#34d399', label: 'Poste de santé' },
  camp_refugies:{ color: '#fb923c', label: 'Camp de réfugiés' },
  autre:        { color: '#94a3b8', label: 'Autre' },
}

const TYPES = ['hôpital', 'centre_sante', 'poste_sante', 'camp_refugies', 'autre'] as const

function colorForType(type: string): string {
  return TYPE_CONFIG[type]?.color ?? '#94a3b8'
}

function labelForType(type: string): string {
  return TYPE_CONFIG[type]?.label ?? type
}

export default function StructuresSanteMap() {
  const geo        = useMemo(() => buildDjiboutiMap(), [])
  const geoVille   = useMemo(() => buildDjiboutiVilleMap(), [])
  const bounds     = useMemo(() => djiboutiBounds(), [])
  const villeB     = useMemo(() => djiVilleBounds(), [])

  const [view, setView]           = useState<'national' | 'ville' | 'table'>('national')
  const [filterType, setFilterType] = useState<string>('all')
  const [hovered, setHovered]     = useState<SanteFeature | null>(null)

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: STRUCTURES.length }
    for (const s of STRUCTURES) { c[s.properties.type] = (c[s.properties.type] ?? 0) + 1 }
    return c
  }, [])

  const filtered = useMemo(
    () => filterType === 'all' ? STRUCTURES : STRUCTURES.filter(s => s.properties.type === filterType),
    [filterType],
  )

  const villeStructures = useMemo(
    () => filtered.filter(s => s.properties.region === 'djibouti_ville'),
    [filtered],
  )

  const regionTable = useMemo(() => {
    const c: Record<string, number> = {}
    for (const s of filtered) { c[s.properties.region] = (c[s.properties.region] ?? 0) + 1 }
    return Object.entries(c).sort((a, b) => b[1] - a[1])
  }, [filtered])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* View switch */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <div className="view-switch" role="tablist" aria-label="Vue carte santé">
          <button className={view === 'national' ? 'active' : ''} onClick={() => setView('national')}>Djibouti national</button>
          <button className={view === 'ville' ? 'active' : ''} onClick={() => setView('ville')}>Djibouti-ville</button>
          <button className={view === 'table' ? 'active' : ''} onClick={() => setView('table')}>Tableau</button>
        </div>
      </div>

      {/* Type filter */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        <button
          className="btn-ghost"
          style={{ fontSize: 12, padding: '4px 10px', borderRadius: 20, background: filterType === 'all' ? 'var(--accent)' : undefined, color: filterType === 'all' ? '#fff' : undefined }}
          onClick={() => setFilterType('all')}
        >
          Tous ({counts.all})
        </button>
        {TYPES.map(tp => (
          counts[tp] ? (
            <button
              key={tp}
              className="btn-ghost"
              style={{
                fontSize: 12, padding: '4px 10px', borderRadius: 20,
                background: filterType === tp ? TYPE_CONFIG[tp].color : undefined,
                color: filterType === tp ? '#fff' : undefined,
                borderColor: TYPE_CONFIG[tp].color,
              }}
              onClick={() => setFilterType(filterType === tp ? 'all' : tp)}
            >
              <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: TYPE_CONFIG[tp].color, marginRight: 5 }} />
              {labelForType(tp)} ({counts[tp] ?? 0})
            </button>
          ) : null
        ))}
      </div>

      {/* National map */}
      {view === 'national' && (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <div style={{ position: 'relative', width: '100%', maxWidth: 340, flexShrink: 0, aspectRatio: geo.ratio }}>
            <svg viewBox={geo.view} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
              role="img" aria-label="Carte des structures de santé de Djibouti">
              {geo.shapes.map(g => (
                <path key={g.key} d={g.d}
                  fill="oklch(22% 0.04 265)" stroke="oklch(45% 0.06 265)"
                  strokeWidth={0.8} strokeLinejoin="round" />
              ))}
              {filtered.map((s, i) => {
                const { x, y } = projectLonLat(s.geometry.coordinates[0], s.geometry.coordinates[1], bounds)
                const color = colorForType(s.properties.type)
                const isHov = hovered?.properties.structure === s.properties.structure
                return (
                  <circle key={`${i}`} cx={x} cy={y}
                    r={isHov ? 5 : (s.properties.type === 'hôpital' ? 4 : 3)}
                    fill={color} stroke="oklch(10% 0.02 265)" strokeWidth={0.5}
                    style={{ cursor: 'pointer', transition: 'r 0.1s' }}
                    onMouseEnter={() => setHovered(s)} onMouseLeave={() => setHovered(null)}>
                    <title>{`${s.properties.structure} — ${labelForType(s.properties.type)}`}</title>
                  </circle>
                )
              })}
            </svg>
          </div>

          <div style={{ flex: 1, minWidth: 200, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {hovered ? (
              <div className="card-solid" style={{ padding: '10px 14px', fontSize: 13 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>{hovered.properties.structure}</div>
                <div style={{ color: colorForType(hovered.properties.type), fontWeight: 600, marginBottom: 4 }}>
                  {labelForType(hovered.properties.type)}
                </div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>Région : {hovered.properties.region?.replace(/_/g, ' ')}</div>
                {hovered.properties.total_personnel !== null && (
                  <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                    Personnel : {hovered.properties.total_personnel}
                    {hovered.properties.medecins !== null && ` (médecins : ${hovered.properties.medecins})`}
                  </div>
                )}
              </div>
            ) : (
              <div className="card-solid" style={{ padding: '10px 14px', fontSize: 12, color: 'var(--muted)' }}>
                Survolez un point pour voir les détails.
              </div>
            )}
            <div className="table-wrap" style={{ maxHeight: 220 }}>
              <table className="data" style={{ fontSize: 12 }}>
                <thead><tr><th>Région</th><th>Nb</th></tr></thead>
                <tbody>
                  {regionTable.map(([r, n]) => (
                    <tr key={r}><td>{r.replace(/_/g, ' ')}</td><td>{n}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Djibouti-ville map */}
      {view === 'ville' && (
        <div>
          <p className="muted" style={{ fontSize: 12, marginBottom: 10 }}>
            {villeStructures.length} structures dans Djibouti-ville ({filtered.length} national)
          </p>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
            <div style={{ position: 'relative', width: '100%', maxWidth: 340, flexShrink: 0, aspectRatio: geoVille.ratio }}>
              <svg viewBox={geoVille.view} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
                role="img" aria-label="Structures de santé Djibouti-ville">
                {geoVille.shapes.map(g => (
                  <path key={g.key} d={g.d}
                    fill="oklch(22% 0.04 265)" stroke="oklch(50% 0.08 265)"
                    strokeWidth={0.6} strokeLinejoin="round" />
                ))}
                {geoVille.shapes.map(g => (
                  <text key={`lbl-${g.key}`} x={g.x} y={g.y}
                    textAnchor="middle" dominantBaseline="middle"
                    fontSize={6} fill="oklch(70% 0.05 265)"
                    style={{ pointerEvents: 'none', userSelect: 'none' }}>
                    {g.name}
                  </text>
                ))}
                {villeStructures.map((s, i) => {
                  const { x, y } = projectLonLat(s.geometry.coordinates[0], s.geometry.coordinates[1], villeB)
                  const color = colorForType(s.properties.type)
                  const isHov = hovered?.properties.structure === s.properties.structure
                  return (
                    <circle key={`v-${i}`} cx={x} cy={y}
                      r={isHov ? 7 : (s.properties.type === 'hôpital' ? 6 : 4)}
                      fill={color} stroke="oklch(10% 0.02 265)" strokeWidth={0.5}
                      style={{ cursor: 'pointer', transition: 'r 0.1s' }}
                      onMouseEnter={() => setHovered(s)} onMouseLeave={() => setHovered(null)}>
                      <title>{`${s.properties.structure} — ${labelForType(s.properties.type)}`}</title>
                    </circle>
                  )
                })}
              </svg>
            </div>

            <div style={{ flex: 1, minWidth: 200, display: 'flex', flexDirection: 'column', gap: 10 }}>
              {hovered ? (
                <div className="card-solid" style={{ padding: '10px 14px', fontSize: 13 }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>{hovered.properties.structure}</div>
                  <div style={{ color: colorForType(hovered.properties.type), fontWeight: 600, marginBottom: 4 }}>
                    {labelForType(hovered.properties.type)}
                  </div>
                  {hovered.properties.total_personnel !== null && (
                    <div style={{ color: 'var(--muted)', fontSize: 12 }}>
                      Personnel : {hovered.properties.total_personnel}
                      {hovered.properties.medecins !== null && ` · médecins : ${hovered.properties.medecins}`}
                      {hovered.properties.infirmiers !== null && ` · infirmiers : ${hovered.properties.infirmiers}`}
                    </div>
                  )}
                </div>
              ) : (
                <div className="card-solid" style={{ padding: '10px 14px', fontSize: 12, color: 'var(--muted)' }}>
                  Survolez un point pour voir les détails.
                </div>
              )}
              <div className="table-wrap" style={{ maxHeight: 260 }}>
                <table className="data" style={{ fontSize: 12 }}>
                  <thead><tr><th>Structure</th><th>Type</th><th>Personnel</th></tr></thead>
                  <tbody>
                    {villeStructures.map((s, i) => (
                      <tr key={i} style={{ cursor: 'pointer' }}
                        onMouseEnter={() => setHovered(s)} onMouseLeave={() => setHovered(null)}>
                        <td style={{ fontWeight: hovered?.properties.structure === s.properties.structure ? 600 : 400 }}>
                          {s.properties.structure}
                        </td>
                        <td>
                          <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: colorForType(s.properties.type), marginRight: 5 }} />
                          {labelForType(s.properties.type)}
                        </td>
                        <td>{s.properties.total_personnel ?? '—'}</td>
                      </tr>
                    ))}
                    {villeStructures.length === 0 && (
                      <tr><td colSpan={3} style={{ color: 'var(--muted)', textAlign: 'center' }}>Aucune structure</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Table view */}
      {view === 'table' && (
        <div className="table-wrap" style={{ maxHeight: 400 }}>
          <table className="data" style={{ fontSize: 12 }}>
            <thead>
              <tr><th>Structure</th><th>Type</th><th>Région</th><th>Personnel</th><th>Médecins</th></tr>
            </thead>
            <tbody>
              {filtered.map((s, i) => (
                <tr key={i}>
                  <td>{s.properties.structure}</td>
                  <td>
                    <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: colorForType(s.properties.type), marginRight: 5 }} />
                    {labelForType(s.properties.type)}
                  </td>
                  <td>{s.properties.region?.replace(/_/g, ' ')}</td>
                  <td>{s.properties.total_personnel ?? '—'}</td>
                  <td>{s.properties.medecins ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="muted" style={{ fontSize: 11, marginTop: 4 }}>
        Source : Ministère de la Santé de Djibouti · 65 structures · Données démo (2024)
      </p>
    </div>
  )
}
