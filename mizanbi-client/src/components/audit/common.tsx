import type { ReactNode } from 'react'
import type { Dict } from '../../lib/i18n'
import { classify } from '../../lib/auditApi'

export type AuditText = Dict['audit']

export function ErrorBox({ error, a }: { error: unknown; a: AuditText }) {
  const c = classify(error)
  const base = a.errors[c.kind] ?? a.errors.server
  return (
    <div role="alert" style={{ padding: '10px 14px', borderRadius: 10, border: '1px solid var(--warn, #fbbf24)', fontSize: 13 }}>
      {base}{c.message && c.kind !== 'unconfigured' ? <> — <span>{c.message}</span></> : null}
    </div>
  )
}

export function RiskNotice({ a }: { a: AuditText }) {
  return <p className="muted" role="note" style={{ margin: 0, fontSize: 12 }}>⚠️ {a.disclaimer}</p>
}

export function Hash({ value, label }: { value?: string | null; label: string }) {
  if (!value) return null
  return <span title={value} style={{ fontFamily: 'monospace', fontSize: 12 }}>{label} {value.slice(0, 12)}…</span>
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13 }}>
      <span style={{ fontWeight: 600 }}>{label}</span>
      {children}
      {hint && <span className="muted" style={{ fontSize: 11 }}>{hint}</span>}
    </label>
  )
}

export function PageHead({ title, sub }: { title: string; sub: string }) {
  return (
    <div>
      <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, letterSpacing: '-.02em' }}>{title}</h1>
      <p style={{ margin: '4px 0 0', color: 'var(--muted)' }}>{sub}</p>
    </div>
  )
}

export function Empty({ text }: { text: string }) {
  return <p className="muted" role="status">{text}</p>
}
