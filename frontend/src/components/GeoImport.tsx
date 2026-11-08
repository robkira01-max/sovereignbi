import { useRef, useState } from 'react'
import { useLocale } from '../hooks/useLocale'

interface ImportResult {
  id: string
  name_fr: string
  feature_count: number
  geometry_type: string
  status: string
}

interface Props {
  apiKey: string
  onImported?: (layer: ImportResult) => void
}

const ACCEPTED = '.geojson,.json,.gpkg,.parquet'
const MAX_MB = 50

export function GeoImport({ apiKey, onImported }: Props) {
  const { t } = useLocale()

  const [file, setFile] = useState<File | null>(null)
  const [nameFr, setNameFr] = useState('')
  const [nameEn, setNameEn] = useState('')
  const [descFr, setDescFr] = useState('')
  const [descEn, setDescEn] = useState('')
  const [source, setSource] = useState('Import utilisateur')
  const [license, setLicense] = useState('À vérifier')
  const [licenseUrl, setLicenseUrl] = useState('')
  const [coverage, setCoverage] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [dragging, setDragging] = useState(false)

  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = (f: File) => {
    setError(null)
    setResult(null)
    const ext = f.name.split('.').pop()?.toLowerCase() ?? ''
    if (!['geojson', 'json', 'gpkg', 'parquet'].includes(ext)) {
      setError(t('geo_import.error_type'))
      return
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(t('geo_import.error_size'))
      return
    }
    setFile(f)
    if (!nameFr) setNameFr(f.name.replace(/\.[^.]+$/, ''))
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f) handleFile(f)
  }

  const submit = async () => {
    if (!file) { setError(t('geo_import.no_file')); return }
    if (!nameFr.trim()) { setError(t('geo_import.field_name_fr') + ' requis'); return }

    setLoading(true)
    setError(null)
    setResult(null)

    const fd = new FormData()
    fd.append('file', file)
    fd.append('name_fr', nameFr)
    fd.append('name_en', nameEn)
    fd.append('description_fr', descFr)
    fd.append('description_en', descEn)
    fd.append('source', source)
    fd.append('license', license)
    fd.append('license_url', licenseUrl)
    fd.append('coverage', coverage)

    try {
      const res = await fetch('/api/v1/geo/import', {
        method: 'POST',
        headers: { 'X-Api-Key': apiKey },
        body: fd,
      })
      if (res.status === 400) {
        const j = await res.json()
        setError(j.detail ?? t('geo_import.error_invalid'))
      } else if (res.status === 413) {
        setError(t('geo_import.error_size'))
      } else if (!res.ok) {
        setError(t('geo_import.error_server'))
      } else {
        const j = await res.json()
        const layer: ImportResult = j.layer
        setResult(layer)
        setFile(null)
        setNameFr('')
        if (inputRef.current) inputRef.current.value = ''
        onImported?.(layer)
      }
    } catch {
      setError(t('geo_import.error_server'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div data-testid="geo-import" style={{ maxWidth: 600 }}>
      <h2 style={{ marginBottom: 4 }}>{t('geo_import.title')}</h2>
      <p style={{ color: '#666', marginBottom: 16, fontSize: 14 }}>{t('geo_import.subtitle')}</p>

      {/* Drop zone */}
      <div
        data-testid="geo-import-dropzone"
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragging ? '#1a4a8c' : '#ccc'}`,
          borderRadius: 8,
          padding: '24px 16px',
          textAlign: 'center',
          cursor: 'pointer',
          marginBottom: 16,
          background: dragging ? '#f0f4ff' : '#fafafa',
          transition: 'all 0.15s',
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          style={{ display: 'none' }}
          data-testid="geo-import-file-input"
          onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
        />
        {file ? (
          <span data-testid="geo-import-filename" style={{ fontWeight: 600 }}>
            {file.name}
          </span>
        ) : (
          <span style={{ color: '#888' }}>{t('geo_import.drop_or_click')}</span>
        )}
      </div>

      {/* Metadata fields */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
        <label style={{ gridColumn: '1 / 2' }}>
          <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>{t('geo_import.field_name_fr')} *</div>
          <input
            data-testid="geo-import-name-fr"
            value={nameFr}
            onChange={e => setNameFr(e.target.value)}
            style={{ width: '100%', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 4, boxSizing: 'border-box' }}
          />
        </label>
        <label style={{ gridColumn: '2 / 3' }}>
          <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>{t('geo_import.field_name_en')}</div>
          <input
            data-testid="geo-import-name-en"
            value={nameEn}
            onChange={e => setNameEn(e.target.value)}
            style={{ width: '100%', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 4, boxSizing: 'border-box' }}
          />
        </label>
        <label style={{ gridColumn: '1 / 3' }}>
          <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>{t('geo_import.field_desc_fr')}</div>
          <textarea
            data-testid="geo-import-desc-fr"
            value={descFr}
            onChange={e => setDescFr(e.target.value)}
            rows={2}
            style={{ width: '100%', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 4, resize: 'vertical', boxSizing: 'border-box' }}
          />
        </label>
        <label>
          <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>{t('geo_import.field_source')}</div>
          <input
            data-testid="geo-import-source"
            value={source}
            onChange={e => setSource(e.target.value)}
            style={{ width: '100%', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 4, boxSizing: 'border-box' }}
          />
        </label>
        <label>
          <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>{t('geo_import.field_license')}</div>
          <input
            data-testid="geo-import-license"
            value={license}
            onChange={e => setLicense(e.target.value)}
            style={{ width: '100%', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 4, boxSizing: 'border-box' }}
          />
        </label>
        <label style={{ gridColumn: '1 / 3' }}>
          <div style={{ fontSize: 12, color: '#555', marginBottom: 2 }}>{t('geo_import.field_coverage')}</div>
          <input
            data-testid="geo-import-coverage"
            value={coverage}
            onChange={e => setCoverage(e.target.value)}
            style={{ width: '100%', padding: '6px 8px', border: '1px solid #ccc', borderRadius: 4, boxSizing: 'border-box' }}
          />
        </label>
      </div>

      {error && (
        <div
          data-testid="geo-import-error"
          role="alert"
          style={{ background: '#fff0f0', border: '1px solid #f88', borderRadius: 4, padding: '8px 12px', marginBottom: 12, color: '#c00' }}
        >
          {error}
        </div>
      )}

      {result && (
        <div
          data-testid="geo-import-success"
          role="status"
          style={{ background: '#f0fff4', border: '1px solid #6c6', borderRadius: 4, padding: '10px 12px', marginBottom: 12 }}
        >
          <div style={{ fontWeight: 600, marginBottom: 4 }}>{t('geo_import.success')}</div>
          <div style={{ fontSize: 13, color: '#444' }}>
            {t('geo_import.success_id')} <code data-testid="geo-import-result-id">{result.id}</code>
          </div>
          <div style={{ fontSize: 13, color: '#444' }}>
            {t('geo_import.success_features')} <span data-testid="geo-import-result-features">{result.feature_count}</span>
          </div>
          <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>{t('geo_import.success_draft')}</div>
        </div>
      )}

      <button
        data-testid="geo-import-submit"
        onClick={submit}
        disabled={loading || !file}
        style={{
          padding: '8px 24px',
          background: loading || !file ? '#aaa' : '#1a4a8c',
          color: '#fff',
          border: 'none',
          borderRadius: 4,
          cursor: loading || !file ? 'default' : 'pointer',
          fontWeight: 600,
        }}
      >
        {loading ? t('geo_import.uploading') : t('geo_import.btn_upload')}
      </button>
    </div>
  )
}
