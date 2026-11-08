import { useState } from 'react'
import type { Dict, Lang } from '../lib/i18n'
import { apiJson, isApiConfigured } from '../lib/api'
import {
  QUESTION_MAX, demoAnswer, demoQuestions, fmt, guardInjection, numberLocale, parseGeoAIResult,
  type GeoAIResult,
} from '../lib/geoai'

// P-035 — Page GeoAI dans mizanbi-client.
// Mode connecté : POST /api/v1/geo/ai-query (backend SovereignBI P-027).
// Mode démo (VITE_API_BASE vide) : réponses précalculées depuis data/demo.ts.
// Textes : t.geoai (fr/en/ar) ; la langue courante est aussi transmise au backend.

function ResultTable({ columns, rows, locale }: { columns: string[]; rows: (string | number | null)[][]; locale: string }) {
  if (!columns.length || !rows.length) return null
  return (
    <div className="table-wrap">
      <table className="data">
        <thead><tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j} dir="ltr">
                  {cell == null ? '—' : typeof cell === 'number' ? cell.toLocaleString(locale) : String(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function MapHint({ config, t }: { config: NonNullable<GeoAIResult['map_config']>; t: Dict['geoai'] }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10, background: 'oklch(26% 0.06 265 / .6)', fontSize: 13 }}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="oklch(68% 0.18 265)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M9 20l-5.5-2.5v-13L9 7l6-2.5L20.5 7v13L15 17.5 9 20zM9 7v13M15 4.5v13" />
      </svg>
      <span>
        {t.mapHintLayer.split('{layer}')[0]}<code style={{ fontSize: 12 }}>{config.layer_id}</code>{t.mapHintLayer.split('{layer}')[1]}
        {config.value_col && <>{t.mapHintColumn.split('{col}')[0]}<code style={{ fontSize: 12 }}>{config.value_col}</code></>}
      </span>
    </div>
  )
}

export default function GeoAIPage({ t, lang, go }: { t: Dict; lang: Lang; go: (p: string) => void }) {
  const g = t.geoai
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<GeoAIResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showReasoning, setShowReasoning] = useState(false)
  const demo = !isApiConfigured()

  const ask = async (q: string) => {
    const trimmed = q.trim()
    if (!trimmed) return
    if (trimmed.length > QUESTION_MAX) { setError(fmt(g.tooLong, { max: QUESTION_MAX })); return }
    if (guardInjection(trimmed)) { setError(g.notAllowed); return }
    setLoading(true); setError(null); setResult(null); setShowReasoning(false)
    try {
      if (demo) {
        await new Promise((r) => setTimeout(r, 400))
        setResult(demoAnswer(trimmed, lang))
      } else {
        const raw = await apiJson('/api/v1/geo/ai-query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: trimmed, locale: lang }),
        })
        const r = parseGeoAIResult(raw)
        if (r.error) setError(r.error)
        else setResult(r)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : g.networkError)
    } finally {
      setLoading(false)
    }
  }

  const submit = (e: React.FormEvent) => { e.preventDefault(); ask(question) }

  return (
    <div style={{ maxWidth: 820, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, letterSpacing: '-.02em' }}>{g.title}</h1>
        <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 13 }}>
          {g.subtitle} · {demo ? <span style={{ color: 'oklch(72% 0.18 55)' }}>{g.modeDemo}</span> : <span style={{ color: 'oklch(72% 0.17 155)' }}>{g.modeLive}</span>}
        </p>
      </div>

      {/* Quick examples */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {demoQuestions(lang).map((dq) => (
          <button key={dq.q} className="btn-ghost" style={{ fontSize: 12, padding: '4px 12px' }}
            onClick={() => { setQuestion(dq.q); ask(dq.q) }}>
            {dq.label}
          </button>
        ))}
      </div>

      {/* Input */}
      <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={QUESTION_MAX}
          placeholder={g.placeholder}
          disabled={loading}
          rows={3}
          style={{
            width: '100%', padding: '10px 14px', borderRadius: 10, resize: 'vertical', fontSize: 14,
            background: 'oklch(22% 0.04 265 / .8)', border: '1px solid var(--border)',
            color: 'var(--text)', fontFamily: 'inherit', boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 11, color: 'var(--muted)' }}>{question.length} / {QUESTION_MAX}</span>
          <button className="btn" type="submit" disabled={loading || !question.trim()}>
            {loading ? '…' : g.analyze}
          </button>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div style={{ padding: '10px 14px', borderRadius: 10, background: 'oklch(32% 0.1 25 / .5)', color: 'oklch(80% 0.14 25)', fontSize: 14 }}>
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Prose */}
          <div className="card-solid" style={{ lineHeight: 1.7, fontSize: 15 }}>
            {result.prose}
          </div>

          {/* Map hint */}
          {result.map_config && (
            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              <MapHint config={result.map_config} t={g} />
              <button className="btn-ghost" style={{ fontSize: 12, whiteSpace: 'nowrap' }} onClick={() => go('sig')}>
                {g.openMap}
              </button>
            </div>
          )}

          {/* Data table */}
          {result.columns.length > 0 && result.rows.length > 0 && (
            <div className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ fontSize: 13, fontWeight: 600 }}>
                {fmt(g.dataTitle, { n: result.rows.length })}
              </div>
              <ResultTable columns={result.columns} rows={result.rows} locale={numberLocale(lang)} />
            </div>
          )}

          {/* Reasoning (collapsible) */}
          {result.intent.reasoning && (
            <div>
              <button className="btn-ghost" style={{ fontSize: 12 }}
                onClick={() => setShowReasoning((v) => !v)}>
                {showReasoning ? '▲' : '▼'} {g.reasoning}
              </button>
              {showReasoning && (
                <div style={{ marginTop: 8, padding: '10px 14px', borderRadius: 10, background: 'oklch(22% 0.04 265 / .6)', fontSize: 13, color: 'var(--muted)', lineHeight: 1.6 }}>
                  <div><strong>{g.analysis}:</strong> {result.intent.analysis} · <strong>{g.layer}:</strong> {result.intent.layer_id}</div>
                  <div style={{ marginTop: 4 }}>{result.intent.reasoning}</div>
                </div>
              )}
            </div>
          )}

          {demo && (
            <p style={{ fontSize: 11, color: 'var(--muted)', margin: 0 }}>
              {g.demoNote}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
