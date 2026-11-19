import { useEffect, useState } from 'react'
import type { Lang } from '../lib/i18n'
import { auditApi, canWrite, formatDecimal, type Comparison, type FinRun, type Formula } from '../lib/auditApi'
import { Empty, ErrorBox, Field, Hash, PageHead, type AuditText } from '../components/audit/common'

// P-079 écran 3 — Formules : définition, calcul reproductible, comparaison. Aucun calcul dans React :
// les valeurs sont des chaînes décimales fournies par l'API, mises en forme sans conversion numérique.

const DEC = /^-?\d+([.,]\d+)?$/

export function FormulaDetail({ f, a }: { f: Formula; a: AuditText }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13 }}>
      <p style={{ margin: 0 }}>{f.description}</p>
      <p style={{ margin: 0 }}><strong>{a.fin.expression} :</strong> <code>{f.expression}</code></p>
      <ul style={{ margin: 0, paddingInlineStart: 18 }}>
        <li>{a.fin.version} : {f.version} · {a.fin.unit} : {f.result_unit || '—'}</li>
        <li>{a.fin.rounding} : {f.rounding} ({f.precision})</li>
        <li>{a.fin.zeroDiv} : {f.on_zero_division}</li>
        {f.variables.map(v => <li key={v.name}><code>{v.name}</code> — {v.label}{v.unit ? ` (${v.unit})` : ''}{v.required ? ' *' : ''}{v.default != null ? ` · ${a.fin.defaultMissing} ${v.default}` : ''}</li>)}
      </ul>
      {f.interpretation && <p className="muted" style={{ margin: 0 }}>{f.interpretation}</p>}
    </div>
  )
}

export function ResultCard({ run, a, lang }: { run: FinRun; a: AuditText; lang: Lang }) {
  const r = run.result
  const ok = r?.status === 'ok'
  return (
    <div role="status" style={{ padding: 14, borderRadius: 12, border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'baseline', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 28, fontWeight: 700 }}>{r?.value != null ? `${formatDecimal(r.value, lang, true)}${r.unit ? ` ${r.unit}` : ''}` : '—'}</span>
        <span className={`badge ${ok ? 'badge-ok' : 'badge-off'}`}>{ok ? a.fin.computed : (r?.status === 'undefined' ? a.fin.undefinedResult : (r?.status ?? '—'))}</span>
        {run.integrity && <span className={`badge ${run.integrity === 'ok' ? 'badge-ok' : 'badge-off'}`}>{run.integrity === 'ok' ? a.fin.integrityOk : a.fin.integrityBad}</span>}
        {run.definition_status && run.definition_status !== 'unchanged' && <span className="badge badge-off">{a.fin.defChanged}</span>}
      </div>
      {r?.message && <p className="muted" style={{ margin: 0 }}>{r.message}</p>}
      <p className="muted" style={{ margin: 0, fontSize: 12, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <span>{a.fin.engine} {run.engine_version}</span><Hash value={run.input_snapshot_hash} label={a.fin.dataHash} /><Hash value={run.result_hash} label={a.fin.resultHash} /><span>#{run.run_id.slice(0, 8)}</span>
      </p>
    </div>
  )
}

export function ComparisonView({ c, a, lang }: { c: Comparison; a: AuditText; lang: Lang }) {
  return (
    <div role="status" style={{ padding: 12, borderRadius: 10, border: '1px solid var(--border)', fontSize: 13 }}>
      <strong>{c.same_result_hash && c.same_inputs ? a.fin.identical : a.fin.different}</strong>
      <ul style={{ margin: '6px 0 0', paddingInlineStart: 18 }}>
        <li>{a.fin.sameFormula} : {c.same_formula_and_version ? a.yes : a.no}</li>
        <li>{a.fin.sameInputs} : {c.same_inputs ? a.yes : a.no}</li>
        <li>{a.fin.sameResult} : {c.same_result_hash ? a.yes : a.no}</li>
        <li>{formatDecimal(c.value_a, lang, true)} → {formatDecimal(c.value_b, lang, true)}{c.delta_b_minus_a != null ? ` (Δ ${formatDecimal(c.delta_b_minus_a, lang, true)})` : ''}</li>
        {Object.entries(c.input_differences).map(([k, d]) => <li key={k}><code>{k}</code> : {d.a ?? '—'} → {d.b ?? '—'}</li>)}
      </ul>
    </div>
  )
}

export default function FinancialPage({ a, lang, role }: { a: AuditText; lang: Lang; role: string }) {
  const writer = canWrite(role)
  const [formulas, setFormulas] = useState<Formula[] | null>(null)
  const [engine, setEngine] = useState('')
  const [code, setCode] = useState('')
  const [inputs, setInputs] = useState<Record<string, string>>({})
  const [run, setRun] = useState<FinRun | null>(null)
  const [history, setHistory] = useState<FinRun[]>([])
  const [pair, setPair] = useState<string[]>([])
  const [cmp, setCmp] = useState<Comparison | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => { auditApi.formulas().then(r => { setFormulas(r.formulas); setEngine(r.engine_version) }).catch(setError) }, [])
  const f = formulas?.find(x => x.code === code) ?? null
  const loadHistory = async (c: string) => { try { setHistory((await auditApi.finRuns(c)).runs) } catch (e) { setError(e) } }
  const pick = (c: string) => { setCode(c); setInputs({}); setRun(null); setCmp(null); setPair([]); setHistory([]); if (c) void loadHistory(c) }

  const missing = f ? f.variables.filter(v => v.required && v.default == null && !(inputs[v.name] ?? '').trim()) : []
  const invalid = f ? f.variables.filter(v => (inputs[v.name] ?? '').trim() && !DEC.test(inputs[v.name].trim())) : []
  const norm = () => Object.fromEntries(Object.entries(inputs).filter(([, v]) => v.trim()).map(([k, v]) => [k, v.trim().replace(',', '.')]))

  const calc = async () => {
    if (!f) return
    setBusy(true); setError(null); setCmp(null)
    try { const r = await auditApi.runFormula(f.code, f.version, norm()); setRun(r); await loadHistory(f.code) } catch (e) { setError(e) } finally { setBusy(false) }
  }
  const reproduce = async () => {
    if (!run) return
    setBusy(true); setError(null)
    try {
      const again = await auditApi.runFormula(run.formula_code, run.formula_version, run.inputs ?? {})
      setCmp(await auditApi.compare(run.run_id, again.run_id)); await loadHistory(run.formula_code)
    } catch (e) { setError(e) } finally { setBusy(false) }
  }
  const compare = async () => { if (pair.length === 2) { try { setCmp(await auditApi.compare(pair[0], pair[1])) } catch (e) { setError(e) } } }
  const togglePair = (id: string) => setPair(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id].slice(-2))
  const explicitOnly = !!run && Object.values(run.sources ?? {}).every(s => s.explicit !== false)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 1000 }}>
      <PageHead title={a.fin.title} sub={a.fin.sub} />
      {error != null && <ErrorBox error={error} a={a} />}
      <section className="card-solid">
        <Field label={a.fin.formula} hint={engine ? `${a.fin.engine} ${engine}` : undefined}>
          <select value={code} onChange={e => pick(e.target.value)} aria-label={a.fin.formula}>
            <option value="">{a.data.choose}</option>
            {(formulas ?? []).map(x => <option key={x.code} value={x.code}>{x.code} — {x.label}</option>)}
          </select>
        </Field>
        {formulas === null && error == null && <Empty text={a.loading} />}
        {formulas?.length === 0 && <Empty text={a.fin.noFormulas} />}
      </section>

      {f && (
        <section className="card-solid">
          <FormulaDetail f={f} a={a} />
          <h4>{a.fin.inputs}</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10 }}>
            {f.variables.map(v => (
              <Field key={v.name} label={`${v.label}${v.required ? ' *' : ''}`} hint={invalid.includes(v) ? a.fin.notDecimal : v.unit || undefined}>
                <input inputMode="decimal" value={inputs[v.name] ?? ''} onChange={e => setInputs(s => ({ ...s, [v.name]: e.target.value }))} />
              </Field>
            ))}
          </div>
          {writer
            ? <button className="btn" style={{ marginTop: 12 }} disabled={busy || missing.length > 0 || invalid.length > 0} onClick={calc}>{busy ? a.loading : a.fin.compute}</button>
            : <p className="muted">{a.readOnly}</p>}
        </section>
      )}

      {run && (
        <section className="card-solid">
          <ResultCard run={run} a={a} lang={lang} />
          {writer && <div style={{ marginTop: 10 }}>
            <button className="btn-ghost" disabled={busy || !explicitOnly} onClick={reproduce}>{a.fin.reproduce}</button>
            {!explicitOnly && <span className="muted" style={{ fontSize: 12, marginInlineStart: 8 }}>{a.fin.reproduceTableNote}</span>}
          </div>}
        </section>
      )}

      {f && (
        <section className="card-solid">
          <h3 style={{ marginTop: 0 }}>{a.fin.history}</h3>
          {history.length === 0 ? <Empty text={a.fin.noRuns} /> : (
            <div className="table-wrap" style={{ maxHeight: 260 }}>
              <table className="data">
                <thead><tr><th></th><th>{a.fin.when}</th><th>v</th><th>{a.fin.result}</th><th>{a.fin.by}</th></tr></thead>
                <tbody>
                  {history.map(h => (
                    <tr key={h.run_id}>
                      <td><input type="checkbox" aria-label={`${a.fin.select} ${h.run_id.slice(0, 8)}`} checked={pair.includes(h.run_id)} onChange={() => togglePair(h.run_id)} /></td>
                      <td>{h.created_at?.slice(0, 16).replace('T', ' ')}</td><td>{h.formula_version}</td>
                      <td><Hash value={h.result_hash} label="" /></td><td>{h.created_by}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <button className="btn-ghost" style={{ marginTop: 8 }} disabled={pair.length !== 2} onClick={compare}>{a.fin.compare}</button>
        </section>
      )}
      {cmp && <ComparisonView c={cmp} a={a} lang={lang} />}
    </div>
  )
}
