/**
 * P-025 — Spatial analysis UI: buffer, intersection, density
 * Viewer-accessible; queries POST /api/v1/geo/analyze
 */
import { useEffect, useState } from 'react'
import { useLocale } from '../hooks/useLocale'

interface AnalysisType {
  id: string
  description: string
}

interface GeoLayer {
  id: string
  name_fr: string
  name_en: string
  enabled: boolean
}

interface AnalysisResult {
  [key: string]: unknown
}

interface Props {
  apiKey: string
}

const P025_ANALYSES = ['buffer', 'intersection', 'density']

export function SpatialAnalysis({ apiKey }: Props) {
  const { t, locale } = useLocale()

  const [analyses, setAnalyses] = useState<AnalysisType[]>([])
  const [layers, setLayers] = useState<GeoLayer[]>([])
  const [layerId, setLayerId] = useState('')
  const [analysis, setAnalysis] = useState('buffer')
  const [layerIdB, setLayerIdB] = useState('')
  // buffer params
  const [lon, setLon] = useState('43.145')
  const [lat, setLat] = useState('11.589')
  const [radiusKm, setRadiusKm] = useState('50')
  // density param
  const [valueCol, setValueCol] = useState('')

  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<AnalysisResult[] | null>(null)
  const [rowCount, setRowCount] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const headers = { 'X-Api-Key': apiKey, 'Content-Type': 'application/json' }

  useEffect(() => {
    fetch('/api/v1/geo/analyze/types', { headers })
      .then(r => r.ok ? r.json() : null)
      .then(j => j && setAnalyses((j.analyses as AnalysisType[]).filter(a => P025_ANALYSES.includes(a.id))))
      .catch(() => null)

    fetch('/api/v1/geo/catalog', { headers })
      .then(r => r.ok ? r.json() : null)
      .then(j => j && setLayers(j.layers as GeoLayer[]))
      .catch(() => null)
  }, [apiKey])

  const layerName = (layer: GeoLayer) =>
    locale === 'fr' ? layer.name_fr : layer.name_en || layer.name_fr

  const run = async () => {
    if (!layerId) { setError(t('spatial_analysis.error_no_layer')); return }
    setLoading(true)
    setError(null)
    setResults(null)

    const params: Record<string, unknown> = {}
    if (analysis === 'buffer') {
      params.lon = parseFloat(lon)
      params.lat = parseFloat(lat)
      params.radius_km = parseFloat(radiusKm)
    }
    if (analysis === 'density' && valueCol.trim()) {
      params.value_col = valueCol.trim()
    }

    const body: Record<string, unknown> = { layer_id: layerId, analysis, params }
    if (analysis === 'intersection') {
      if (!layerIdB) { setError(t('spatial_analysis.error_no_layer_b')); setLoading(false); return }
      body.layer_id_b = layerIdB
    }

    try {
      const res = await fetch('/api/v1/geo/analyze', {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const j = await res.json().catch(() => null)
        setError(j?.detail ?? t('spatial_analysis.error_server'))
      } else {
        const j = await res.json()
        setResults(j.results)
        setRowCount(j.row_count)
      }
    } catch {
      setError(t('spatial_analysis.error_server'))
    } finally {
      setLoading(false)
    }
  }

  const resultKeys = results && results.length > 0 ? Object.keys(results[0]) : []

  return (
    <div data-testid="spatial-analysis" style={{ maxWidth: 700 }}>
      <h2 style={{ marginBottom: 4 }}>{t('spatial_analysis.title')}</h2>
      <p style={{ color: '#666', fontSize: 14, marginBottom: 16 }}>{t('spatial_analysis.subtitle')}</p>

      {/* Analysis selector */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
        <label>
          <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>{t('spatial_analysis.analysis')}</div>
          <select
            data-testid="spatial-analysis-type"
            value={analysis}
            onChange={e => { setAnalysis(e.target.value); setResults(null) }}
            style={{ width: '100%', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 4 }}
          >
            {analyses.map(a => (
              <option key={a.id} value={a.id}>{a.id}</option>
            ))}
          </select>
        </label>

        <label>
          <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>{t('spatial_analysis.layer_a')}</div>
          <select
            data-testid="spatial-analysis-layer-a"
            value={layerId}
            onChange={e => setLayerId(e.target.value)}
            style={{ width: '100%', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 4 }}
          >
            <option value="">— {t('spatial_analysis.select_layer')} —</option>
            {layers.map(l => (
              <option key={l.id} value={l.id}>{layerName(l)}</option>
            ))}
          </select>
        </label>
      </div>

      {/* Contextual params */}
      {analysis === 'buffer' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 16 }}>
          <label>
            <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>{t('spatial_analysis.lon')}</div>
            <input
              data-testid="spatial-analysis-lon"
              type="number" step="any"
              value={lon}
              onChange={e => setLon(e.target.value)}
              style={{ width: '100%', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 4, boxSizing: 'border-box' }}
            />
          </label>
          <label>
            <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>{t('spatial_analysis.lat')}</div>
            <input
              data-testid="spatial-analysis-lat"
              type="number" step="any"
              value={lat}
              onChange={e => setLat(e.target.value)}
              style={{ width: '100%', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 4, boxSizing: 'border-box' }}
            />
          </label>
          <label>
            <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>{t('spatial_analysis.radius_km')}</div>
            <input
              data-testid="spatial-analysis-radius"
              type="number" step="any" min="0"
              value={radiusKm}
              onChange={e => setRadiusKm(e.target.value)}
              style={{ width: '100%', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 4, boxSizing: 'border-box' }}
            />
          </label>
        </div>
      )}

      {analysis === 'intersection' && (
        <div style={{ marginBottom: 16 }}>
          <label>
            <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>{t('spatial_analysis.layer_b')}</div>
            <select
              data-testid="spatial-analysis-layer-b"
              value={layerIdB}
              onChange={e => setLayerIdB(e.target.value)}
              style={{ width: '100%', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 4 }}
            >
              <option value="">— {t('spatial_analysis.select_layer')} —</option>
              {layers.filter(l => l.id !== layerId).map(l => (
                <option key={l.id} value={l.id}>{layerName(l)}</option>
              ))}
            </select>
          </label>
        </div>
      )}

      {analysis === 'density' && (
        <div style={{ marginBottom: 16 }}>
          <label>
            <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>{t('spatial_analysis.value_col')}</div>
            <input
              data-testid="spatial-analysis-value-col"
              value={valueCol}
              onChange={e => setValueCol(e.target.value)}
              placeholder={t('spatial_analysis.value_col_placeholder')}
              style={{ width: '100%', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 4, boxSizing: 'border-box' }}
            />
          </label>
        </div>
      )}

      {error && (
        <div
          data-testid="spatial-analysis-error"
          role="alert"
          style={{ background: '#fff0f0', border: '1px solid #f88', borderRadius: 4, padding: '8px 12px', marginBottom: 12, color: '#c00' }}
        >
          {error}
        </div>
      )}

      <button
        data-testid="spatial-analysis-run"
        onClick={run}
        disabled={loading}
        style={{
          padding: '8px 24px',
          background: loading ? '#aaa' : '#1a4a8c',
          color: '#fff',
          border: 'none',
          borderRadius: 4,
          cursor: loading ? 'default' : 'pointer',
          fontWeight: 600,
          marginBottom: 16,
        }}
      >
        {loading ? t('spatial_analysis.running') : t('spatial_analysis.run')}
      </button>

      {results !== null && (
        <div data-testid="spatial-analysis-results">
          <div style={{ fontSize: 13, color: '#555', marginBottom: 8 }}>
            {rowCount} {t('spatial_analysis.rows')}
          </div>
          {results.length === 0 ? (
            <p style={{ color: '#888' }}>{t('spatial_analysis.no_results')}</p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 13 }}>
                <thead>
                  <tr>
                    {resultKeys.map(k => (
                      <th key={k} style={{ textAlign: 'left', padding: '6px 10px', background: '#f0f4ff', borderBottom: '2px solid #ccc' }}>
                        {k}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {results.map((row, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                      {resultKeys.map(k => (
                        <td key={k} style={{ padding: '5px 10px' }}>
                          {row[k] !== null && row[k] !== undefined ? String(row[k]) : '—'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
