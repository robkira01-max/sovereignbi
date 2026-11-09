import { useState, useMemo } from 'react'
import { buildDjiboutiMap, buildDjiboutiVilleMap, projectLonLat, djiboutiBounds, djiVilleBounds, getQuartierForPoint } from '../lib/geo'
import ECOLES_GEO from '../data/ecoles-djibouti.json'
import type { Dict } from '../lib/i18n'

interface EcoleFeature {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: {
    name: string
    type: string
    amenity: string | null
    district_adm2: string
    operator: string | null
    operator_type: string | null
    osm_type: string
    osm_id: number
    source: string
  }
}

const ECOLES: EcoleFeature[] = (
  ECOLES_GEO as unknown as { features: EcoleFeature[] }
).features

const TYPE_COLORS: Record<string, string> = {
  Primaire: '#3b82f6',
  College: '#f97316',
  Lycee: '#a855f7',
  Maternelle: '#ec4899',
  Universite: '#22c55e',
  'Formation professionnelle': '#eab308',
}

const DEFAULT_COLOR = '#94a3b8'

function colorForType(type: string): string {
  for (const [key, color] of Object.entries(TYPE_COLORS)) {
    if (type.includes(key)) return color
  }
  return DEFAULT_COLOR
}

const CANONICAL_TYPES = [
  'Primaire',
  'College',
  'Lycee',
  'Maternelle',
  'Universite',
  'Formation professionnelle',
]

function canonicalType(type: string): string {
  for (const c of CANONICAL_TYPES) {
    if (type.includes(c)) return c
  }
  return 'Autre'
}

function countByDistrict(schools: EcoleFeature[]): [string, number][] {
  const counts: Record<string, number> = {}
  for (const s of schools) {
    const d = s.properties.district_adm2 || 'Inconnu'
    counts[d] = (counts[d] ?? 0) + 1
  }
  return Object.entries(counts).sort((a, b) => b[1] - a[1])
}

interface Props { t: Dict }

export default function EcolesMap({ t }: Props) {
  const geo = useMemo(() => buildDjiboutiMap(), [])
  const geoVille = useMemo(() => buildDjiboutiVilleMap(), [])
  const bounds = useMemo(() => djiboutiBounds(), [])
  const villeB = useMemo(() => djiVilleBounds(), [])
  const [filterType, setFilterType] = useState<string>('all')
  const [hovered, setHovered] = useState<EcoleFeature | null>(null)
  const [view, setView] = useState<'map' | 'ville' | 'table'>('map')

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: ECOLES.length }
    for (const s of ECOLES) {
      const ct = canonicalType(s.properties.type)
      c[ct] = (c[ct] ?? 0) + 1
    }
    return c
  }, [])

  const filtered = useMemo(
    () =>
      filterType === 'all'
        ? ECOLES
        : ECOLES.filter((s) => canonicalType(s.properties.type) === filterType),
    [filterType],
  )

  const districtTable = useMemo(() => countByDistrict(filtered), [filtered])

  // Djibouti-ville : écoles du district Djibouti uniquement
  const villeSchools = useMemo(
    () => filtered.filter((s) => s.properties.district_adm2 === 'Djibouti'),
    [filtered],
  )
  const quartierTable = useMemo(() => {
    const c: Record<string, number> = {}
    for (const s of villeSchools) {
      const q = getQuartierForPoint(s.geometry.coordinates[0], s.geometry.coordinates[1]) ?? 'Hors quartiers'
      c[q] = (c[q] ?? 0) + 1
    }
    return Object.entries(c).sort((a, b) => b[1] - a[1])
  }, [villeSchools])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <div className="view-switch" role="tablist" aria-label={t.ecoles.filterType}>
          <button className={view === 'map' ? 'active' : ''} onClick={() => setView('map')}>{t.ecoles.viewMap}</button>
          <button className={view === 'ville' ? 'active' : ''} onClick={() => setView('ville')}>{t.ecoles.viewVille}</button>
          <button className={view === 'table' ? 'active' : ''} onClick={() => setView('table')}>{t.ecoles.viewTable}</button>
        </div>
      </div>

      {/* Type filter */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        <button
          className={`btn-ghost${filterType === 'all' ? ' active' : ''}`}
          style={{ fontSize: 12, padding: '4px 10px', borderRadius: 20, background: filterType === 'all' ? 'var(--accent)' : undefined, color: filterType === 'all' ? '#fff' : undefined }}
          onClick={() => setFilterType('all')}
        >
          {t.ecoles.allTypes} ({counts.all})
        </button>
        {CANONICAL_TYPES.map((ct) => (
          counts[ct] ? (
            <button
              key={ct}
              className="btn-ghost"
              style={{
                fontSize: 12, padding: '4px 10px', borderRadius: 20,
                background: filterType === ct ? TYPE_COLORS[ct] : undefined,
                color: filterType === ct ? '#fff' : undefined,
                borderColor: TYPE_COLORS[ct],
              }}
              onClick={() => setFilterType(filterType === ct ? 'all' : ct)}
            >
              <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: TYPE_COLORS[ct], marginRight: 5 }} />
              {ct} ({counts[ct] ?? 0})
            </button>
          ) : null
        ))}
      </div>

      {view === 'map' && (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          {/* SVG map */}
          <div style={{ position: 'relative', width: '100%', maxWidth: 340, flexShrink: 0, aspectRatio: geo.ratio }}>
            <svg
              viewBox={geo.view}
              style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
              role="img"
              aria-label={t.ecoles.title}
            >
              {/* Region shapes */}
              {geo.shapes.map((g) => (
                <path
                  key={g.key}
                  d={g.d}
                  fill="oklch(22% 0.04 265)"
                  stroke="oklch(45% 0.06 265)"
                  strokeWidth={0.8}
                  strokeLinejoin="round"
                />
              ))}
              {/* School dots */}
              {filtered.map((s, i) => {
                const { x, y } = projectLonLat(s.geometry.coordinates[0], s.geometry.coordinates[1], bounds)
                const color = colorForType(s.properties.type)
                return (
                  <circle
                    key={`${s.properties.osm_id}-${i}`}
                    cx={x}
                    cy={y}
                    r={hovered?.properties.osm_id === s.properties.osm_id ? 4 : 2.5}
                    fill={color}
                    stroke="oklch(10% 0.02 265)"
                    strokeWidth={0.4}
                    style={{ cursor: 'pointer', transition: 'r 0.1s' }}
                    onMouseEnter={() => setHovered(s)}
                    onMouseLeave={() => setHovered(null)}
                  >
                    <title>{`${s.properties.name} — ${s.properties.type} (${s.properties.district_adm2})`}</title>
                  </circle>
                )
              })}
            </svg>
          </div>

          {/* Right panel: tooltip + district counts */}
          <div style={{ flex: 1, minWidth: 200, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {hovered ? (
              <div className="card-solid" style={{ padding: '10px 14px', fontSize: 13 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>{hovered.properties.name}</div>
                <div style={{ color: 'var(--muted)' }}>{hovered.properties.type}</div>
                <div style={{ color: 'var(--muted)' }}>{t.ecoles.district} : {hovered.properties.district_adm2}</div>
              </div>
            ) : (
              <div className="card-solid" style={{ padding: '10px 14px', fontSize: 12, color: 'var(--muted)' }}>
                {t.ecoles.hoverHint}
              </div>
            )}
            <div className="table-wrap" style={{ maxHeight: 220 }}>
              <table className="data" style={{ fontSize: 12 }}>
                <thead><tr><th>{t.ecoles.districtCol}</th><th>{t.ecoles.countCol}</th></tr></thead>
                <tbody>
                  {districtTable.map(([d, n]) => (
                    <tr key={d}><td>{d}</td><td>{n}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {view === 'ville' && (
        <div>
          <p className="muted" style={{ fontSize: 12, marginBottom: 10 }}>{t.ecoles.villeNote}</p>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
            {/* Quartiers SVG */}
            <div style={{ position: 'relative', width: '100%', maxWidth: 340, flexShrink: 0, aspectRatio: geoVille.ratio }}>
              <svg
                viewBox={geoVille.view}
                style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
                role="img"
                aria-label={t.ecoles.villeTitle}
              >
                {geoVille.shapes.map((g) => (
                  <path
                    key={g.key}
                    d={g.d}
                    fill="oklch(22% 0.04 265)"
                    stroke="oklch(50% 0.08 265)"
                    strokeWidth={0.6}
                    strokeLinejoin="round"
                  />
                ))}
                {geoVille.shapes.map((g) => (
                  <text
                    key={`lbl-${g.key}`}
                    x={g.x}
                    y={g.y}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={6}
                    fill="oklch(70% 0.05 265)"
                    style={{ pointerEvents: 'none', userSelect: 'none' }}
                  >{g.name}</text>
                ))}
                {villeSchools.map((s, i) => {
                  const { x, y } = projectLonLat(s.geometry.coordinates[0], s.geometry.coordinates[1], villeB)
                  const color = colorForType(s.properties.type)
                  return (
                    <circle
                      key={`v-${s.properties.osm_id}-${i}`}
                      cx={x} cy={y}
                      r={hovered?.properties.osm_id === s.properties.osm_id ? 5 : 3}
                      fill={color}
                      stroke="oklch(10% 0.02 265)"
                      strokeWidth={0.4}
                      style={{ cursor: 'pointer', transition: 'r 0.1s' }}
                      onMouseEnter={() => setHovered(s)}
                      onMouseLeave={() => setHovered(null)}
                    >
                      <title>{`${s.properties.name} — ${s.properties.type} (${s.properties.district_adm2})`}</title>
                    </circle>
                  )
                })}
              </svg>
            </div>
            {/* Right panel */}
            <div style={{ flex: 1, minWidth: 200, display: 'flex', flexDirection: 'column', gap: 10 }}>
              {hovered ? (
                <div className="card-solid" style={{ padding: '10px 14px', fontSize: 13 }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>{hovered.properties.name}</div>
                  <div style={{ color: 'var(--muted)' }}>{hovered.properties.type}</div>
                  <div style={{ color: 'var(--muted)' }}>{t.ecoles.district} : {hovered.properties.district_adm2}</div>
                </div>
              ) : (
                <div className="card-solid" style={{ padding: '10px 14px', fontSize: 12, color: 'var(--muted)' }}>
                  {t.ecoles.hoverHint}
                </div>
              )}
              <div className="table-wrap" style={{ maxHeight: 260 }}>
                <table className="data" style={{ fontSize: 12 }}>
                  <thead><tr><th>{t.ecoles.quartierCol}</th><th>{t.ecoles.countCol}</th></tr></thead>
                  <tbody>
                    {quartierTable.map(([q, n]) => (
                      <tr key={q}><td>{q}</td><td>{n}</td></tr>
                    ))}
                    {villeSchools.length === 0 && (
                      <tr><td colSpan={2} style={{ color: 'var(--muted)', textAlign: 'center' }}>Aucun établissement</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              <p className="muted" style={{ fontSize: 11 }}>{villeSchools.length} / {filtered.length} {t.ecoles.countCol.toLowerCase()}</p>
            </div>
          </div>
        </div>
      )}

      {view === 'table' && (
        <div className="table-wrap" style={{ maxHeight: 400 }}>
          <table className="data" style={{ fontSize: 12 }}>
            <thead>
              <tr>
                <th>{t.ecoles.nameCol}</th>
                <th>{t.ecoles.typeCol}</th>
                <th>{t.ecoles.districtCol}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, i) => (
                <tr key={`${s.properties.osm_id}-${i}`}>
                  <td>{s.properties.name}</td>
                  <td>
                    <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: colorForType(s.properties.type), marginRight: 5 }} />
                    {canonicalType(s.properties.type)}
                  </td>
                  <td>{s.properties.district_adm2}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="muted" style={{ fontSize: 11, marginTop: 4 }}>
        {t.ecoles.source} · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a>
      </p>
    </div>
  )
}
