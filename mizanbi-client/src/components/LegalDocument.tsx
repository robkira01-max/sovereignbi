import type { Dict, Lang } from '../lib/i18n'
import { LEGAL, PLACEHOLDER_RE } from '../lib/legalConfig'
import { fill, getLegalDoc, type LegalKind } from '../lib/legalContent'

function Marked({ text }: { text: string }) {
  const parts = text.split(new RegExp(`(${PLACEHOLDER_RE.source})`, 'g'))
  return (
    <>
      {parts.map((p, i) =>
        new RegExp(`^${PLACEHOLDER_RE.source}$`).test(p)
          ? <mark key={i} style={{ background: '#fde68a', color: '#111', padding: '0 3px', borderRadius: 3 }}>{p}</mark>
          : <span key={i}>{p}</span>,
      )}
    </>
  )
}

interface Props {
  kind: LegalKind
  lang: Lang
  t: Dict
  /** Mode compact (fenêtre d'acceptation) : titres plus petits, pas de marge basse. */
  compact?: boolean
}

export default function LegalDocument({ kind, lang, t, compact = false }: Props) {
  const doc = getLegalDoc(kind, lang)
  return (
    <article>
      <h1 style={{ fontSize: compact ? 20 : 28, fontWeight: 700, marginBottom: 8 }}>{doc.title}</h1>
      <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 16 }}>{t.legalUi.updated} {LEGAL.updated[lang]}</p>
      {LEGAL.draft && (
        <p role="note" style={{ background: 'rgba(253, 230, 138, .15)', border: '1px solid #fde68a', borderRadius: 8, padding: '8px 12px', fontSize: 13, marginBottom: 24 }}>
          {t.legalUi.draftBanner}
        </p>
      )}
      {doc.sections.map((s, i) => (
        <section key={i} style={{ marginBottom: compact ? 16 : 28 }}>
          <h2 style={{ fontSize: compact ? 15 : 18, fontWeight: 600, marginBottom: 8 }}>{s.title}</h2>
          {s.paragraphs?.map((p, j) => <p key={j} style={{ lineHeight: 1.7, marginBottom: 8 }}><Marked text={fill(p)} /></p>)}
          {s.bullets && (
            <ul style={{ paddingInlineStart: 20, lineHeight: 1.7, marginBottom: 8 }}>
              {s.bullets.map((b, j) => <li key={j}><Marked text={fill(b)} /></li>)}
            </ul>
          )}
          {s.after && <p style={{ lineHeight: 1.7 }}><Marked text={fill(s.after)} /></p>}
        </section>
      ))}
    </article>
  )
}
