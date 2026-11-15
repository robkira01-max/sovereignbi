import { useRef, useState } from 'react'
import type { Dict } from '../lib/i18n'
import { isApiConfigured } from '../lib/api'
import { classifyError, fileIssue, sameRequest, sdmxImport, tableIssue, type SdmxImportResult } from '../lib/sdmxImport'

type T = Dict['sdmxImport']
const fill = (s: string, v: Record<string, string | number>) => s.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ''))

interface Props {
  t: T
  onLoaded?: (table: string) => void
}

/** Import SDMX-CSV en deux temps : « Vérifier » (dry_run, rien n'est chargé) puis « Charger » pour la même requête. */
export default function SdmxImport({ t, onLoaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [table, setTable] = useState('')
  const [replace, setReplace] = useState(false)
  const [checked, setChecked] = useState<{ req: { file: File | null; table: string; replace: boolean }; result: SdmxImportResult } | null>(null)
  const [busy, setBusy] = useState<'verify' | 'load' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const fIssue = fileIssue(file)
  const tIssue = tableIssue(table)
  const fileMsg = fIssue === 'type' ? t.errType : fIssue === 'size' ? t.errSize : fIssue === 'empty' ? t.errEmpty : null
  const ready = file !== null && fIssue === 'none' && tIssue === null
  // Le chargement n'est permis que pour la requête exactement vérifiée (fichier, table, remplacement inchangés).
  const confirmed = checked !== null && sameRequest(checked.req, { file, table, replace })

  const reset = () => { setChecked(null); setError(null); setNotice(null) }

  const run = async (dryRun: boolean) => {
    if (!file || !ready) return
    setBusy(dryRun ? 'verify' : 'load'); setError(null); setNotice(null)
    try {
      const result = await sdmxImport(file, { table, replace, dryRun })
      if (dryRun) {
        setChecked({ req: { file, table, replace }, result })
        setNotice(t.dryOk)
      } else {
        setChecked(null)
        setNotice(fill(t.loaded, { table: result.table, rows: result.rows }))
        onLoaded?.(result.table)
      }
    } catch (e) {
      const c = classifyError(e)
      setChecked(null)
      setError(c.kind === 'exists' ? t.errExists : c.kind === 'forbidden' ? t.errForbidden : c.kind === 'unauthorized' ? t.errUnauthorized
        : c.kind === 'server' ? (c.detail ?? t.errNetwork) : t.errNetwork)
    } finally {
      setBusy(null)
    }
  }

  const field = { display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13 } as const
  const bad = { color: 'oklch(78% 0.15 25)', fontSize: 12 } as const
  const r = checked?.result

  return (
    <section className="card" aria-labelledby="sdmx-import-title" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <h2 id="sdmx-import-title" style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>{t.title}</h2>
      <p className="muted" style={{ margin: 0 }}>{t.intro}</p>

      {!isApiConfigured() ? (
        <div className="muted" role="status">{t.demo}</div>
      ) : (
        <>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <button type="button" className="btn-ghost" onClick={() => inputRef.current?.click()} style={{ fontSize: 13 }}>{t.pick}</button>
            <span dir="ltr" className="muted">{file ? file.name : t.noFile}</span>
            <input ref={inputRef} type="file" accept=".csv,.txt,text/csv" style={{ display: 'none' }} data-testid="sdmx-file"
              onChange={(e) => { setFile(e.target.files?.[0] ?? null); reset() }} />
          </div>
          {fileMsg && <span role="alert" style={bad}>{fileMsg}</span>}

          <label style={field}>{t.tableLabel}
            <input className="input" value={table} dir="ltr" maxLength={61} placeholder="chomage" aria-invalid={tIssue !== null}
              onChange={(e) => { setTable(e.target.value); reset() }} />
            {tIssue ? <span role="alert" style={bad}>{t.errTable}</span> : <span className="muted" style={{ fontSize: 11 }}>{t.tableHint}</span>}
          </label>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13 }}>
            <input type="checkbox" checked={replace} onChange={(e) => { setReplace(e.target.checked); reset() }} />
            {t.replaceLabel}
          </label>

          {notice && <div role="status" className="badge badge-ok" style={{ alignSelf: 'flex-start', fontSize: 13 }}>{notice}</div>}
          {error && <div role="alert" className="badge badge-off" style={{ alignSelf: 'flex-start', fontSize: 13 }}>{error}</div>}

          {r && confirmed && (
            <div style={{ fontSize: 13, display: 'flex', flexDirection: 'column', gap: 2 }} data-testid="sdmx-summary">
              <div>{fill(t.summary, { id: r.structure_id, rows: r.rows, cols: r.columns.length, version: r.version })}</div>
              <div dir="ltr" style={{ textAlign: 'start' }}>{fill(t.target, { table: r.table })}</div>
              <div className="muted">{r.has_time_period ? t.timeYes : t.timeNo} · {r.columns.join(', ')}</div>
            </div>
          )}

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button type="button" className="btn-ghost" disabled={!ready || busy !== null} onClick={() => void run(true)}>
              {busy === 'verify' ? t.verifying : t.verify}
            </button>
            <button type="button" className="btn" disabled={!confirmed || busy !== null} onClick={() => void run(false)}>
              {busy === 'load' ? t.loading : t.load}
            </button>
          </div>
          <span className="muted" style={{ fontSize: 11 }}>{t.note}</span>
        </>
      )}
    </section>
  )
}
