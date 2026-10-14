import { useRef, useState } from 'react'
import { api } from '../api/client'
import { useLocale } from '../hooks/useLocale'

export function UploadPage() {
  const { t } = useLocale()
  const inputRef = useRef<HTMLInputElement>(null)
  const [tables, setTables] = useState<string[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [dragOver, setDragOver] = useState(false)

  const handleFile = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!['csv', 'xlsx', 'xlsm'].includes(ext ?? '')) {
      setError(t('upload.format_error'))
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await api.upload(file)
      setTables(res.tables)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('upload.error_upload'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: '600px', margin: '32px auto', padding: '0 16px' }}>
      <h2>{t('upload.title')}</h2>
      <div
        data-testid="drop-zone"
        onDragOver={e => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f) }}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? '#2563eb' : '#d1d5db'}`,
          borderRadius: '8px',
          padding: '40px',
          textAlign: 'center',
          cursor: 'pointer',
          background: dragOver ? '#eff6ff' : '#fafafa',
          marginBottom: '16px',
        }}
      >
        {loading ? t('upload.loading') : t('upload.drop_hint')}
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xlsm"
          style={{ display: 'none' }}
          onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
        />
      </div>

      {error && <p style={{ color: '#dc2626' }}>{error}</p>}

      {tables.length > 0 && (
        <div>
          <strong>{t('upload.tables_loaded')}</strong>
          <ul>{tables.map(tb => <li key={tb}>{tb}</li>)}</ul>
        </div>
      )}
    </div>
  )
}
