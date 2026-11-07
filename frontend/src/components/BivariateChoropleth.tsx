/**
 * BivariateChoropleth — two variables on one map, 3×3 colour matrix.
 *
 * Columns expected: [region, var1, var2]
 * Options: x1_label, x2_label, colorScheme ('classic' | 'teal-orange')
 *
 * Classification: equal-count quantiles (terciles) for each variable.
 * Colour matrix: row = var1 class (0–2), col = var2 class (0–2).
 */
import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import 'maplibre-gl/dist/maplibre-gl.css'
import djiGeojson from '../data/dji_adm1.geojson'

// ── Types ────────────────────────────────────────────────────────────────────

interface TileData {
  columns: string[]
  rows: unknown[][]
}

interface Props {
  data: TileData
  title: string
  unit?: string
  x1_label?: string
  x2_label?: string
  colorScheme?: 'classic' | 'teal-orange'
}

// ── Colour palettes (row = var1 low→high, col = var2 low→high) ──────────────

// Classic bivariate (blue × pink — Schroeder / US Census)
const PALETTE_CLASSIC: string[][] = [
  ['#e8e8e8', '#ace4e4', '#5ac8c8'],
  ['#dfb0d6', '#a5add3', '#5698b9'],
  ['#be64ac', '#8c62aa', '#3b4994'],
]

// MizanBI brand: teal (var2) × orange (var1)
const PALETTE_TEAL_ORANGE: string[][] = [
  ['#f0f0f0', '#a8ddb5', '#43a2ca'],
  ['#fed976', '#78c679', '#238443'],
  ['#fc4e2a', '#bd0026', '#800026'],
]

const PALETTES: Record<string, string[][]> = {
  classic:      PALETTE_CLASSIC,
  'teal-orange': PALETTE_TEAL_ORANGE,
}

// ── Constants ────────────────────────────────────────────────────────────────

const GEO_TO_INSTAD: Record<string, string> = {
  'Djibouti':   'Djibouti-ville',
  'Ali Sabieh': 'Ali Sabieh',
  'Arta':        'Arta',
  'Dikhil':      'Dikhil',
  'Tadjourah':   'Tadjourah',
  'Obock':       'Obock',
}
const INSTAD_TO_GEO = Object.fromEntries(
  Object.entries(GEO_TO_INSTAD).map(([g, i]) => [i, g])
)

const PMTILES_URL =
  (import.meta.env.VITE_PMTILES_URL as string | undefined) ??
  '/tiles/djibouti.pmtiles'

const BASE_STYLE = (pmtilesUrl: string): maplibregl.StyleSpecification => ({
  version: 8,
  glyphs: 'https://fonts.openmaptiles.org/{fontstack}/{range}.pbf',
  sources: {
    protomaps: {
      type: 'vector',
      url: `pmtiles://${pmtilesUrl}`,
      attribution: '© <a href="https://protomaps.com">Protomaps</a> · <a href="https://www.openstreetmap.org/copyright">OSM</a>',
    },
  },
  layers: [
    { id: 'bg',    type: 'background', paint: { 'background-color': '#1e293b' } },
    { id: 'water', type: 'fill', source: 'protomaps', 'source-layer': 'water', paint: { 'fill-color': '#0c2340' } },
    { id: 'roads', type: 'line', source: 'protomaps', 'source-layer': 'roads', paint: { 'line-color': '#334155', 'line-width': 0.8 } },
  ],
})

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Assign tercile class (0, 1, 2) to each sorted value. */
function tercileClass(values: number[]): number[] {
  const sorted = [...values].sort((a, b) => a - b)
  const n = sorted.length
  const t1 = sorted[Math.floor(n / 3)]
  const t2 = sorted[Math.floor((2 * n) / 3)]
  return values.map(v => (v <= t1 ? 0 : v <= t2 ? 1 : 2))
}

function buildGeoJSON(data: TileData, palette: string[][]): GeoJSON.FeatureCollection {
  const regionIdx = 0
  const v1Idx = 1
  const v2Idx = 2

  const v1ByGeo: Record<string, number> = {}
  const v2ByGeo: Record<string, number> = {}

  for (const row of data.rows) {
    const ins = String(row[regionIdx] ?? '')
    const geo = INSTAD_TO_GEO[ins] ?? ins
    v1ByGeo[geo] = Number(row[v1Idx] ?? 0)
    v2ByGeo[geo] = Number(row[v2Idx] ?? 0)
  }

  const geoNames = Object.keys(v1ByGeo)
  const v1Values = geoNames.map(g => v1ByGeo[g])
  const v2Values = geoNames.map(g => v2ByGeo[g])
  const v1Classes = tercileClass(v1Values)
  const v2Classes = tercileClass(v2Values)

  const classMap: Record<string, { class: number; color: string; v1: number; v2: number }> = {}
  geoNames.forEach((geo, i) => {
    const c1 = v1Classes[i]
    const c2 = v2Classes[i]
    classMap[geo] = {
      class: c1 * 3 + c2,
      color: palette[c1][c2],
      v1: v1Values[i],
      v2: v2Values[i],
    }
  })

  return {
    type: 'FeatureCollection',
    features: (djiGeojson as GeoJSON.FeatureCollection).features.map(feat => {
      const geoName = (feat.properties as Record<string, string>).shapeName
      const info = classMap[geoName]
      return {
        ...feat,
        properties: {
          ...feat.properties,
          _bivClass:   info?.class  ?? -1,
          _bivColor:   info?.color  ?? '#888',
          _v1:         info?.v1     ?? null,
          _v2:         info?.v2     ?? null,
          _instadName: GEO_TO_INSTAD[geoName] ?? geoName,
        },
      }
    }),
  }
}

// ── Protocol singleton ───────────────────────────────────────────────────────

let _registered = false

// ── Component ────────────────────────────────────────────────────────────────

export function BivariateChoropleth({
  data, title, unit = '', x1_label, x2_label, colorScheme = 'classic',
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef       = useRef<maplibregl.Map | null>(null)
  const popupRef     = useRef<maplibregl.Popup | null>(null)

  const palette     = PALETTES[colorScheme] ?? PALETTE_CLASSIC
  const col1Label   = x1_label ?? data.columns[1]?.replace(/_/g, ' ') ?? 'Variable 1'
  const col2Label   = x2_label ?? data.columns[2]?.replace(/_/g, ' ') ?? 'Variable 2'

  if (!_registered) {
    const proto = new Protocol()
    maplibregl.addProtocol('pmtiles', proto.tile)
    _registered = true
  }

  // Init map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      style:     BASE_STYLE(PMTILES_URL),
      center:    [42.65, 11.85],
      zoom:      7.2,
      minZoom:   6,
      maxZoom:   13,
      attributionControl: false,
    })
    mapRef.current = map

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')

    popupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false })

    map.on('load', () => {
      const geojson = buildGeoJSON(data, palette)

      map.addSource('biv-regions', { type: 'geojson', data: geojson })

      // Build fill-color match expression: class → color
      const matchExpr: maplibregl.ExpressionSpecification = [
        'match', ['get', '_bivClass'],
        ...palette.flatMap((row, r) =>
          row.map((color, c) => [r * 3 + c, color] as [number, string])
        ).flat(),
        '#888888',
      ]

      map.addLayer({
        id: 'biv-fill', type: 'fill', source: 'biv-regions',
        paint: { 'fill-color': matchExpr, 'fill-opacity': 0.85 },
      })
      map.addLayer({
        id: 'biv-outline', type: 'line', source: 'biv-regions',
        paint: { 'line-color': '#ffffff', 'line-width': 0.9, 'line-opacity': 0.7 },
      })
      map.addLayer({
        id: 'biv-label', type: 'symbol', source: 'biv-regions',
        layout: {
          'text-field': ['get', '_instadName'],
          'text-size': 10,
          'text-anchor': 'center',
        },
        paint: {
          'text-color': '#ffffff',
          'text-halo-color': '#0f172a',
          'text-halo-width': 1.5,
        },
      })

      // Hover popup
      map.on('mouseenter', 'biv-fill', (e) => {
        map.getCanvas().style.cursor = 'pointer'
        const feat = e.features?.[0]
        if (!feat || !popupRef.current) return
        const p  = feat.properties as Record<string, unknown>
        const v1 = p._v1 !== null ? `${Number(p._v1).toLocaleString('fr-FR')} ${unit}` : '—'
        const v2 = p._v2 !== null ? `${Number(p._v2).toLocaleString('fr-FR')} ${unit}` : '—'
        popupRef.current
          .setLngLat(e.lngLat)
          .setHTML(
            `<strong>${p._instadName}</strong><br/>` +
            `${col1Label}: <b>${v1}</b><br/>` +
            `${col2Label}: <b>${v2}</b>`
          )
          .addTo(map)
      })
      map.on('mouseleave', 'biv-fill', () => {
        map.getCanvas().style.cursor = ''
        popupRef.current?.remove()
      })
    })

    return () => {
      popupRef.current?.remove()
      map.remove()
      mapRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Auto-update on data change
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return
    const src = map.getSource('biv-regions') as maplibregl.GeoJSONSource | undefined
    if (!src) return
    src.setData(buildGeoJSON(data, palette))
  }, [data, palette])

  // ── 3×3 legend ─────────────────────────────────────────────────────────────
  const CELL = 18
  const GRID = 3 * CELL

  return (
    <div data-testid="tile-map-bivariate" style={{ width: '100%', position: 'relative' }}>
      <div
        ref={containerRef}
        style={{ width: '100%', height: 340, borderRadius: 8, overflow: 'hidden' }}
      />

      {/* 3×3 legend + axis labels */}
      <div style={{
        display: 'flex', alignItems: 'flex-end', gap: 8,
        padding: '8px 4px 0', fontSize: '0.68rem', color: 'var(--muted, #94a3b8)',
      }}>
        <div style={{ position: 'relative' }}>
          {/* grid rows — var1 high at top */}
          {[2, 1, 0].map(r => (
            <div key={r} style={{ display: 'flex' }}>
              {[0, 1, 2].map(c => (
                <div key={c} style={{
                  width: CELL, height: CELL,
                  background: palette[r][c],
                  border: '0.5px solid rgba(255,255,255,0.15)',
                }} />
              ))}
            </div>
          ))}
          {/* var2 → (bottom label) */}
          <div style={{
            position: 'absolute', bottom: -16, left: 0, width: GRID,
            textAlign: 'center', fontSize: '0.62rem', color: 'var(--muted, #94a3b8)',
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            → {col2Label}
          </div>
          {/* var1 ↑ (left label rotated) */}
          <div style={{
            position: 'absolute', top: 0, left: -(GRID * 0.6),
            height: GRID, width: GRID * 0.6,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <span style={{
              writingMode: 'vertical-rl', transform: 'rotate(180deg)',
              fontSize: '0.62rem', color: 'var(--muted, #94a3b8)',
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
              maxHeight: GRID,
            }}>
              ↑ {col1Label}
            </span>
          </div>
        </div>

        <span style={{ marginLeft: 4, opacity: 0.7 }}>
          {title} {unit ? `(${unit})` : ''}
        </span>
      </div>
    </div>
  )
}
