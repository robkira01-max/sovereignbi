/**
 * GeoAI — P-027: natural-language geographic analysis assistant.
 * Sends a question to POST /api/v1/geo/ai-query and renders results:
 *   - Prose explanation
 *   - Choropleth map (via TileRenderer) if map_config present
 *   - Data table otherwise
 */
import { useState } from 'react'
import { apiFetch } from '../api/client'
import { useLocale } from '../hooks/useLocale'
import { TileRenderer } from './TileRenderer'

// ── Types ─────────────────────────────────────────────────────────────────────

interface GeoIntent {
  analysis: string
  layer_id: string
  params: Record<string, unknown>
  reasoning: string
}

interface MapConfig {
  type: string
  layer_id: string
  value_col?: string
}

interface GeoAIResult {
  intent: GeoIntent | null
  columns: string[]
  rows: unknown[][]
  map_config: MapConfig | null
  prose: string
  error: string | null
}

interface Props {
  apiKey?: string
}

// ── Component ─────────────────────────────────────────────────────────────────

export function GeoAI({ apiKey: _apiKey }: Props) {
  const { t } = useLocale()
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<GeoAIResult | null>(null)
  const [view, setView] = useState<'map' | 'table'>('map')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const q = question.trim()
    if (!q) return
    setLoading(true)
    setResult(null)
    try {
      const data = await apiFetch<GeoAIResult>('/api/v1/geo/ai-query', {
        method: 'POST',
        body: JSON.stringify({ question: q, locale: 'fr' }),
      })
      setResult(data)
      setView(data.map_config ? 'map' : 'table')
    } catch (err) {
      setResult({
        intent: null,
        columns: [],
        rows: [],
        map_config: null,
        prose: '',
        error: err instanceof Error ? err.message : String(err),
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div data-testid="geo-ai" style={{ maxWidth: 760, margin: '0 auto', padding: '0 8px' }}>
      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>
          {t('geo_ai.title')}
        </h3>
        <p style={{ margin: '4px 0 0', fontSize: '0.82rem', color: 'var(--muted, #94a3b8)' }}>
          {t('geo_ai.subtitle')}
        </p>
      </div>

      {/* Input form */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <input
          data-testid="geo-ai-input"
          type="text"
          value={question}
          onChange={e => setQuestion(e.target.value)}
          placeholder={t('geo_ai.placeholder')}
          maxLength={500}
          disabled={loading}
          style={{
            flex: 1,
            padding: '8px 12px',
            fontSize: '0.9rem',
            border: '1px solid var(--border, #d1d5db)',
            borderRadius: 8,
            background: 'var(--surface, #fff)',
            color: 'var(--fg, #111)',
            outline: 'none',
          }}
        />
        <button
          data-testid="geo-ai-submit"
          type="submit"
          disabled={loading || !question.trim()}
          style={{
            padding: '8px 20px',
            fontSize: '0.9rem',
            fontWeight: 600,
            background: 'var(--brand, #3b82f6)',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            cursor: loading ? 'wait' : 'pointer',
            opacity: loading || !question.trim() ? 0.6 : 1,
          }}
        >
          {loading ? t('geo_ai.asking') : t('geo_ai.ask')}
        </button>
      </form>

      {/* Results */}
      {result && (
        <div data-testid="geo-ai-result">
          {/* Error */}
          {result.error && (
            <div
              data-testid="geo-ai-error"
              style={{
                padding: '10px 14px',
                background: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: 8,
                color: '#b91c1c',
                fontSize: '0.85rem',
              }}
            >
              {result.error}
            </div>
          )}

          {/* Prose + reasoning */}
          {!result.error && result.prose && (
            <div style={{ marginBottom: 12 }}>
              <p
                data-testid="geo-ai-prose"
                style={{ margin: 0, fontSize: '0.9rem', lineHeight: 1.6 }}
              >
                {result.prose}
              </p>
              {result.intent?.reasoning && (
                <p style={{ margin: '6px 0 0', fontSize: '0.75rem', color: 'var(--muted, #94a3b8)' }}>
                  <em>{t('geo_ai.reasoning_label')} :</em> {result.intent.reasoning}
                </p>
              )}
            </div>
          )}

          {/* View toggle (map / table) */}
          {!result.error && result.rows.length > 0 && (
            <>
              <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
                {result.map_config && (
                  <button
                    data-testid="geo-ai-view-map"
                    onClick={() => setView('map')}
                    style={{
                      padding: '4px 14px',
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      border: `1px solid ${view === 'map' ? 'var(--brand, #3b82f6)' : '#d1d5db'}`,
                      background: view === 'map' ? 'var(--brand, #3b82f6)' : 'transparent',
                      color: view === 'map' ? '#fff' : 'var(--muted, #64748b)',
                      borderRadius: 6,
                      cursor: 'pointer',
                    }}
                  >
                    {t('geo_ai.result_map')}
                  </button>
                )}
                <button
                  data-testid="geo-ai-view-table"
                  onClick={() => setView('table')}
                  style={{
                    padding: '4px 14px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    border: `1px solid ${view === 'table' ? 'var(--brand, #3b82f6)' : '#d1d5db'}`,
                    background: view === 'table' ? 'var(--brand, #3b82f6)' : 'transparent',
                    color: view === 'table' ? '#fff' : 'var(--muted, #64748b)',
                    borderRadius: 6,
                    cursor: 'pointer',
                  }}
                >
                  {t('geo_ai.result_table')}
                </button>
              </div>

              {/* Map view */}
              {view === 'map' && result.map_config && (
                <div data-testid="geo-ai-map-view">
                  <TileRenderer
                    type={result.map_config.type}
                    title={result.intent?.analysis ?? ''}
                    data={{ columns: result.columns, rows: result.rows }}
                  />
                </div>
              )}

              {/* Table view */}
              {view === 'table' && (
                <div
                  data-testid="geo-ai-table-view"
                  style={{ overflowX: 'auto', fontSize: '0.82rem' }}
                >
                  <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 300 }}>
                    <thead>
                      <tr>
                        {result.columns.map(col => (
                          <th
                            key={col}
                            style={{
                              padding: '6px 10px',
                              textAlign: 'start',
                              borderBottom: '2px solid var(--border, #e2e8f0)',
                              fontWeight: 600,
                              color: 'var(--muted, #64748b)',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.rows.map((row, ri) => (
                        <tr
                          key={ri}
                          style={{
                            background: ri % 2 === 0 ? 'transparent' : 'var(--surface-alt, rgba(0,0,0,.03))',
                          }}
                        >
                          {row.map((cell, ci) => (
                            <td
                              key={ci}
                              style={{
                                padding: '5px 10px',
                                borderBottom: '1px solid var(--border, #f1f5f9)',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {cell === null || cell === undefined
                                ? '—'
                                : typeof cell === 'number'
                                  ? cell.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
                                  : String(cell)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}

          {/* No results */}
          {!result.error && result.rows.length === 0 && !loading && (
            <p style={{ color: 'var(--muted, #94a3b8)', fontSize: '0.85rem' }}>
              {t('geo_ai.no_results')}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
