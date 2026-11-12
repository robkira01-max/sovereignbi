import { useState, useMemo } from 'react'
import { buildDjiboutiVilleMap, projectLonLat, djiVilleBounds } from '../lib/geo'
import CERD_GEO from '../data/cerd_ecoles.json'

interface CerdFeature {
  type: 'Feature'
  geometry: { type: string; coordinates: number[][][] | number[][][][] }
  properties: {
    categorie: string
    sous_categorie: string
    nom: string
    code_primaire: string | null
    code_cem: string | null
    code_lycee: string | null
  }
}

function polygonCentroid(coords: number[][][] | number[][][][]): [number, number] {
  // Handle Polygon or MultiPolygon — take first ring
  const ring: number[][] =
    typeof coords[0][0][0] === 'number'
      ? (coords as number[][][])[0]
      : (coords as number[][][][])[0][0]
  const xs = ring.map(p => p[0])
  const ys = ring.map(p => p[1])
  return [xs.reduce((a, b) => a + b, 0) / xs.length, ys.reduce((a, b) => a + b, 0) / ys.length]
}

const SCHOOLS: (CerdFeature & { _centroid: [number, number] })[] = (
  CERD_GEO as unknown as { features: CerdFeature[] }
).features.map(f => ({
  ...f,
  _centroid: polygonCentroid(f.geometry.coordinates as number[][][] | number[][][][]),
}))

const CAT_CONFIG: Record<string, { color: string; label: string }> = {
  'Ecole Primaire Publique': { color: '#60a5fa', label: 'Primaire public' },
  'CEM public':              { color: '#fb923c', label: 'CEM public' },
  'EP/CEM privé':            { color: '#94a3b8', label: 'EP/CEM privé' },
  'EP/CEM/lycée privé':      { color: '#c084fc', label: 'Multi-niveaux privé' },
  'Lycée public':            { color: '#818cf8', label: 'Lycée public' },
  'Ecole maternelle publique':{ color: '#f9a8d4', label: 'Maternelle' },
}

const CATS = Object.keys(CAT_CONFIG) as (keyof typeof CAT_CONFIG)[]

function colorForCat(cat: string): string {
  return CAT_CONFIG[cat]?.color ?? '#94a3b8'
}

function labelForCat(cat: string): string {
  return CAT_CONFIG[cat]?.label ?? cat
}

export default function CerdEcolesMap() {
  const geoVille  = useMemo(() => buildDjiboutiVilleMap(), [])
  const villeB    = useMemo(() => djiVilleBounds(), [])

  const [filterCat, setFilterCat]   = useState<string>('all')
  const [hovered, setHovered]       = useState<typeof SCHOOLS[number] | null>(null)
  const [view, setView]             = useState<'map' | 'table'>('map')

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: SCHOOLS.length }
    for (const s of SCHOOLS) { c[s.properties.sous_categorie] = (c[s.properties.sous_categorie] ?? 0) + 1 }
    return c
  }, [])

  const filtered = useMemo(
    () => filterCat === 'all' ? SCHOOLS : SCHOOLS.filter(s => s.properties.sous_categorie === filterCat),
    [filterCat],
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* View switch */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <div className="view-switch" role="tablist" aria-label="Vue CERD écoles">
          <button className={view === 'map' ? 'active' : ''} onClick={() => setView('map')}>Carte</button>
          <button className={view === 'table' ? 'active' : ''} onClick={() => setView('table')}>Tableau</button>
        </div>
        <span className="muted" style={{ fontSize: 12 }}>{filtered.length} établissements · Djibouti-ville · Données CERD</span>
      </div>

      {/* Category filter */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        <button
          className="btn-ghost"
          style={{ fontSize: 12, padding: '4px 10px', borderRadius: 20, background: filterCat === 'all' ? 'var(--accent)' : undefined, color: filterCat === 'all' ? '#fff' : undefined }}
          onClick={() => setFilterCat('all')}
        >
          Tous ({counts.all})
        </button>
        {CATS.map(cat => (
          counts[cat] ? (
            <button key={cat}
              className="btn-ghost"
              style={{
                fontSize: 12, padding: '4px 10px', borderRadius: 20,
                background: filterCat === cat ? CAT_CONFIG[cat].color : undefined,
                color: filterCat === cat ? '#fff' : undefined,
                borderColor: CAT_CONFIG[cat].color,
              }}
              onClick={() => setFilterCat(filterCat === cat ? 'all' : cat)}
            >
              <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: CAT_CONFIG[cat].color, marginRight: 5 }} />
              {labelForCat(cat)} ({counts[cat] ?? 0})
            </button>
          ) : null
        ))}
      </div>

      {view === 'map' && (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          {/* SVG quartiers map */}
          <div style={{ position: 'relative', width: '100%', maxWidth: 340, flexShrink: 0, aspectRatio: geoVille.ratio }}>
            <svg viewBox={geoVille.view} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
              role="img" aria-label="Carte des établissements scolaires CERD Djibouti-ville">
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
              {filtered.map((s, i) => {
                const [lon, lat] = s._centroid
                const { x, y } = projectLonLat(lon, lat, villeB)
                const color = colorForCat(s.properties.sous_categorie)
                const isHov = hovered?.properties.nom === s.properties.nom
                return (
                  <circle key={i} cx={x} cy={y}
                    r={isHov ? 6 : 3.5}
                    fill={color} stroke="oklch(10% 0.02 265)" strokeWidth={0.5}
                    style={{ cursor: 'pointer', transition: 'r 0.1s' }}
                    onMouseEnter={() => setHovered(s)} onMouseLeave={() => setHovered(null)}>
                    <title>{`${s.properties.nom} — ${labelForCat(s.properties.sous_categorie)}`}</title>
                  </circle>
                )
              })}
            </svg>
          </div>

          {/* Right panel */}
          <div style={{ flex: 1, minWidth: 200, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {hovered ? (
              <div className="card-solid" style={{ padding: '10px 14px', fontSize: 13 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>{hovered.properties.nom}</div>
                <div style={{ color: colorForCat(hovered.properties.sous_categorie), fontWeight: 600, marginBottom: 4 }}>
                  {labelForCat(hovered.properties.sous_categorie)}
                </div>
                {hovered.properties.code_primaire && (
                  <div style={{ color: 'var(--muted)', fontSize: 12 }}>Code primaire : {hovered.properties.code_primaire}</div>
                )}
                {hovered.properties.code_cem && (
                  <div style={{ color: 'var(--muted)', fontSize: 12 }}>Code CEM : {hovered.properties.code_cem}</div>
                )}
                {hovered.properties.code_lycee && (
                  <div style={{ color: 'var(--muted)', fontSize: 12 }}>Code lycée : {hovered.properties.code_lycee}</div>
                )}
              </div>
            ) : (
              <div className="card-solid" style={{ padding: '10px 14px', fontSize: 12, color: 'var(--muted)' }}>
                Survolez un point pour voir les détails.
              </div>
            )}

            {/* Stats by category */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {CATS.filter(cat => (counts[cat] ?? 0) > 0).map(cat => (
                <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                  <span style={{ width: 10, height: 10, borderRadius: '50%', background: CAT_CONFIG[cat].color, flexShrink: 0, display: 'inline-block' }} />
                  <span style={{ flex: 1, color: 'var(--muted)' }}>{labelForCat(cat)}</span>
                  <span style={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{counts[cat]}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {view === 'table' && (
        <div className="table-wrap" style={{ maxHeight: 400 }}>
          <table className="data" style={{ fontSize: 12 }}>
            <thead>
              <tr>
                <th>Établissement</th>
                <th>Niveau</th>
                <th>Code</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, i) => (
                <tr key={i}>
                  <td>{s.properties.nom}</td>
                  <td>
                    <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: colorForCat(s.properties.sous_categorie), marginRight: 5 }} />
                    {labelForCat(s.properties.sous_categorie)}
                  </td>
                  <td style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--muted)' }}>
                    {s.properties.code_primaire ?? s.properties.code_cem ?? s.properties.code_lycee ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="muted" style={{ fontSize: 11, marginTop: 4 }}>
        Source : CERD (Centre d'Études et de Recherches de Djibouti) · 31 établissements · Djibouti-ville
      </p>
    </div>
  )
}
