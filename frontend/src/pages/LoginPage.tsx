import { useState } from 'react'
import { useLocale, SUPPORTED_LOCALES, type Locale } from '../hooks/useLocale'
import { LOCALE_LABELS } from '../i18n'

interface LoginPageProps {
  onLogin?: () => void
}

export function LoginPage({ onLogin }: LoginPageProps = {}) {
  const { t, locale, setLocale } = useLocale()
  const [key, setKey] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!key.trim()) { setError(t('login.key_required')); return }
    localStorage.setItem('sovereign_api_key', key.trim())
    if (onLogin) onLogin()
    else window.location.href = (import.meta.env.BASE_URL ?? '/') + 'chat'
  }

  return (
    <div style={{ maxWidth: '400px', margin: '80px auto', padding: '0 16px' }}>
      <div style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: '16px',
        padding: '40px',
        boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px', marginBottom: '24px' }}>
          {SUPPORTED_LOCALES.map((l: Locale) => (
            <button
              key={l}
              data-testid={`locale-btn-${l}`}
              onClick={() => setLocale(l)}
              aria-pressed={locale === l}
              style={{
                background: locale === l ? 'var(--brand)' : 'transparent',
                color: locale === l ? '#fff' : 'var(--muted)',
                border: '1px solid var(--border)',
                borderRadius: '999px',
                padding: '2px 10px',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: locale === l ? 600 : 400,
                fontFamily: 'inherit',
              }}
            >
              {LOCALE_LABELS[l]}
            </button>
          ))}
        </div>

        <h1 style={{ fontSize: '1.375rem', fontWeight: 700, margin: '0 0 24px', color: 'var(--text)' }}>
          {t('login.title')}
        </h1>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{
              display: 'block',
              marginBottom: '6px',
              fontSize: '0.75rem',
              fontWeight: 500,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: 'var(--muted)',
            }}>
              {t('login.api_key')}
            </label>
            <input
              type="password"
              value={key}
              onChange={e => setKey(e.target.value)}
              placeholder="sk-..."
              autoFocus
              style={{
                display: 'block',
                width: '100%',
                padding: '10px 14px',
                border: '1px solid var(--border)',
                borderRadius: '10px',
                fontSize: '0.9375rem',
                color: 'var(--text)',
                background: 'var(--surface)',
                fontFamily: 'inherit',
                outline: 'none',
                boxSizing: 'border-box',
              }}
              onFocus={e => { e.target.style.borderColor = 'var(--accent)' }}
              onBlur={e => { e.target.style.borderColor = 'var(--border)' }}
            />
          </div>
          {error && (
            <p style={{ margin: '0 0 12px', fontSize: '0.85rem', color: 'var(--danger)' }}>{error}</p>
          )}
          <button
            type="submit"
            style={{
              width: '100%',
              padding: '11px',
              background: 'var(--brand)',
              color: '#fff',
              border: 'none',
              borderRadius: '10px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.9375rem',
              fontFamily: 'inherit',
            }}
            onMouseOver={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--brand-hover)' }}
            onMouseOut={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--brand)' }}
          >
            {t('login.submit')}
          </button>
        </form>
      </div>
    </div>
  )
}
