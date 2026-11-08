import { useRef, useState } from 'react'
import type { Dict } from '../lib/i18n'
import { apiFetch, isApiConfigured } from '../lib/api'

export default function ImportPage({ t }: { t: Dict }) {
  const [dragging, setDragging] = useState(false)
  const [msg, setMsg] = useState('')
  const [ok, setOk] = useState(true)
  const [created, setCreated] = useState<string[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  const upload = async (f: File | undefined) => {
    if (!f) return
    setMsg(t.up)
    setOk(true)
    if (!isApiConfigured()) {
      // Mode démo : on simule la création de table à partir du nom du fichier.
      const table = f.name.replace(/\.(csv|xlsx|xls)$/i, '').toLowerCase().replace(/[^a-z0-9_]+/g, '_')
      setCreated((c) => [...new Set([...c, table])])
      setMsg(`✓ ${f.name} — ${t.demoBadge}`)
      setOk(true)
      return
    }
    try {
      const fd = new FormData()
      fd.append('file', f)
      const res = await apiFetch('/upload', { method: 'POST', body: fd })
      const j = (await res.json()) as { tables?: string[] }
      setCreated(j.tables || [])
      setMsg(`✓ ${f.name}`)
      setOk(true)
    } catch {
      setMsg(`${t.uploadFail} — ${f.name}`)
      setOk(false)
    }
  }

  return (
    <div style={{ maxWidth: 760, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, letterSpacing: '-.02em' }}>{t.import}</h1>
        <p style={{ margin: '4px 0 0', color: 'var(--muted)' }}>{t.importSub}</p>
      </div>
      <div
        className={`dropzone${dragging ? ' dragging' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); upload(e.dataTransfer.files[0]) }}
        role="button"
        tabIndex={0}
      >
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="oklch(75% 0.15 265)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" /></svg>
        <div style={{ fontWeight: 600, fontSize: 16 }}>{t.drop}</div>
        <div style={{ color: 'oklch(68% 0.03 265)' }}>CSV · XLSX</div>
        <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls" onChange={(e) => upload(e.target.files?.[0])} style={{ display: 'none' }} />
      </div>
      {msg && (
        <div style={{ padding: '12px 16px', borderRadius: 12, background: ok ? 'oklch(30% 0.09 155 / .5)' : 'oklch(32% 0.1 25 / .5)', color: ok ? 'oklch(85% 0.14 155)' : 'oklch(80% 0.14 25)' }}>
          {msg}
        </div>
      )}
      {created.length > 0 && (
        <section className="card" style={{ padding: 20 }}>
          <h2 style={{ margin: '0 0 12px', fontSize: 16, fontWeight: 600 }}>{t.created}</h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {created.map((c) => <span key={c} className="pill">{c}</span>)}
          </div>
        </section>
      )}
      <div className="muted">{t.demoBadge} — {t.loi25}</div>
    </div>
  )
}
