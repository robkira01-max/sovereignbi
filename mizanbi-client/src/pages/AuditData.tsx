import { useCallback, useEffect, useState } from 'react'
import type { Lang } from '../lib/i18n'
import {
  IMPORT_DATE_FORMATS, NORMALIZED_FIELDS, REQUIRED_FIELDS, auditApi, canWrite, fileIssue, formatDecimal, justificationOk, uploadedId,
  type AuditDocument, type ImportBody, type ImportResult, type Issue, type NormalizedField, type Preview, type Suggestions,
} from '../lib/auditApi'
import { Empty, ErrorBox, Field, Hash, PageHead, RiskNotice, type AuditText } from '../components/audit/common'

// P-079 écran 1 — Données : dépôt, correspondance des colonnes, anomalies, résolution justifiée.
// L'interface masque les boutons selon le rôle ; le contrôle réel reste côté serveur (RequireRole).

export function DocumentsTable({ docs, selected, onSelect, a }: { docs: AuditDocument[]; selected: string | null; onSelect: (id: string) => void; a: AuditText }) {
  if (!docs.length) return <Empty text={a.data.noDocs} />
  return (
    <div className="table-wrap" style={{ maxHeight: 280 }}>
      <table className="data">
        <thead><tr><th>{a.data.file}</th><th>{a.data.status}</th><th>{a.data.rows}</th><th>{a.data.uploaded}</th></tr></thead>
        <tbody>
          {docs.map(d => (
            <tr key={d.document_id} aria-selected={selected === d.document_id} style={selected === d.document_id ? { outline: '2px solid var(--accent, #6366f1)' } : undefined}>
              <td><button className="btn-ghost" onClick={() => onSelect(d.document_id)}>{d.display_name ?? d.document_id.slice(0, 8)}</button></td>
              <td><span className={`badge ${d.status === 'imported' ? 'badge-ok' : 'badge-demo'}`}>{d.status === 'imported' ? a.data.statusImported : a.data.statusUploaded}</span></td>
              <td>{d.rows_imported ?? d.rows_total ?? '—'}</td>
              <td>{d.uploaded_at?.slice(0, 16).replace('T', ' ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function IssuesList({ issues, role, a, onResolve, busyId }: {
  issues: Issue[]; role: string; a: AuditText; onResolve?: (issue: Issue, justification: string) => void; busyId?: string | null
}) {
  const [open, setOpen] = useState<string | null>(null)
  const [text, setText] = useState('')
  if (!issues.length) return <Empty text={a.data.noIssues} />
  return (
    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
      {issues.map(i => {
        const blocking = i.severity === 'error'
        const mayResolve = i.status === 'open' && canWrite(role) && (!blocking || role === 'admin')
        return (
          <li key={i.issue_id} style={{ padding: '10px 12px', borderRadius: 10, background: 'oklch(22% 0.04 265 / .6)' }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              <span className={`badge ${blocking ? 'badge-off' : 'badge-demo'}`}>{blocking ? a.data.blocking : a.data.toReview}</span>
              <code>{i.code}</code>
              <span className="muted" style={{ fontSize: 12 }}>{i.source_row != null ? `${a.data.row} ${i.source_row}` : a.data.global}{i.field ? ` · ${i.field}` : ''}</span>
              {i.status === 'resolved' && <span className="badge badge-ok">{a.data.resolved}</span>}
            </div>
            <p style={{ margin: '6px 0 0', fontSize: 13 }}>{i.message}</p>
            {i.raw_value && <p className="muted" style={{ margin: '2px 0 0', fontSize: 12 }}>{a.data.rawValue} : <code>{i.raw_value}</code></p>}
            {i.status === 'resolved' && i.justification && <p className="muted" style={{ margin: '4px 0 0', fontSize: 12 }}>{a.data.justification} : {i.justification}</p>}
            {i.status === 'open' && blocking && !mayResolve && <p className="muted" style={{ margin: '4px 0 0', fontSize: 12 }}>{a.data.adminOnlyNote}</p>}
            {mayResolve && open !== i.issue_id && <button className="btn-ghost" style={{ marginTop: 6 }} onClick={() => { setOpen(i.issue_id); setText('') }}>{a.data.resolve}</button>}
            {mayResolve && open === i.issue_id && (
              <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
                {blocking && <p className="muted" style={{ margin: 0, fontSize: 12 }}>{a.data.separationNote}</p>}
                <Field label={a.data.justification} hint={`${text.trim().length} / ${a.data.minChars}`}>
                  <textarea rows={2} maxLength={500} value={text} onChange={e => setText(e.target.value)} />
                </Field>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn" disabled={!justificationOk(text) || busyId === i.issue_id} onClick={() => { onResolve?.(i, text.trim()); setOpen(null) }}>{a.data.confirmResolve}</button>
                  <button className="btn-ghost" onClick={() => setOpen(null)}>{a.cancel}</button>
                </div>
              </div>
            )}
          </li>
        )
      })}
    </ul>
  )
}

export function ImportSummaryView({ result, a, lang }: { result: ImportResult; a: AuditText; lang: Lang }) {
  const s = result.summary
  return (
    <div role="status" style={{ padding: 12, borderRadius: 10, border: '1px solid var(--border)', fontSize: 13 }}>
      <strong>{result.dry_run ? a.data.dryRunTitle : a.data.importDone}</strong>
      <ul style={{ margin: '6px 0 0', paddingInlineStart: 18 }}>
        <li>{a.data.rows} : {s.rows}</li>
        <li>{a.data.rowsWithErrors} : {s.rows_with_errors}</li>
        {s.totals && Object.keys(s.totals).length > 0 && <li>{Object.entries(s.totals).map(([k, v]) => `${k} ${formatDecimal(v, lang)}`).join(' · ')}</li>}
        {Object.entries(s.issue_counts).map(([k, n]) => <li key={k}><code>{k}</code> : {n}</li>)}
        {s.issues_truncated && <li>{a.data.truncated}</li>}
      </ul>
    </div>
  )
}

export default function AuditDataPage({ a, lang, role }: { a: AuditText; lang: Lang; role: string }) {
  const writer = canWrite(role)
  const [docs, setDocs] = useState<AuditDocument[] | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [sel, setSel] = useState<string | null>(null)
  const [doc, setDoc] = useState<AuditDocument | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [preview, setPreview] = useState<{ p: Preview; s: Suggestions } | null>(null)
  const [mapping, setMapping] = useState<Partial<Record<NormalizedField, string>>>({})
  const [decimal, setDecimal] = useState<'' | ',' | '.'>('')
  const [dateFmt, setDateFmt] = useState('')
  const [currency, setCurrency] = useState('')
  const [result, setResult] = useState<ImportResult | null>(null)
  const [issues, setIssues] = useState<Issue[]>([])
  const [filter, setFilter] = useState<'open' | 'resolved'>('open')
  const [integrity, setIntegrity] = useState<string | null>(null)
  const [duplicate, setDuplicate] = useState(false)

  const refresh = useCallback(() => auditApi.listDocuments().then(r => { setDocs(r.documents); setError(null) }).catch(setError), [])
  useEffect(() => { void refresh() }, [refresh])

  const loadDoc = useCallback(async (id: string) => {
    setSel(id); setDuplicate(false); setResult(null); setPreview(null); setIssues([]); setIntegrity(null); setError(null)
    try {
      const d = await auditApi.getDocument(id); setDoc(d)
      if (d.status === 'uploaded' && writer) {
        const pv = await auditApi.preview(id); setPreview({ p: pv.preview, s: pv.suggestions }); setMapping(pv.suggestions.mapping); setDecimal(''); setDateFmt(''); setCurrency('')
      } else if (d.status === 'imported' && writer) {
        setIssues((await auditApi.issues(id, filter)).issues)
      }
    } catch (e) { setError(e) }
  }, [writer, filter])

  const upload = async () => {
    if (!file || fileIssue(file) !== 'none') return
    setBusy(true)
    try { const r = await auditApi.upload(file); setFile(null); await refresh(); await loadDoc(uploadedId(r)); setDuplicate(r.duplicate) } catch (e) { setError(e) } finally { setBusy(false) }
  }

  const body = (dry: boolean): ImportBody | null => {
    if (!decimal || !dateFmt) return null
    const m = Object.fromEntries(Object.entries(mapping).filter(([, v]) => v)) as ImportBody['mapping']
    return { mapping: m, decimal_separator: decimal, date_format: dateFmt, default_currency: currency.trim().toUpperCase() || null, dry_run: dry }
  }
  const run = async (dry: boolean) => {
    const b = body(dry); if (!b || !sel) return
    setBusy(true); setError(null)
    try { const r = await auditApi.importDoc(sel, b); setResult(r); if (!dry) { await refresh(); await loadDoc(sel) } } catch (e) { setError(e) } finally { setBusy(false) }
  }
  const resolve = async (i: Issue, justification: string) => {
    setBusy(true)
    try { await auditApi.resolve(i.issue_id, justification); if (sel) { setIssues((await auditApi.issues(sel, filter)).issues); setDoc(await auditApi.getDocument(sel)) } } catch (e) { setError(e) } finally { setBusy(false) }
  }
  const switchFilter = async (f: 'open' | 'resolved') => { setFilter(f); if (sel) { try { setIssues((await auditApi.issues(sel, f)).issues) } catch (e) { setError(e) } } }
  const check = async () => { if (sel) { try { setIntegrity((await auditApi.integrity(sel)).status) } catch (e) { setError(e) } } }

  const headers = preview?.p.headers ?? []
  const missingRequired = REQUIRED_FIELDS.filter(f => !mapping[f])
  const needsAmount = !mapping.amount && !(mapping.debit || mapping.credit)
  const canSubmit = !!decimal && !!dateFmt && missingRequired.length === 0 && !needsAmount && (!!mapping.currency || /^[A-Za-z]{3}$/.test(currency.trim())) && !busy

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 1000 }}>
      <PageHead title={a.data.title} sub={a.data.sub} />
      <RiskNotice a={a} />
      {error != null && <ErrorBox error={error} a={a} />}

      {writer ? (
        <section className="card-solid" aria-label={a.data.uploadTitle}>
          <h3 style={{ marginTop: 0 }}>{a.data.uploadTitle}</h3>
          <input type="file" accept=".csv,.xlsx" aria-label={a.data.chooseFile} onChange={e => setFile(e.target.files?.[0] ?? null)} />
          <p className="muted" style={{ fontSize: 12 }}>{a.data.uploadHint}</p>
          {file && fileIssue(file) !== 'none' && <p role="alert" style={{ color: 'var(--warn, #fbbf24)', fontSize: 13 }}>{a.data.fileIssue[fileIssue(file) as 'type' | 'empty' | 'size']}</p>}
          <button className="btn" disabled={!file || fileIssue(file) !== 'none' || busy} onClick={upload}>{busy ? a.loading : a.data.upload}</button>
        </section>
      ) : <p className="muted">{a.readOnly}</p>}

      <section className="card-solid">
        <h3 style={{ marginTop: 0 }}>{a.data.docs}</h3>
        {docs === null && error == null ? <Empty text={a.loading} /> : <DocumentsTable docs={docs ?? []} selected={sel} onSelect={loadDoc} a={a} />}
      </section>

      {doc && (
        <section className="card-solid" aria-label={doc.display_name ?? ''}>
          <h3 style={{ marginTop: 0 }}>{doc.display_name}</h3>
          {duplicate && <p role="status" style={{ fontSize: 13 }}>ℹ️ {a.data.duplicate}</p>}
          <p className="muted" style={{ fontSize: 12 }}><Hash value={doc.sha256} label="SHA-256" /> · {doc.rows_total ?? '—'} {a.data.rows.toLowerCase()}</p>

          {doc.status === 'uploaded' && writer && preview && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <h4 style={{ margin: 0 }}>{a.data.mapTitle}</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
                {NORMALIZED_FIELDS.map(f => (
                  <Field key={f} label={`${a.data.fields[f]}${REQUIRED_FIELDS.includes(f) ? ' *' : ''}`}>
                    <select value={mapping[f] ?? ''} onChange={e => setMapping(m => ({ ...m, [f]: e.target.value || undefined }))}>
                      <option value="">{a.data.notMapped}</option>
                      {headers.map(h => <option key={h} value={h}>{h}</option>)}
                    </select>
                  </Field>
                ))}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
                <Field label={`${a.data.decimalSep} *`} hint={preview.s.decimal_separator ? `${a.data.suggested} : « ${preview.s.decimal_separator} »` : a.data.mustChoose}>
                  <select value={decimal} onChange={e => setDecimal(e.target.value as '' | ',' | '.')}>
                    <option value="">{a.data.choose}</option><option value=",">{a.data.comma}</option><option value=".">{a.data.dot}</option>
                  </select>
                </Field>
                <Field label={`${a.data.dateFormat} *`} hint={preview.s.date_formats.length ? `${a.data.suggested} : ${preview.s.date_formats.join(' / ')}` : a.data.mustChoose}>
                  <select value={dateFmt} onChange={e => setDateFmt(e.target.value)}>
                    <option value="">{a.data.choose}</option>{IMPORT_DATE_FORMATS.map(f => <option key={f} value={f}>{f}</option>)}
                  </select>
                </Field>
                <Field label={a.data.defaultCurrency} hint={mapping.currency ? undefined : a.data.currencyRequired}>
                  <input value={currency} maxLength={3} onChange={e => setCurrency(e.target.value)} placeholder="DJF" />
                </Field>
              </div>
              <div className="table-wrap" style={{ maxHeight: 220 }}>
                <table className="data"><thead><tr>{headers.map(h => <th key={h}>{h}</th>)}</tr></thead>
                  <tbody>{preview.p.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c ?? ''}</td>)}</tr>)}</tbody></table>
              </div>
              {(missingRequired.length > 0 || needsAmount) && <p className="muted" style={{ fontSize: 12 }}>{a.data.mappingIncomplete}</p>}
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button className="btn-ghost" disabled={!canSubmit} onClick={() => run(true)}>{a.data.dryRun}</button>
                <button className="btn" disabled={!canSubmit} onClick={() => run(false)}>{a.data.doImport}</button>
              </div>
              <p className="muted" style={{ fontSize: 12, margin: 0 }}>{a.data.noSilentFix}</p>
            </div>
          )}
          {result && <ImportSummaryView result={result} a={a} lang={lang} />}

          {doc.status === 'imported' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                <button className="btn-ghost" onClick={check}>{a.data.checkIntegrity}</button>
                {integrity && <span className={`badge ${integrity === 'ok' ? 'badge-ok' : 'badge-off'}`}>{a.data.integrity[integrity as 'ok' | 'mismatch' | 'missing']}</span>}
                {doc.issue_counts && <span className="muted" style={{ fontSize: 12 }}>{a.data.openErrors} : {doc.issue_counts.open_errors ?? 0} · {a.data.openWarnings} : {doc.issue_counts.open_warnings ?? 0}</span>}
              </div>
              {writer ? (
                <>
                  <div className="view-switch" role="tablist" aria-label={a.data.issues}>
                    <button className={filter === 'open' ? 'active' : ''} onClick={() => switchFilter('open')}>{a.data.open}</button>
                    <button className={filter === 'resolved' ? 'active' : ''} onClick={() => switchFilter('resolved')}>{a.data.resolved}</button>
                  </div>
                  <IssuesList issues={issues} role={role} a={a} onResolve={resolve} busyId={busy ? 'x' : null} />
                </>
              ) : <p className="muted">{a.data.issuesEditorOnly}</p>}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
