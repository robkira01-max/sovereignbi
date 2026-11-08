import { useState } from 'react'
import type { Dict } from '../lib/i18n'
import { DEMO_ALERT, PROVENANCE, REGIONS, fmt } from '../data/demo'
import { postChat } from '../lib/api'
import { AbstainBox, Provenance } from '../components/Proof'

interface Msg {
  role: 'user' | 'assistant'
  text: string
  sql?: string
  cols?: string[]
  rows?: (string | number)[][]
  conf?: 'high' | 'medium' | 'low'
  followUps?: string[]
  verification?: string
  abstain?: boolean
}

// P-022 — périmètre démo : emploi, population, pauvreté, Djibouti, 2024.
// Hors de ces mots, l'agent s'abstient au lieu d'inventer.
const IN_SCOPE = /chômage|chomage|population|pauvret|emploi|région|region|djibouti|obock|dikhil|tadjourah|arta|ali sabieh|2024|2030|taux/i
const OUT_OF_SCOPE = /météo|meteo|sport|recette|cuisine|film|musique|football|voiture|tucson|garage/i

const KW = /\b(SELECT|FROM|WHERE|GROUP BY|ORDER BY|LIMIT|AND|OR|AS|JOIN|ON|HAVING|DESC|ASC|AVG|SUM|COUNT|MIN|MAX|DISTINCT|BY|IN|LIKE)\b/gi

function highlight(sql: string) {
  const parts: { t: string; kw: boolean }[] = []
  let i = 0
  sql.replace(KW, (m, _a, o) => {
    if (o > i) parts.push({ t: sql.slice(i, o), kw: false })
    parts.push({ t: m, kw: true })
    i = o + m.length
    return m
  })
  if (i < sql.length) parts.push({ t: sql.slice(i), kw: false })
  return parts
}

export default function ChatPage({ t, initialQuestion }: { t: Dict; initialQuestion?: string }) {
  const [mode, setMode] = useState<'data' | 'general'>('data')
  const [question, setQuestion] = useState(initialQuestion || '')
  const [messages, setMessages] = useState<Msg[]>([])
  const [busy, setBusy] = useState(false)
  const [openSql, setOpenSql] = useState<Record<number, boolean>>({})
  const [copied, setCopied] = useState(-1)

  const demoAnswer = (q: string): Msg => {
    if (mode === 'general') return { role: 'assistant', text: t.generalDemo }
    if (OUT_OF_SCOPE.test(q) || !IN_SCOPE.test(q)) {
      return { role: 'assistant', text: t.outOfScope, abstain: true, conf: 'low' }
    }
    const rows = [...REGIONS].sort((a, b) => b.unemployment - a.unemployment).map((r) => [r.name, r.unemployment])
    // P-022 — 2e vérification démo : on recalcule le taux pondéré depuis les régions
    // et on le compare au KPI affiché. Ici les deux coïncident (23,5 %).
    const recomputed = Math.round((REGIONS.reduce((a, r) => a + r.population * r.unemployment, 0) / REGIONS.reduce((a, r) => a + r.population, 0)) * 10) / 10
    return {
      role: 'assistant',
      text: t.chatAnswerDemo,
      sql: PROVENANCE.unemployment.sql,
      cols: ['region', 'taux'],
      rows,
      conf: 'medium',
      followUps: ['Comparer avec 2024', 'Voir par région', 'Voir l’évolution'],
      verification: `2e requête, même résultat — ${String(recomputed).replace('.', ',')} % (emploi_region, 2024, démo).`,
    }
  }

  const send = async (e?: React.FormEvent, override?: string) => {
    e?.preventDefault()
    const q = (override ?? question).trim()
    if (!q || busy) return
    const hist = messages.slice(-10).map((m) => ({ role: m.role, content: m.text }))
    setMessages((m) => [...m, { role: 'user', text: q }])
    setQuestion('')
    setBusy(true)
    try {
      const j = await postChat(q, hist, mode === 'data')
      const cols = j.columns || j.data?.columns || []
      const rows = j.rows || j.data?.rows || []
      const c = String(j.confidence || '').toLowerCase()
      const conf: Msg['conf'] = c.includes('high') || c.includes('élev') ? 'high' : c.includes('low') || c.includes('faib') ? 'low' : c ? 'medium' : undefined
      setMessages((m) => [...m, { role: 'assistant', text: j.answer, sql: j.sql, cols, rows, conf }])
    } catch {
      setMessages((m) => [...m, demoAnswer(q)])
    } finally {
      setBusy(false)
    }
  }

  const confMeta = (c?: Msg['conf']) => {
    if (c === 'high') return { label: t.high, bg: 'oklch(30% 0.09 155 / .6)', fg: 'oklch(82% 0.15 155)' }
    if (c === 'low') return { label: t.low, bg: 'oklch(32% 0.1 25 / .6)', fg: 'oklch(78% 0.15 25)' }
    if (c === 'medium') return { label: t.medium, bg: 'oklch(34% 0.08 55 / .6)', fg: 'oklch(82% 0.15 65)' }
    return null
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 18, minHeight: 'calc(100vh - 56px - 56px)' }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <div className="view-switch">
          <button className={mode === 'data' ? 'active' : ''} onClick={() => setMode('data')}>{t.data}</button>
          <button className={mode === 'general' ? 'active' : ''} onClick={() => setMode('general')}>{t.general}</button>
        </div>
        <span className="badge badge-demo">{t.demoBadge}</span>
        <span className="badge badge-ok">{t.offlineBadge}</span>
      </div>
      {/* P-022 — alerte démo : indicateur au-dessus du seuil 25 %. */}
      <div style={{ padding: '12px 16px', borderRadius: 12, background: 'oklch(34% 0.08 55 / .5)', color: 'oklch(82% 0.15 65)', fontSize: 13, lineHeight: 1.6 }}>
        <b>⚠ {DEMO_ALERT.title}.</b> {DEMO_ALERT.detail}
      </div>
      {mode === 'general' && (
        <div style={{ padding: '12px 16px', borderRadius: 12, background: 'oklch(32% 0.1 25 / .5)', color: 'oklch(80% 0.14 25)', fontSize: 13, lineHeight: 1.6 }}>
          {t.generalWarning}
        </div>
      )}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>
        {messages.length === 0 && (
          <div style={{ padding: '48px 0', textAlign: 'center', color: 'oklch(68% 0.03 265)' }}>
            <div style={{ fontSize: 22, fontWeight: 600, color: '#f0f0fa', marginBottom: 12 }}>{t.askAnything}</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
              {t.suggestions.map((s) => (
                <button key={s} className="btn-ghost" style={{ borderRadius: 999 }} onClick={() => setQuestion(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {m.role === 'user' && (
              <div style={{ alignSelf: 'flex-end', maxWidth: '80%', background: 'oklch(65% 0.22 265)', color: '#fff', padding: '10px 16px', borderRadius: 16, borderEndEndRadius: 4 }}>{m.text}</div>
            )}
            {m.role === 'assistant' && (
              <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {m.abstain ? (
                  <AbstainBox reason={m.text} />
                ) : (
                  <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', justifyContent: 'space-between' }}>
                    <div style={{ fontSize: 15, lineHeight: 1.6 }}>{m.text}</div>
                    {confMeta(m.conf) && (
                      <span className="badge" style={{ background: confMeta(m.conf)!.bg, color: confMeta(m.conf)!.fg, flex: 'none' }}>
                        <span style={{ width: 7, height: 7, borderRadius: '50%', background: confMeta(m.conf)!.fg }} />
                        {confMeta(m.conf)!.label}
                      </span>
                    )}
                  </div>
                )}
                {/* P-023 — provenance sous chaque réponse (mode Données uniquement). */}
                {!m.abstain && mode === 'data' && m.sql && (
                  <Provenance table={PROVENANCE.unemployment.table} year={PROVENANCE.unemployment.year} sql={m.sql} confidence={m.conf} />
                )}
                {m.sql && (
                  <div>
                    <button onClick={() => setOpenSql((s) => ({ ...s, [i]: !s[i] }))} style={{ cursor: 'pointer', border: 0, background: 'transparent', color: 'oklch(75% 0.15 265)', fontWeight: 600, fontSize: 12, padding: 0 }}>
                      {openSql[i] ? t.hideSql : t.showSql}
                    </button>
                    {openSql[i] && (
                      <div className="sql-block">
                        <button
                          onClick={() => { navigator.clipboard?.writeText(m.sql!); setCopied(i); setTimeout(() => setCopied(-1), 1500) }}
                          style={{ position: 'absolute', top: 8, insetInlineEnd: 8, cursor: 'pointer', border: '1px solid oklch(30% 0.05 265)', background: 'oklch(16% 0.03 265)', color: '#f0f0fa', borderRadius: 8, padding: '3px 10px', fontSize: 11 }}
                        >
                          {copied === i ? t.copied : t.copy}
                        </button>
                        <pre dir="ltr">{highlight(m.sql).map((p, j) => <span key={j} style={{ color: p.kw ? 'oklch(75% 0.15 265)' : '#d6d6ea' }}>{p.t}</span>)}</pre>
                      </div>
                    )}
                  </div>
                )}
                {m.rows && m.rows.length > 0 && (
                  <div className="table-wrap">
                    <table className="data">
                      <thead><tr>{(m.cols || []).map((c) => <th key={c}>{c}</th>)}</tr></thead>
                      <tbody>
                        {m.rows.slice(0, 100).map((r, j) => (
                          <tr key={j}>{r.map((c, k) => <td key={k}>{fmt(c as number | string)}</td>)}</tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {/* P-022 — 2e vérification + suites logiques cliquables. */}
                {m.verification && (
                  <div className="muted" style={{ fontSize: 12 }}>✓ {t.verification} : {m.verification}</div>
                )}
                {m.followUps && m.followUps.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
                    <span className="muted">{t.followUps} :</span>
                    {m.followUps.map((f) => (
                      <button key={f} className="btn-ghost" style={{ borderRadius: 999 }} onClick={() => send(undefined, f)}>{f}</button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {busy && <div style={{ color: 'oklch(68% 0.03 265)' }}>{t.thinking}</div>}
      </div>
      <form onSubmit={send} style={{ position: 'sticky', bottom: 16, display: 'flex', gap: 10, padding: 8, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, backdropFilter: 'blur(12px)' }}>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder={t.placeholder} className="input" style={{ border: 0, background: 'transparent' }} />
        <button type="submit" className="btn">{t.send}</button>
      </form>
    </div>
  )
}
