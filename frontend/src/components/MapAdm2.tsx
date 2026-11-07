import { useEffect, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useLocale } from '../hooks/useLocale'

// ── Types ────────────────────────────────────────────────────────────────────

interface TileData {
  columns: string[]
  rows: unknown[][]
}

interface Props {
  data: TileData
  title: string
  unit?: string
  colorScheme?: 'blue' | 'green' | 'red' | 'orange'
  options?: {
    level?: 'adm2' | 'quartiers'
    showLevelToggle?: boolean
  }
}

// ── Constants ────────────────────────────────────────────────────────────────

const PALETTES: Record<string, [string, string]> = {
  blue:   ['#c7d2fe', '#312e81'],
  green:  ['#d1fae5', '#065f46'],
  red:    ['#fee2e2', '#7f1d1d'],
  orange: ['#ffedd5', '#7c2d12'],
}

const PMTILES_URL =
  (import.meta.env.VITE_PMTILES_URL as string | undefined) ??
  '/tiles/djibouti.pmtiles'

const MAP_STYLE = (pmtilesUrl: string): maplibregl.StyleSpecification => ({
  version: 8,
  glyphs: 'https://fonts.openmaptiles.org/{fontstack}/{range}.pbf',
  sources: {
    'protomaps': {
      type: 'vector',
      url: `pmtiles://${pmtilesUrl}`,
      attribution: '© <a href="https://protomaps.com">Protomaps</a> · <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    },
  },
  layers: [
    { id: 'background', type: 'background', paint: { 'background-color': '#1e293b' } },
    { id: 'water', type: 'fill', source: 'protomaps', 'source-layer': 'water', paint: { 'fill-color': '#0c2340' } },
    { id: 'landuse', type: 'fill', source: 'protomaps', 'source-layer': 'landuse', paint: { 'fill-color': '#1e293b', 'fill-opacity': 0.4 } },
    { id: 'roads', type: 'line', source: 'protomaps', 'source-layer': 'roads', paint: { 'line-color': '#334155', 'line-width': 1 } },
  ],
})

// Zoom + center per level
const LEVEL_VIEW: Record<string, { center: [number, number]; zoom: number }> = {
  adm2:      { center: [42.65, 11.85], zoom: 7.2 },
  quartiers: { center: [43.11, 11.56], zoom: 10.5 },
}

// ── Helper: map data onto GeoJSON features ────────────────────────────────────

function joinData(
  geojson: GeoJSON.FeatureCollection,
  data: TileData,
  nameKey: string,
): GeoJSON.FeatureCollection {
  const regionIdx = 0
  const valueIdx  = 1
  const valueMap: Record<string, number> = {}
  for (const row of data.rows) {
    valueMap[String(row[regionIdx] ?? '')] = Number(row[valueIdx] ?? 0)
  }
  const values = Object.values(valueMap).filter(v => !isNaN(v))
  const minVal = values.length ? Math.min(...values) : 0
  const maxVal = values.length ? Math.max(...values) : 1

  return {
    ...geojson,
    features: geojson.features.map(feat => {
      const featureName = String((feat.properties as Record<string, unknown>)[nameKey] ?? '')
      const val  = valueMap[featureName] ?? null
      const norm = val !== null && maxVal > minVal ? (val - minVal) / (maxVal - minVal) : 0
      return {
        ...feat,
        properties: {
          ...feat.properties,
          _value:  val,
          _norm:   norm,
          _minVal: minVal,
          _maxVal: maxVal,
          _label:  featureName,
        },
      }
    }),
  }
}

// ── Component ─────────────────────────────────────────────────────────────────

let _pmtilsRegistered = false

export function MapAdm2({ data, title, unit = '', colorScheme = 'blue', options = {} }: Props) {
  const { t } = useLocale()
  const { showLevelToggle = true } = options

  const [level, setLevel]       = useState<'adm2' | 'quartiers'>(options.level ?? 'adm2')
  const [geoData, setGeoData]   = useState<GeoJSON.FeatureCollection | null>(null)
  const [geoError, setGeoError] = useState<string | null>(null)

  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef       = useRef<maplibregl.Map | null>(null)
  const popupRef     = useRef<maplibregl.Popup | null>(null)

  const [colorLow, colorHigh] = PALETTES[colorScheme] ?? PALETTES.blue
  const valueLabel = data.columns[1]?.replace(/_/g, ' ') ?? ''
  const nameKey    = level === 'quartiers' ? 'name' : 'name'

  // Fetch GeoJSON from backend
  useEffect(() => {
    setGeoData(null)
    setGeoError(null)
    fetch(`/api/v1/geo/dj/${level}`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((fc: GeoJSON.FeatureCollection) => setGeoData(fc))
      .catch(err => setGeoError(String(err)))
  }, [level])

  // Register PMTiles once
  if (!_pmtilsRegistered) {
    const proto = new Protocol()
    maplibregl.addProtocol('pmtiles', proto.tile)
    _pmtilsRegistered = true
  }

  // Init map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    const view = LEVEL_VIEW[level]
    const map = new maplibregl.Map({
      container: containerRef.current,
      style:     MAP_STYLE(PMTILES_URL),
      center:    view.center,
      zoom:      view.zoom,
      minZoom:   5,
      maxZoom:   15,
      attributionControl: false,
    })
    mapRef.current = map
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')
    popupRef.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false })
    return () => {
      popupRef.current?.remove()
      map.remove()
      mapRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Add/update choropleth when geoData or data changes
  useEffect(() => {
    const map = mapRef.current
    if (!map || !geoData) return

    const apply = () => {
      const joined = joinData(geoData, data, nameKey)

      if (map.getSource('adm2-regions')) {
        ;(map.getSource('adm2-regions') as maplibregl.GeoJSONSource).setData(joined)
        map.setPaintProperty('adm2-fill', 'fill-color', [
          'interpolate', ['linear'], ['get', '_norm'], 0, colorLow, 1, colorHigh,
        ])
        return
      }

      map.addSource('adm2-regions', { type: 'geojson', data: joined })

      map.addLayer({
        id: 'adm2-fill', type: 'fill', source: 'adm2-regions',
        paint: {
          'fill-color': ['interpolate', ['linear'], ['get', '_norm'], 0, colorLow, 1, colorHigh],
          'fill-opacity': 0.82,
        },
      })
      map.addLayer({
        id: 'adm2-outline', type: 'line', source: 'adm2-regions',
        paint: { 'line-color': '#ffffff', 'line-width': 1, 'line-opacity': 0.7 },
      })
      map.addLayer({
        id: 'adm2-label', type: 'symbol', source: 'adm2-regions',
        layout: {
          'text-field': ['format',
            ['get', '_label'], { 'font-scale': 1 }, '\n', {},
            ['to-string', ['get', '_value']], { 'font-scale': 0.82 }],
          'text-size': level === 'quartiers' ? 10 : 11,
          'text-anchor': 'center',
        },
        paint: { 'text-color': '#ffffff', 'text-halo-color': '#1e1b4b', 'text-halo-width': 1.5 },
      })

      map.on('mouseenter', 'adm2-fill', (e) => {
        map.getCanvas().style.cursor = 'pointer'
        const feat = e.features?.[0]
        if (!feat || !popupRef.current) return
        const p   = feat.properties as Record<string, unknown>
        const val = p._value !== null ? `${Number(p._value).toLocaleString('fr-FR')} ${unit}` : '—'
        const pop = p.population_est ? `<br/>Pop. : ${Number(p.population_est).toLocaleString('fr-FR')}` : ''
        popupRef.current
          .setLngLat(e.lngLat)
          .setHTML(`<strong>${p._label}</strong><br/>${valueLabel}: <b>${val}</b>${pop}`)
          .addTo(map)
      })
      map.on('mouseleave', 'adm2-fill', () => {
        map.getCanvas().style.cursor = ''
        popupRef.current?.remove()
      })
    }

    if (map.isStyleLoaded()) apply()
    else map.once('load', apply)

    // Fly to new level view
    const view = LEVEL_VIEW[level]
    map.flyTo({ center: view.center, zoom: view.zoom, duration: 800 })
  }, [geoData, data, colorLow, colorHigh, level, nameKey, unit, valueLabel])

  // Remove old layers on level change before re-adding
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return
    for (const id of ['adm2-label', 'adm2-outline', 'adm2-fill']) {
      if (map.getLayer(id)) map.removeLayer(id)
    }
    if (map.getSource('adm2-regions')) map.removeSource('adm2-regions')
  }, [level])

  return (
    <div data-testid="tile-map-adm2" style={{ width: '100%', position: 'relative' }}>
      {showLevelToggle && (
        <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
          {(['adm2', 'quartiers'] as const).map(l => (
            <button
              key={l}
              data-testid={`map-level-btn-${l}`}
              onClick={() => setLevel(l)}
              style={{
                padding: '3px 10px', fontSize: '0.72rem', borderRadius: 4,
                border: `1px solid ${level === l ? colorHigh : '#475569'}`,
                background: level === l ? colorHigh : 'transparent',
                color: level === l ? '#fff' : 'var(--muted, #94a3b8)',
                cursor: 'pointer',
              }}
            >
              {l === 'adm2' ? t('map.level_adm2') : t('map.level_quartiers')}
            </button>
          ))}
        </div>
      )}
      {geoError && (
        <div data-testid="map-geo-error" style={{ color: '#f87171', fontSize: '0.75rem', marginBottom: 4 }}>
          ⚠ {geoError}
        </div>
      )}
      <div
        ref={containerRef}
        style={{ width: '100%', height: 340, borderRadius: 8, overflow: 'hidden' }}
      />
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '6px 4px 0', fontSize: '0.7rem', color: 'var(--muted, #94a3b8)',
      }}>
        <span style={{
          display: 'inline-block', width: 90, height: 8, borderRadius: 4,
          background: `linear-gradient(to right, ${colorLow}, ${colorHigh})`,
        }} />
        <span>{title} {unit ? `(${unit})` : ''} · bas → élevé</span>
        {level === 'quartiers' && (
          <span style={{ marginLeft: 'auto', fontSize: '0.65rem', color: '#64748b' }}>
            ⚠ {t('map.quartiers_disclaimer')}
          </span>
        )}
      </div>
    </div>
  )
}
