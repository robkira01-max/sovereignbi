import { useEffect, useState } from 'react'
import { useLocale } from '../hooks/useLocale'

interface LayerWarning {
  fr: string
  en: string
}

interface GeoLayer {
  id: string
  name_fr: string
  name_en: string
  description_fr: string
  description_en: string
  format: string
  geometry_type: string
  source: string
  license: string
  license_url: string
  date_acquired: string
  coverage: string
  feature_count: number
  status: 'validated' | 'draft' | 'deprecated'
  warnings: LayerWarning[]
  api_endpoint: string
  enabled: boolean
}

interface CatalogResponse {
  version: string
  count: number
  layers: GeoLayer[]
}

interface Props {
  apiKey: string
  isEditor?: boolean
}

const STATUS_COLORS: Record<string, string> = {
  validated:  '#059669',
  draft:      '#d97706',
  deprecated: '#6b7280',
}

export function GeoCatalog({ apiKey, isEditor = false }: Props) {
  const { t, locale } = useLocale()
  const [catalog, setCatalog]     = useState<CatalogResponse | null>(null)
  const [error, setError]         = useState<string | null>(null)
  const [loading, setLoading]     = useState(true)
  const [enabledOnly, setEnabledOnly] = useState(false)
  const [toggling, setToggling]   = useState<string | null>(null)

  const fetchCatalog = (eo = enabledOnly) => {
    setLoading(true)
    setError(null)
    const url = `/api/v1/geo/catalog${eo ? '?enabled_only=true' : ''}`
    fetch(url, { headers: { 'X-Api-Key': apiKey } })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<CatalogResponse>
      })
      .then(data => { setCatalog(data); setLoading(false) })
      .catch(e => { setError(String(e)); setLoading(false) })
  }

  useEffect(() => { fetchCatalog() }, [enabledOnly])  // eslint-disable-line react-hooks/exhaustive-deps

  const handleToggle = async (layerId: string) => {
    if (!isEditor || toggling) return
    setToggling(layerId)
    try {
      const r = await fetch(`/api/v1/geo/catalog/${layerId}/toggle`, {
        method: 'PUT',
        headers: { 'X-Api-Key': apiKey },
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      await fetchCatalog(enabledOnly)
    } catch (e) {
      setError(String(e))
    } finally {
      setToggling(null)
    }
  }

  const layerName = (l: GeoLayer) => locale === 'en' ? l.name_en : l.name_fr
  const layerDesc = (l: GeoLayer) => locale === 'en' ? l.description_en : l.description_fr
  const warnText  = (w: LayerWarning) => locale === 'en' ? w.en : w.fr

  if (loading) return <div data-testid="geo-catalog-loading" style={{ padding: 16, color: 'var(--muted)' }}>…</div>
  if (error)   return <div data-testid="geo-catalog-error"   style={{ padding: 16, color: '#ef4444' }}>{error}</div>
  if (!catalog) return null

  return (
    <div data-testid="geo-catalog" style={{ fontFamily: 'inherit' }}>
      {/* Header */}
      <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text)' }}>
            {t('geo_catalog.title')}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--muted)', marginTop: 2 }}>
            {t('geo_catalog.subtitle')} · v{catalog.version}
          </div>
        </div>
        <label
          data-testid="geo-catalog-enabled-toggle"
          style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', cursor: 'pointer', marginLeft: 'auto' }}
        >
          <input
            type="checkbox"
            checked={enabledOnly}
            onChange={e => setEnabledOnly(e.target.checked)}
            style={{ cursor: 'pointer' }}
          />
          {t('geo_catalog.enabled_only')}
        </label>
      </div>

      {catalog.layers.length === 0 && (
        <div style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>{t('geo_catalog.no_layers')}</div>
      )}

      {/* Layer cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {catalog.layers.map(layer => (
          <div
            key={layer.id}
            data-testid={`geo-layer-card-${layer.id}`}
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 10,
              padding: '14px 16px',
              opacity: layer.enabled ? 1 : 0.6,
            }}
          >
            {/* Title row */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, flexWrap: 'wrap' }}>
              <div style={{ flex: 1 }}>
                <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{layerName(layer)}</span>
                <span
                  data-testid={`geo-layer-status-${layer.id}`}
                  style={{
                    marginLeft: 8,
                    fontSize: '0.68rem',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    color: STATUS_COLORS[layer.status] ?? '#6b7280',
                    background: `${STATUS_COLORS[layer.status] ?? '#6b7280'}18`,
                    padding: '1px 6px',
                    borderRadius: 4,
                  }}
                >
                  {t(`geo_catalog.status_${layer.status}`)}
                </span>
              </div>

              {/* Enable/disable toggle — editor only */}
              {isEditor && (
                <button
                  data-testid={`geo-layer-toggle-${layer.id}`}
                  onClick={() => handleToggle(layer.id)}
                  disabled={toggling === layer.id}
                  style={{
                    fontSize: '0.75rem',
                    padding: '3px 10px',
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                    background: layer.enabled ? '#fee2e2' : '#d1fae5',
                    color: layer.enabled ? '#dc2626' : '#059669',
                    cursor: toggling === layer.id ? 'wait' : 'pointer',
                    fontWeight: 500,
                  }}
                >
                  {layer.enabled ? t('geo_catalog.toggle_disable') : t('geo_catalog.toggle_enable')}
                </button>
              )}

              {/* Enabled badge — viewer */}
              {!isEditor && (
                <span
                  data-testid={`geo-layer-enabled-badge-${layer.id}`}
                  style={{
                    fontSize: '0.68rem',
                    padding: '1px 7px',
                    borderRadius: 4,
                    background: layer.enabled ? '#d1fae518' : '#f3f4f618',
                    color: layer.enabled ? '#059669' : '#6b7280',
                    border: '1px solid currentColor',
                    fontWeight: 500,
                  }}
                >
                  {layer.enabled ? t('geo_catalog.enabled') : t('geo_catalog.disabled')}
                </span>
              )}
            </div>

            {/* Description */}
            <div style={{ fontSize: '0.8rem', color: 'var(--muted)', marginTop: 6 }}>
              {layerDesc(layer)}
            </div>

            {/* Metadata grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
              gap: '4px 16px',
              marginTop: 10,
              fontSize: '0.75rem',
            }}>
              <MetaItem label={t('geo_catalog.format')}         value={layer.format.toUpperCase()} />
              <MetaItem label={t('geo_catalog.source')}         value={layer.source} />
              <MetaItem label={t('geo_catalog.coverage')}       value={layer.coverage} />
              <MetaItem label={t('geo_catalog.feature_count')}  value={String(layer.feature_count)} />
              <MetaItem label={t('geo_catalog.date_acquired')}  value={layer.date_acquired} />
              <div style={{ gridColumn: 'span 2' }}>
                <span style={{ color: 'var(--muted)', fontWeight: 500 }}>{t('geo_catalog.license')}: </span>
                <a
                  href={layer.license_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: 'var(--brand)' }}
                >
                  {layer.license}
                </a>
              </div>
              <div style={{ gridColumn: 'span 2' }}>
                <span style={{ color: 'var(--muted)', fontWeight: 500 }}>{t('geo_catalog.api_endpoint')}: </span>
                <code style={{ fontSize: '0.72rem', background: 'var(--border)', padding: '1px 4px', borderRadius: 3 }}>
                  {layer.api_endpoint}
                </code>
              </div>
            </div>

            {/* Quality warnings */}
            {layer.warnings.length > 0 && (
              <div
                data-testid={`geo-layer-warning-${layer.id}`}
                style={{
                  marginTop: 10,
                  padding: '7px 10px',
                  background: '#fef3c718',
                  border: '1px solid #d97706',
                  borderRadius: 6,
                  fontSize: '0.76rem',
                  color: '#92400e',
                }}
              >
                <span style={{ fontWeight: 600 }}>⚠ {t('geo_catalog.warning_label')} : </span>
                {layer.warnings.map((w, i) => (
                  <span key={i}>{warnText(w)}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span style={{ color: 'var(--muted)', fontWeight: 500 }}>{label}: </span>
      <span>{value}</span>
    </div>
  )
}
