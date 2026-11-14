import { useState } from 'react'
import COMMUNES_GEO from '../data/cerd_communes.json'
import SECTEURS_GEO from '../data/cerd_secteurs.json'
import TYPOLOGIES_GEO from '../data/cerd_typologies.json'
import EQUIPEMENTS_GEO from '../data/cerd_equipements_sociaux.json'
import ECOLES_GEO from '../data/cerd_ecoles.json'
import VOIRIE_GEO from '../data/cerd_voirie.json'
import LIGNES_BUS_GEO from '../data/cerd_lignes_bus.json'
import TERMINUS_GEO from '../data/cerd_terminus_bus.json'
import OSM_VOIRIE_GEO from '../data/osm_centre_voirie.json'
import OSM_LIEUX_GEO from '../data/osm_centre_lieux.json'

import {
  OSM_ROAD_STYLE, VILLE_BOUNDS, VILLE_PAD, VILLE_W, centroidOfPolygon, linePath, polygonPath, px, py,
  type Coord, type GeoFeature,
} from '../lib/villeGeo'

// Color schemes
const TYPO_COLORS: Record<string, string> = {
  'spontané dense':                                         'oklch(60% 0.14 40)',
  'cité-lotissement':                                       'oklch(55% 0.12 240)',
  'spontané tramé en cours de densification':               'oklch(65% 0.14 85)',
  'trame acceuil':                                          'oklch(58% 0.13 155)',
  "trame d'acceuil en cours de densification":              'oklch(62% 0.12 170)',
}

const VOIRIE_COLORS: Record<string, string> = {
  'Reseau national':          'oklch(85% 0.18 55)',
  'Axe structurant revetu':   'oklch(70% 0.15 35)',
  'route secondaire revetue': 'oklch(55% 0.06 265)',
  '':                         'oklch(42% 0.04 265)',
}

const EQUIP_COLORS: Record<string, string> = {
  'equipement scolaire':  '#60a5fa',
  'equipement sanitaire': '#f87171',
  'equipement marchand':  '#fb923c',
  'equipement religieux': '#c084fc',
  'equipement social':    '#34d399',
  'administration':       '#22d3ee',
  'equipement sportif':   '#facc15',
  'Zone militaire':       '#94a3b8',
}

const LAYER_LABELS: Record<string, string> = {
  centre:      'Centre-ville (OSM)',
  secteurs:    'Secteurs',
  typologies:  'Typologies urbaines',
  voirie:      'Voirie',
  equipements: 'Équipements',
  ecoles:      'Écoles',
  bus:         'Transport',
}

type Layer = keyof typeof LAYER_LABELS

type HoveredFeature = { nom: string; detail: string; color: string }

export default function DjiboutiVilleMap() {
  const [layers, setLayers] = useState<Record<Layer, boolean>>({
    centre: true, secteurs: true, typologies: false, voirie: true, equipements: true, ecoles: false, bus: false,
  })
  const [hovered, setHovered] = useState<HoveredFeature | null>(null)
  const [view, setView] = useState<'map' | 'table'>('map')
  const [tableLayer, setTableLayer] = useState<'equipements' | 'ecoles'>('equipements')

  const W = VILLE_W
  const PAD = VILLE_PAD
  const b = VILLE_BOUNDS
  const viewBox = `-${PAD} -${PAD} ${W + PAD * 2} ${b.H + PAD * 2}`

  const toggle = (l: Layer) => setLayers(prev => ({ ...prev, [l]: !prev[l] }))

  const feats = <T,>(geo: unknown) => (geo as { features: T[] }).features

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Controls */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <div className="view-switch" role="tablist" aria-label="Vue carte SIG">
          <button className={view === 'map' ? 'active' : ''} onClick={() => setView('map')}>Carte</button>
          <button className={view === 'table' ? 'active' : ''} onClick={() => setView('table')}>Tableau</button>
        </div>
        {(Object.keys(LAYER_LABELS) as Layer[]).map(l => (
          <label key={l} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, cursor: 'pointer', userSelect: 'none' }}>
            <input type="checkbox" checked={layers[l]} onChange={() => toggle(l)} />
            {LAYER_LABELS[l]}
          </label>
        ))}
      </div>

      {view === 'map' && (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <div style={{ position: 'relative', width: '100%', maxWidth: 760, flexShrink: 0 }}>
            <svg
              viewBox={viewBox}
              style={{ width: '100%', height: 'auto', display: 'block' }}
              role="img"
              aria-label="Carte SIG Djibouti-ville — données CERD"
            >
              {/* Background communes */}
              {feats<GeoFeature>(COMMUNES_GEO).map((f, i) => (
                <path key={`comm-${i}`}
                  d={polygonPath(f.geometry.coordinates, b)}
                  fill="oklch(18% 0.03 265)"
                  stroke="oklch(45% 0.08 265)"
                  strokeWidth={0.8}
                />
              ))}

              {/* Centre-ville : voirie OSM (hors couverture CERD) */}
              {layers.centre && (['locale', 'tertiaire', 'secondaire', 'primaire'] as const).map(cl => (
                <g key={`osm-${cl}`} fill="none" stroke={OSM_ROAD_STYLE[cl].color}
                  strokeWidth={OSM_ROAD_STYLE[cl].w} strokeLinecap="round" strokeLinejoin="round">
                  {feats<GeoFeature>(OSM_VOIRIE_GEO).filter(f => f.properties.classe === cl).map((f, i) => (
                    <path key={i} d={linePath(f.geometry.coordinates, b)} />
                  ))}
                </g>
              ))}
              {layers.centre && feats<GeoFeature>(OSM_LIEUX_GEO).map((f, i) => {
                const c = f.geometry.coordinates as Coord
                return (
                  <text key={`lieu-${i}`}
                    x={px(c[0], b).toFixed(1)} y={py(c[1], b).toFixed(1)}
                    textAnchor="middle" dominantBaseline="middle"
                    fontSize={6.5} fontStyle="italic" fill="oklch(82% 0.06 200)"
                    stroke="oklch(12% 0.03 265)" strokeWidth={1.6} paintOrder="stroke"
                    style={{ pointerEvents: 'none', userSelect: 'none' }}
                  >
                    {String(f.properties.nom)}
                  </text>
                )
              })}

              {/* Secteurs d'adressage */}
              {layers.secteurs && feats<GeoFeature>(SECTEURS_GEO).map((f, i) => {
                const nom = String(f.properties.nom ?? '')
                const [clon, clat] = centroidOfPolygon(f.geometry.coordinates)
                return (
                  <g key={`sect-${i}`}>
                    <path
                      d={polygonPath(f.geometry.coordinates, b)}
                      fill="oklch(24% 0.04 265 / .4)"
                      stroke="oklch(55% 0.08 265)"
                      strokeWidth={0.5}
                      strokeDasharray="3 2"
                      style={{ cursor: 'pointer' }}
                      onMouseEnter={() => setHovered({ nom, detail: 'Secteur d\'adressage', color: 'oklch(65% 0.08 265)' })}
                      onMouseLeave={() => setHovered(null)}
                    />
                    {nom && (
                      <text
                        x={px(clon, b).toFixed(1)} y={py(clat, b).toFixed(1)}
                        textAnchor="middle" dominantBaseline="middle"
                        fontSize={5} fill="oklch(68% 0.06 265)"
                        style={{ pointerEvents: 'none', userSelect: 'none' }}
                      >
                        {nom.length > 14 ? nom.slice(0, 13) + '…' : nom}
                      </text>
                    )}
                  </g>
                )
              })}

              {/* Typologies urbaines */}
              {layers.typologies && feats<GeoFeature>(TYPOLOGIES_GEO).map((f, i) => {
                const type = String(f.properties.type_quart ?? '')
                const nom = String(f.properties.nom ?? '')
                const fill = TYPO_COLORS[type] ?? 'oklch(50% 0.06 265)'
                return (
                  <path key={`typo-${i}`}
                    d={polygonPath(f.geometry.coordinates, b)}
                    fill={fill + '99'}
                    stroke={fill}
                    strokeWidth={0.4}
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHovered({ nom: nom || type, detail: type, color: fill })}
                    onMouseLeave={() => setHovered(null)}
                  />
                )
              })}

              {/* Voirie */}
              {layers.voirie && feats<GeoFeature>(VOIRIE_GEO).map((f, i) => {
                const hier = String(f.properties.hierachie ?? '')
                const color = VOIRIE_COLORS[hier] ?? VOIRIE_COLORS['']
                const w = hier === 'Reseau national' ? 1.2 : hier === 'Axe structurant revetu' ? 0.8 : 0.4
                return (
                  <path key={`voi-${i}`}
                    d={linePath(f.geometry.coordinates, b)}
                    fill="none"
                    stroke={color}
                    strokeWidth={w}
                    strokeLinecap="round"
                  />
                )
              })}

              {/* Lignes de bus */}
              {layers.bus && feats<GeoFeature>(LIGNES_BUS_GEO).map((f, i) => {
                const ligne = String(f.properties.ligne ?? `Ligne ${i + 1}`)
                return (
                  <path key={`bus-${i}`}
                    d={linePath(f.geometry.coordinates, b)}
                    fill="none"
                    stroke="oklch(78% 0.18 155)"
                    strokeWidth={1.5}
                    strokeDasharray="6 3"
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHovered({ nom: ligne, detail: 'Ligne de bus', color: 'oklch(78% 0.18 155)' })}
                    onMouseLeave={() => setHovered(null)}
                  />
                )
              })}

              {/* Terminus de bus */}
              {layers.bus && feats<GeoFeature>(TERMINUS_GEO).map((f, i) => {
                const nom = String(f.properties.nom ?? `Terminus ${i + 1}`)
                const c = f.geometry.coordinates as Coord
                return (
                  <circle key={`term-${i}`}
                    cx={px(c[0], b)} cy={py(c[1], b)}
                    r={4}
                    fill="oklch(78% 0.18 155)"
                    stroke="oklch(10% 0.02 265)"
                    strokeWidth={0.5}
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHovered({ nom, detail: 'Terminus bus', color: 'oklch(78% 0.18 155)' })}
                    onMouseLeave={() => setHovered(null)}
                  />
                )
              })}

              {/* Équipements socio-économiques */}
              {layers.equipements && feats<GeoFeature>(EQUIPEMENTS_GEO).map((f, i) => {
                const cat = String(f.properties.categorie ?? '')
                const nom = String(f.properties.nom ?? '')
                const sous = String(f.properties.sous_categ ?? '')
                const color = EQUIP_COLORS[cat] ?? '#94a3b8'
                const [clon, clat] = centroidOfPolygon(f.geometry.coordinates)
                return (
                  <circle key={`eq-${i}`}
                    cx={px(clon, b)} cy={py(clat, b)}
                    r={3}
                    fill={color}
                    stroke="oklch(10% 0.02 265)"
                    strokeWidth={0.4}
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHovered({ nom: nom || sous, detail: sous || cat, color })}
                    onMouseLeave={() => setHovered(null)}
                  >
                    <title>{`${nom} — ${sous}`}</title>
                  </circle>
                )
              })}

              {/* Écoles */}
              {layers.ecoles && feats<GeoFeature>(ECOLES_GEO).map((f, i) => {
                const nom = String(f.properties.nom ?? '')
                const sous = String(f.properties.sous_categ ?? '')
                const [clon, clat] = centroidOfPolygon(f.geometry.coordinates)
                return (
                  <circle key={`ec-${i}`}
                    cx={px(clon, b)} cy={py(clat, b)}
                    r={3.5}
                    fill="#60a5fa"
                    stroke="oklch(10% 0.02 265)"
                    strokeWidth={0.5}
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHovered({ nom, detail: sous, color: '#60a5fa' })}
                    onMouseLeave={() => setHovered(null)}
                  />
                )
              })}
            </svg>
          </div>

          {/* Legend + tooltip panel */}
          <div style={{ flex: 1, minWidth: 180, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {/* Tooltip */}
            {hovered ? (
              <div className="card-solid" style={{ padding: '10px 14px', fontSize: 13 }}>
                <div style={{ fontWeight: 600, marginBottom: 2 }}>{hovered.nom}</div>
                <div style={{ color: hovered.color, fontSize: 12 }}>{hovered.detail}</div>
              </div>
            ) : (
              <div style={{ padding: '10px 14px', borderRadius: 10, background: 'oklch(22% 0.04 265 / .5)', fontSize: 12, color: 'var(--muted)' }}>
                Survolez la carte pour les détails.
              </div>
            )}

            {/* Typologies legend */}
            {layers.typologies && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em' }}>Typologies</div>
                {Object.entries(TYPO_COLORS).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                    <span style={{ width: 10, height: 10, borderRadius: 2, background: v, flexShrink: 0, display: 'inline-block' }} />
                    <span style={{ color: 'var(--muted)' }}>{k}</span>
                  </div>
                ))}
              </div>
            )}

            {layers.centre && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em' }}>Centre-ville (OSM)</div>
                {Object.entries(OSM_ROAD_STYLE).map(([k, s]) => (
                  <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                    <span style={{ width: 16, height: Math.max(2, s.w * 2), background: s.color, flexShrink: 0, display: 'inline-block', borderRadius: 1 }} />
                    <span style={{ color: 'var(--muted)' }}>{s.label}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Voirie legend */}
            {layers.voirie && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em' }}>Voirie</div>
                {[['Reseau national', 'oklch(85% 0.18 55)'], ['Axe structurant revetu', 'oklch(70% 0.15 35)'], ['route secondaire', 'oklch(55% 0.06 265)']].map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                    <span style={{ width: 16, height: 2, background: v, flexShrink: 0, display: 'inline-block', borderRadius: 1 }} />
                    <span style={{ color: 'var(--muted)' }}>{k}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Équipements legend */}
            {layers.equipements && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.05em' }}>Équipements</div>
                {Object.entries(EQUIP_COLORS).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: v, flexShrink: 0, display: 'inline-block' }} />
                    <span style={{ color: 'var(--muted)' }}>{k}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {view === 'table' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div className="view-switch" role="tablist" aria-label="Tableau couche">
            <button className={tableLayer === 'equipements' ? 'active' : ''} onClick={() => setTableLayer('equipements')}>
              Équipements ({feats<GeoFeature>(EQUIPEMENTS_GEO).length})
            </button>
            <button className={tableLayer === 'ecoles' ? 'active' : ''} onClick={() => setTableLayer('ecoles')}>
              Écoles ({feats<GeoFeature>(ECOLES_GEO).length})
            </button>
          </div>

          {tableLayer === 'equipements' && (
            <div className="table-wrap" style={{ maxHeight: 420 }}>
              <table className="data" style={{ fontSize: 12 }}>
                <thead><tr><th>Nom</th><th>Catégorie</th><th>Sous-catégorie</th></tr></thead>
                <tbody>
                  {feats<GeoFeature>(EQUIPEMENTS_GEO).map((f, i) => (
                    <tr key={i}>
                      <td>{String(f.properties.nom ?? '—')}</td>
                      <td><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: EQUIP_COLORS[String(f.properties.categorie ?? '')] ?? '#94a3b8', marginRight: 5 }} />{String(f.properties.categorie ?? '—')}</td>
                      <td style={{ color: 'var(--muted)' }}>{String(f.properties.sous_categ ?? '—')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {tableLayer === 'ecoles' && (
            <div className="table-wrap" style={{ maxHeight: 420 }}>
              <table className="data" style={{ fontSize: 12 }}>
                <thead><tr><th>Établissement</th><th>Niveau</th></tr></thead>
                <tbody>
                  {feats<GeoFeature>(ECOLES_GEO).map((f, i) => (
                    <tr key={i}>
                      <td>{String(f.properties.nom ?? '—')}</td>
                      <td style={{ color: 'var(--muted)' }}>{String(f.properties.sous_categ ?? '—')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <p className="muted" style={{ fontSize: 11, marginTop: 4 }}>
        Source : CERD (Centre d'Études et de Recherches de Djibouti) · Données SIG Djibouti-ville · 8 couches géographiques (arrondissements 4 et 5, Balbala).
        Centre-ville : © contributeurs OpenStreetMap (ODbL), extrait Geofabrik du 14/11/2026 — voirie et noms de quartiers, moins précis que les données CERD.
      </p>
    </div>
  )
}
