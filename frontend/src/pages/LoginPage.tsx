import { useState } from 'react'
import { useLocale } from '../hooks/useLocale'
import { SUPPORTED_LOCALES, LOCALE_LABELS, type Locale } from '../i18n'

interface LoginPageProps {
  onLogin?: () => void
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const { t, locale, setLocale } = useLocale()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  const _env = (typeof import.meta !== 'undefined' && (import.meta as { env?: Record<string,string> }).env) ?? {}
  const API = (_env['VITE_API_BASE'] ?? _env['VITE_API_URL'] ?? '').replace(/\/$/, '')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password) { setError(t('login.fields_required')); return }
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({})) as { detail?: string }
        setError(data.detail ?? t('login.error'))
        return
      }
      const { token } = await res.json() as { token: string }
      localStorage.setItem('sovereign_api_key', token)
      onLogin?.()
    } catch { setError(t('login.error')) }
    finally { setLoading(false) }
  }

  const inp: React.CSSProperties = {
    display: 'block', width: '100%', padding: '10px 14px',
    border: '1px solid var(--border)', borderRadius: '10px',
    fontSize: '0.9375rem', color: 'var(--text)', background: 'var(--surface)',
    fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box',
  }

  return (
    <div style={{ maxWidth: '400px', margin: '80px auto', padding: '0 16px' }}>
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: '16px', padding: '40px',
        boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 4, marginBottom: 24 }}>
          {SUPPORTED_LOCALES.map((l: Locale) => (
            <button key={l} onClick={() => setLocale(l)} style={{
              background: locale === l ? 'var(--brand)' : 'transparent',
              color: locale === l ? '#fff' : 'var(--muted)',
              border: '1px solid var(--border)', borderRadius: '999px',
              padding: '2px 10px', cursor: 'pointer', fontSize: '0.75rem',
              fontWeight: locale === l ? 600 : 400, fontFamily: 'inherit',
            }}>{LOCALE_LABELS[l]}</button>
          ))}
        </div>

        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ fontSize: '2rem', marginBottom: 8 }}>⬡</div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: 'var(--text)' }}>SovereignBI</h1>
          <p style={{ fontSize: '0.8rem', color: 'var(--muted)', margin: '6px 0 0' }}>{t('login.subtitle')}</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: 'block', marginBottom: 6, fontSize: '0.75rem', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--muted)' }}>
              {t('login.email')}
            </label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              placeholder="vous@exemple.com" autoFocus autoComplete="email" style={inp}
              onFocus={e => { (e.target as HTMLInputElement).style.borderColor = 'var(--accent)' }}
              onBlur={e  => { (e.target as HTMLInputElement).style.borderColor = 'var(--border)' }} />
          </div>

          <div style={{ marginBottom: 20 }}>
            <label style={{ display: 'block', marginBottom: 6, fontSize: '0.75rem', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--muted)' }}>
              {t('login.password')}
            </label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="••••••••" autoComplete="current-password" style={inp}
              onFocus={e => { (e.target as HTMLInputElement).style.borderColor = 'var(--accent)' }}
              onBlur={e  => { (e.target as HTMLInputElement).style.borderColor = 'var(--border)' }} />
          </div>

          {error && <p style={{ color: 'var(--danger)', fontSize: '0.825rem', margin: '0 0 14px', padding: '8px 12px', background: 'oklch(97% 0.02 25)', borderRadius: 8 }}>{error}</p>}

          <button type="submit" disabled={loading} style={{
            display: 'block', width: '100%', padding: '11px',
            background: loading ? 'var(--muted)' : 'var(--brand)', color: '#fff',
            border: 'none', borderRadius: '10px', fontSize: '0.9375rem',
            fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
            fontFamily: 'inherit', transition: 'background 0.15s',
          }}>{loading ? '…' : t('login.submit')}</button>
        </form>
      </div>
    </div>
  )
}
