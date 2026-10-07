import { useRef, useState } from 'react'
import { api } from '../api/client'

export function UploadPage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [tables, setTables] = useState<string[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [dragOver, setDragOver] = useState(false)

  const handleFile = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!['csv', 'xlsx', 'xlsm'].includes(ext ?? '')) {
      setError('Format accepté : CSV, XLSX, XLSM')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await api.upload(file)
      setTables(res.tables)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur upload')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: '600px', margin: '32px auto', padding: '0 16px' }}>
      <h2>Importer des données</h2>
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
        {loading ? 'Chargement…' : 'Glissez un fichier CSV / XLSX ou cliquez pour sélectionner'}
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
          <strong>Tables chargées :</strong>
          <ul>{tables.map(t => <li key={t}>{t}</li>)}</ul>
        </div>
      )}
    </div>
  )
}
