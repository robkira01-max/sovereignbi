import { useEffect, useState } from 'react'
import type { Lang } from '../lib/i18n'
import { auditApi, buildParams, canWrite, formatDecimal, unresolvedErrors, type AuditDocument, type Finding, type Rule, type RulesRun } from '../lib/auditApi'
import { Empty, ErrorBox, Field, Hash, PageHead, RiskNotice, type AuditText } from '../components/audit/common'

// P-079 écran 2 — Contrôles AUD001–AUD010. Libellé fixe : « signal de risque à examiner », jamais « fraude ».

export function FindingsTable({ findings, a, lang }: { findings: Finding[]; a: AuditText; lang: Lang }) {
  if (!findings.length) return <Empty text={a.rules.noFindings} />
  return (
    <div className="table-wrap" style={{ maxHeight: 360 }}>
      <table className="data">
        <thead><tr><th>{a.rules.rule}</th><th>{a.rules.finding}</th><th>{a.rules.amount}</th><th>{a.rules.rowsCol}</th></tr></thead>
        <tbody>
          {findings.map(f => (
            <tr key={f.finding_id}>
              <td><code>{f.rule_code}</code>{f.indicative && <span className="badge badge-demo" style={{ marginInlineStart: 6 }}>{a.rules.indicative}</span>}</td>
              <td>{f.summary}<br /><span className="badge badge-demo">{a.rules.signal}</span></td>
              <td>{formatDecimal(f.amount, lang)}</td>
              <td>{f.source_rows.slice(0, 8).join(', ')}{f.source_rows.length > 8 ? '…' : ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function RunSummaryView({ run, rules, docSha, a }: { run: RulesRun; rules: Rule[]; docSha?: string; a: AuditText }) {
  const ver = (code: string) => rules.find(r => r.code === code)?.version
  return (
    <div role="status" style={{ padding: 12, borderRadius: 10, border: '1px solid var(--border)', fontSize: 13, display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <span>{a.rules.runId} : <code>{run.run_id}</code></span>
        <Hash value={run.summary.ruleset_hash} label={a.rules.rulesetHash} />
        <Hash value={docSha} label={a.rules.dataHash} />
      </div>
      {run.summary.rows_excluded_for_errors > 0 && <p style={{ margin: 0 }}>⚠️ {a.rules.excluded.replace('{n}', String(run.summary.rows_excluded_for_errors))}</p>}
      <ul style={{ margin: 0, paddingInlineStart: 18 }}>
        {run.summary.rules.map(o => (
          <li key={o.code}>
            <code>{o.code}</code> v{o.version ?? ver(o.code)} — {o.status === 'ran' ? `${o.findings} ${a.rules.findingsCount}` : (a.rules.status[o.status as 'not_applicable' | 'error'] ?? o.status)}
            {o.reason ? <span className="muted"> ({o.reason})</span> : null}{o.truncated ? <span className="muted"> — {a.rules.truncated}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function AuditRulesPage({ a, lang, role }: { a: AuditText; lang: Lang; role: string }) {
  const writer = canWrite(role)
  const [docs, setDocs] = useState<AuditDocument[]>([])
  const [rules, setRules] = useState<Rule[] | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [docId, setDocId] = useState('')
  const [doc, setDoc] = useState<AuditDocument | null>(null)
  const [picked, setPicked] = useState<Set<string>>(new Set())
  const [raw, setRaw] = useState<Record<string, Record<string, string>>>({})
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [run, setRun] = useState<RulesRun | null>(null)
  const [findings, setFindings] = useState<Finding[]>([])
  const [only, setOnly] = useState('')

  useEffect(() => {
    auditApi.rules().then(r => { setRules(r.rules); setPicked(new Set(r.rules.map(x => x.code))) }).catch(setError)
    auditApi.listDocuments().then(r => setDocs(r.documents.filter(d => d.status === 'imported'))).catch(setError)
  }, [])

  const pickDoc = async (id: string) => { setDocId(id); setRun(null); setFindings([]); setDoc(null); if (id) { try { setDoc(await auditApi.getDocument(id)) } catch (e) { setError(e) } } }
  const toggle = (c: string) => setPicked(s => { const n = new Set(s); n.has(c) ? n.delete(c) : n.add(c); return n })
  const setParam = (code: string, name: string, v: string) => setRaw(r => ({ ...r, [code]: { ...(r[code] ?? {}), [name]: v } }))

  const launch = async () => {
    if (!rules || !docId) return
    const params: Record<string, Record<string, unknown>> = {}
    const errs: Record<string, string> = {}
    for (const r of rules.filter(x => picked.has(x.code))) {
      const b = buildParams(r, raw[r.code] ?? {})
      if (r.params.length) params[r.code] = b.params
      for (const [k, v] of Object.entries(b.errors)) errs[`${r.code}.${k}`] = v
    }
    setFieldErrors(errs)
    if (Object.keys(errs).length) return
    setBusy(true); setError(null)
    try {
      const res = await auditApi.runRules(docId, [...picked], params)
      setRun(res); setOnly(''); setFindings((await auditApi.findings(res.run_id)).findings)
    } catch (e) { setError(e) } finally { setBusy(false) }
  }
  const filter = async (code: string) => { setOnly(code); if (run) { try { setFindings((await auditApi.findings(run.run_id, code || undefined)).findings) } catch (e) { setError(e) } } }

  const openErrors = unresolvedErrors(doc?.issue_counts)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 1000 }}>
      <PageHead title={a.rules.title} sub={a.rules.sub} />
      <RiskNotice a={a} />
      {error != null && <ErrorBox error={error} a={a} />}

      <section className="card-solid">
        <Field label={a.rules.document}>
          <select value={docId} onChange={e => pickDoc(e.target.value)} aria-label={a.rules.document}>
            <option value="">{a.data.choose}</option>
            {docs.map(d => <option key={d.document_id} value={d.document_id}>{d.display_name ?? d.document_id.slice(0, 8)}</option>)}
          </select>
        </Field>
        {!docs.length && <Empty text={a.rules.noImported} />}
        {openErrors > 0 && <p role="note" style={{ fontSize: 13 }}>⚠️ {a.rules.openErrorsWarn.replace('{n}', String(openErrors))}</p>}
      </section>

      <section className="card-solid">
        <h3 style={{ marginTop: 0 }}>{a.rules.chooseRules}</h3>
        {rules === null && error == null ? <Empty text={a.loading} /> : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
            {(rules ?? []).map(r => (
              <li key={r.code} style={{ padding: '8px 10px', borderRadius: 10, background: 'oklch(22% 0.04 265 / .6)' }}>
                <label style={{ display: 'flex', gap: 8, alignItems: 'baseline', cursor: 'pointer' }}>
                  <input type="checkbox" checked={picked.has(r.code)} onChange={() => toggle(r.code)} />
                  <span><code>{r.code}</code> v{r.version} — <strong>{r.title}</strong>{r.indicative && <span className="badge badge-demo" style={{ marginInlineStart: 6 }}>{a.rules.indicative}</span>}</span>
                </label>
                <p className="muted" style={{ margin: '4px 0 0', fontSize: 12 }}>{r.description}</p>
                {picked.has(r.code) && r.params.length > 0 && (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 8, marginTop: 6 }}>
                    {r.params.map(p => (
                      <Field key={p.name} label={`${p.name}${p.required && p.default == null ? ' *' : ''}`}
                        hint={fieldErrors[`${r.code}.${p.name}`] ? a.rules.paramErr[fieldErrors[`${r.code}.${p.name}`] as 'required'] ?? a.rules.paramErr.required : (p.type === 'budgets' ? a.rules.budgetsHint : p.default != null ? `${a.rules.defaultIs} ${JSON.stringify(p.default)}` : p.type)}>
                        {p.type === 'budgets'
                          ? <textarea rows={3} value={raw[r.code]?.[p.name] ?? ''} onChange={e => setParam(r.code, p.name, e.target.value)} placeholder="601;DJF;1500000" />
                          : <input value={raw[r.code]?.[p.name] ?? ''} onChange={e => setParam(r.code, p.name, e.target.value)} />}
                      </Field>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
        {writer
          ? <button className="btn" style={{ marginTop: 12 }} disabled={!docId || picked.size === 0 || busy} onClick={launch}>{busy ? a.loading : a.rules.launch}</button>
          : <p className="muted">{a.readOnly}</p>}
      </section>

      {run && (
        <section className="card-solid">
          <h3 style={{ marginTop: 0 }}>{a.rules.results}</h3>
          <RunSummaryView run={run} rules={rules ?? []} docSha={doc?.sha256} a={a} />
          <div style={{ margin: '12px 0 8px' }}>
            <Field label={a.rules.filterRule}>
              <select value={only} onChange={e => filter(e.target.value)}>
                <option value="">{a.rules.allRules}</option>
                {run.summary.rules.filter(o => o.findings > 0).map(o => <option key={o.code} value={o.code}>{o.code} ({o.findings})</option>)}
              </select>
            </Field>
          </div>
          <FindingsTable findings={findings} a={a} lang={lang} />
        </section>
      )}
    </div>
  )
}
