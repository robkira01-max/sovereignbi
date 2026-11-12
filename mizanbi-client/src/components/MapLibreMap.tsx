import { useEffect, useRef } from 'react'
import * as maplibregl from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import 'maplibre-gl/dist/maplibre-gl.css'
import djiGeojson from '../data/dj_adm1.json'
import type { LiveTileData } from './LiveTileRenderer'

interface Props {
  data: LiveTileData
  title: string
  unit?: string
  colorScheme?: 'blue' | 'green' | 'red' | 'orange'
  onRegionSelect?: (regionName: string) => void
  selectedRegion?: string | null
}

const GEO_TO_INSTAD: Record<string, string> = {
  'Djibouti':   'Djibouti-ville',
  'Ali Sabieh': 'Ali Sabieh',
  'Arta':       'Arta',
  'Dikhil':     'Dikhil',
  'Tadjourah':  'Tadjourah',
  'Obock':      'Obock',
}
const INSTAD_TO_GEO = Object.fromEntries(
  Object.entries(GEO_TO_INSTAD).map(([geo, ins]) => [ins, geo])
)

const PMTILES_URL =
  (import.meta.env.VITE_PMTILES_URL as string | undefined) ??
  '/tiles/djibouti.pmtiles'

const MAP_STYLE = (pmtilesUrl: string): maplibregl.StyleSpecification => ({
  version: 8,
  glyphs: 'https://fonts.openmaptiles.org/{fontstack}/{range}.pbf',
  sources: {
    protomaps: {
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

const PALETTES: Record<string, [string, string]> = {
  blue:   ['#c7d2fe', '#312e81'],
  green:  ['#d1fae5', '#065f46'],
  red:    ['#fee2e2', '#7f1d1d'],
  orange: ['#ffedd5', '#7c2d12'],
}

function buildGeoJSON(data: LiveTileData): GeoJSON.FeatureCollection {
  const valueByGeo: Record<string, number> = {}
  for (const row of data.rows) {
    const instadName = String(row[0] ?? '')
    const geoName    = INSTAD_TO_GEO[instadName] ?? instadName
    valueByGeo[geoName] = Number(row[1] ?? 0)
  }
  const values = Object.values(valueByGeo).filter(v => !isNaN(v))
  const minVal = values.length ? Math.min(...values) : 0
  const maxVal = values.length ? Math.max(...values) : 1
  return {
    type: 'FeatureCollection',
    features: (djiGeojson as unknown as GeoJSON.FeatureCollection).features.map(feat => {
      const geoName = (feat.properties as Record<string, string>).shapeName
      const val     = valueByGeo[geoName] ?? null
      const norm    = val !== null && maxVal > minVal ? (val - minVal) / (maxVal - minVal) : 0
      return {
        ...feat,
        properties: {
          ...feat.properties,
          _value:      val,
          _norm:       norm,
          _instadName: GEO_TO_INSTAD[geoName] ?? geoName,
        },
      }
    }),
  }
}

let _pmtilsRegistered = false

export function MapLibreMap({ data, title, unit = '', colorScheme = 'blue', onRegionSelect, selectedRegion }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef       = useRef<maplibregl.Map | null>(null)
  const popupRef     = useRef<maplibregl.Popup | null>(null)
  const onRegionSelectRef = useRef(onRegionSelect)
  onRegionSelectRef.current = onRegionSelect

  const [colorLow, colorHigh] = PALETTES[colorScheme] ?? PALETTES.blue
  const valueLabel = data.columns[1]?.replace(/_/g, ' ') ?? ''

  if (!_pmtilsRegistered) {
    const proto = new Protocol()
    maplibregl.addProtocol('pmtiles', proto.tile)
    _pmtilsRegistered = true
  }

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    const map = new maplibregl.Map({
      container: containerRef.current,
      style:     MAP_STYLE(PMTILES_URL),
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
      const geojson = buildGeoJSON(data)
      map.addSource('regions', { type: 'geojson', data: geojson })
      map.addLayer({
        id: 'regions-fill', type: 'fill', source: 'regions',
        paint: {
          'fill-color': ['interpolate', ['linear'], ['get', '_norm'], 0, colorLow, 1, colorHigh],
          'fill-opacity': 0.82,
        },
      })
      map.addLayer({
        id: 'regions-outline', type: 'line', source: 'regions',
        paint: { 'line-color': '#ffffff', 'line-width': 1, 'line-opacity': 0.7 },
      })
      map.addLayer({
        id: 'regions-selected', type: 'line', source: 'regions',
        filter: ['==', '_instadName', ''],
        paint: { 'line-color': '#ffffff', 'line-width': 3, 'line-opacity': 0 },
      })
      map.addLayer({
        id: 'regions-label', type: 'symbol', source: 'regions',
        layout: {
          'text-field': ['format',
            ['get', '_instadName'], { 'font-scale': 1 }, '\n', {},
            ['to-string', ['get', '_value']], { 'font-scale': 0.85 }],
          'text-size': 11,
          'text-anchor': 'center',
        },
        paint: { 'text-color': '#ffffff', 'text-halo-color': '#1e1b4b', 'text-halo-width': 1.5 },
      })

      map.on('mouseenter', 'regions-fill', (e) => {
        map.getCanvas().style.cursor = 'pointer'
        const feat = e.features?.[0]
        if (!feat || !popupRef.current) return
        const p   = feat.properties as Record<string, unknown>
        const val = p._value !== null ? `${Number(p._value).toLocaleString('fr-FR')} ${unit}` : '—'
        popupRef.current
          .setLngLat(e.lngLat)
          .setHTML(`<strong>${p._instadName}</strong><br/>${valueLabel}: <b>${val}</b>`)
          .addTo(map)
      })
      map.on('mouseleave', 'regions-fill', () => {
        map.getCanvas().style.cursor = ''
        popupRef.current?.remove()
      })
      map.on('click', 'regions-fill', (e) => {
        const feat = e.features?.[0]
        if (!feat) return
        onRegionSelectRef.current?.(String((feat.properties as Record<string, unknown>)._instadName ?? ''))
      })
    })

    return () => {
      popupRef.current?.remove()
      map.remove()
      mapRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return
    const src = map.getSource('regions') as maplibregl.GeoJSONSource | undefined
    if (!src) return
    src.setData(buildGeoJSON(data))
    map.setPaintProperty('regions-fill', 'fill-color', [
      'interpolate', ['linear'], ['get', '_norm'], 0, colorLow, 1, colorHigh,
    ])
    if (map.getLayer('regions-selected')) {
      map.setPaintProperty('regions-selected', 'line-opacity', selectedRegion ? 1 : 0)
      map.setFilter('regions-selected', ['==', '_instadName', selectedRegion ?? ''])
    }
  }, [data, colorLow, colorHigh, selectedRegion])

  return (
    <div data-testid="tile-map" style={{ width: '100%', position: 'relative' }}>
      <div ref={containerRef} style={{ width: '100%', height: 340, borderRadius: 8, overflow: 'hidden' }} />
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '6px 4px 0', fontSize: '0.7rem', color: 'var(--muted, #94a3b8)',
      }}>
        <span style={{
          display: 'inline-block', width: 90, height: 8, borderRadius: 4,
          background: `linear-gradient(to right, ${colorLow}, ${colorHigh})`,
        }} />
        <span>{title} {unit ? `(${unit})` : ''} · bas → élevé</span>
      </div>
    </div>
  )
}
