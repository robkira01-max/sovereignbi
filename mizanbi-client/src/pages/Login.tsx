import { useState } from 'react'
import type { Dict, Lang } from '../lib/i18n'
import { LANGS } from '../lib/i18n'
import { DEMO_USER } from '../data/demo'
import { isApiConfigured, login } from '../lib/api'

interface Props {
  t: Dict
  lang: Lang
  setLang: (l: Lang) => void
  onEnter: (token: string, email: string) => void
}

export default function LoginPage({ t, lang, setLang, onEnter }: Props) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErr('')
    if (!isApiConfigured()) {
      setErr(t.loginError)
      return
    }
    setBusy(true)
    try {
      const r = await login(email, password)
      onEnter(r.token, r.email)
    } catch {
      setErr(t.loginError)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, position: 'relative' }}>
      <div style={{ position: 'absolute', top: 16, insetInlineEnd: 16, display: 'flex', gap: 6 }}>
        {LANGS.map((l) => (
          <button key={l} onClick={() => setLang(l)} className="lang-btn" style={{ background: lang === l ? 'var(--brand)' : 'var(--surface)', border: '1px solid var(--border)' }}>
            {l.toUpperCase()}
          </button>
        ))}
      </div>
      <form onSubmit={submit} style={{ width: '100%', maxWidth: 400, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 32, display: 'flex', flexDirection: 'column', gap: 16, backdropFilter: 'blur(12px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 12, background: 'linear-gradient(135deg, oklch(65% 0.22 265), oklch(68% 0.18 155))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 18, color: '#070711' }}>M</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 20, letterSpacing: '-.02em' }}>MizanBI</div>
            <div style={{ color: 'oklch(68% 0.03 265)', fontSize: 12 }}>{t.tagline}</div>
          </div>
        </div>
        <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)' }}>{t.slogan}</p>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontWeight: 500, fontSize: 13 }}>
          {t.email}
          <input type="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="nom@instad.dj" />
        </label>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontWeight: 500, fontSize: 13 }}>
          {t.password}
          <input type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        {err && <div style={{ color: 'oklch(75% 0.17 25)', fontSize: 13 }}>{err}</div>}
        <button type="submit" className="btn" disabled={busy}>{busy ? '…' : t.login}</button>
        {!isApiConfigured() && (
          <>
            <button type="button" className="btn-ghost" onClick={() => onEnter('demo', 'demo@instad.dj')}>{t.demo}</button>
            <div className="muted" style={{ fontSize: 13, textAlign: 'center' }}>{t.demoAccount} · {DEMO_USER.initials}</div>
          </>
        )}
        <div className="muted">{t.loi25} · {t.demoBadge} · {!isApiConfigured() ? t.off : t.live}</div>
      </form>
    </div>
  )
}
