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
  const _prodApi = 'https://sovereignbi-api.147-5-126-188.sslip.io'
  const API = (_env['VITE_API_BASE'] ?? _env['VITE_API_URL'] ?? (typeof window !== 'undefined' && window.location.hostname !== 'localhost' ? _prodApi : '')).replace(/\/$/, '')

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
      localStorage.setItem('mizan_api_key', token)
      onLogin?.()
    } catch { setError(t('login.error')) }
    finally { setLoading(false) }
  }

  const inp: React.CSSProperties = {
    display: 'block', width: '100%', padding: '11px 14px',
    border: '1px solid var(--border)', borderRadius: '10px',
    fontSize: '0.9375rem', color: 'var(--text)',
    background: 'oklch(10% 0.02 265 / 0.8)',
    fontFamily: 'inherit', outline: 'none', boxSizing: 'border-box',
    transition: 'border-color 0.15s, box-shadow 0.15s',
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--mesh-bg)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '24px 16px',
    }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        {/* Locale */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 4, marginBottom: 20 }}>
          {SUPPORTED_LOCALES.map((l: Locale) => (
            <button key={l} onClick={() => setLocale(l)} style={{
              background: locale === l ? 'var(--brand-dim)' : 'transparent',
              color: locale === l ? 'oklch(75% 0.2 265)' : 'var(--text-dim)',
              border: '1px solid var(--border)', borderRadius: 6,
              padding: '3px 10px', cursor: 'pointer', fontSize: '0.72rem',
              fontWeight: locale === l ? 600 : 400, fontFamily: 'inherit',
            }}>{LOCALE_LABELS[l]}</button>
          ))}
        </div>

        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 20, padding: '40px',
          backdropFilter: 'blur(20px)',
          boxShadow: '0 0 60px oklch(65% 0.22 265 / 0.08)',
        }}>
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <div style={{
              width: 48, height: 48, borderRadius: 14, margin: '0 auto 16px',
              background: 'linear-gradient(135deg, var(--brand), oklch(55% 0.2 290))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 22, boxShadow: '0 0 24px var(--brand-glow)',
              color: '#fff',
            }}>⬡</div>
            <h1 style={{
              fontSize: '1.3rem', fontWeight: 700, margin: '0 0 6px',
              background: 'linear-gradient(135deg, #f0f0fa, oklch(75% 0.15 265))',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            }}>MizanBI</h1>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
              {t('login.subtitle')}
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label style={{
                display: 'block', marginBottom: 7,
                fontSize: '0.72rem', fontWeight: 600,
                textTransform: 'uppercase', letterSpacing: '0.08em',
                color: 'var(--text-muted)',
              }}>{t('login.email')}</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                placeholder="vous@exemple.com" autoFocus autoComplete="email" style={inp}
                onFocus={e => { (e.target as HTMLInputElement).style.borderColor = 'var(--brand)'; (e.target as HTMLInputElement).style.boxShadow = '0 0 0 3px var(--brand-dim)' }}
                onBlur={e  => { (e.target as HTMLInputElement).style.borderColor = 'var(--border)'; (e.target as HTMLInputElement).style.boxShadow = 'none' }} />
            </div>

            <div style={{ marginBottom: 24 }}>
              <label style={{
                display: 'block', marginBottom: 7,
                fontSize: '0.72rem', fontWeight: 600,
                textTransform: 'uppercase', letterSpacing: '0.08em',
                color: 'var(--text-muted)',
              }}>{t('login.password')}</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                placeholder="••••••••" autoComplete="current-password" style={inp}
                onFocus={e => { (e.target as HTMLInputElement).style.borderColor = 'var(--brand)'; (e.target as HTMLInputElement).style.boxShadow = '0 0 0 3px var(--brand-dim)' }}
                onBlur={e  => { (e.target as HTMLInputElement).style.borderColor = 'var(--border)'; (e.target as HTMLInputElement).style.boxShadow = 'none' }} />
            </div>

            {error && (
              <p style={{
                color: 'var(--danger)', fontSize: '0.825rem', margin: '0 0 16px',
                padding: '10px 14px',
                background: 'oklch(15% 0.05 25 / 0.5)',
                border: '1px solid oklch(55% 0.2 25 / 0.3)',
                borderRadius: 10,
              }}>{error}</p>
            )}

            <button type="submit" disabled={loading} style={{
              display: 'block', width: '100%', padding: '12px',
              background: loading ? 'var(--text-dim)' : 'var(--brand)',
              color: '#fff', border: 'none', borderRadius: 12,
              fontSize: '0.9375rem', fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              fontFamily: 'inherit',
              boxShadow: loading ? 'none' : '0 0 20px var(--brand-glow)',
              transition: 'all 0.15s',
            }}>{loading ? '…' : t('login.submit')}</button>
          </form>
        </div>

        {/* Sovereign badge */}
        <div style={{
          marginTop: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          fontSize: 11, color: 'var(--text-dim)',
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: 'var(--accent)', boxShadow: '0 0 6px var(--accent)',
            display: 'inline-block',
          }} />
          <span>Données locales · Oracle ARM · Djibouti</span>
        </div>
      </div>
    </div>
  )
}
