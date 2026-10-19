import { useState } from 'react'
import { useLocale, SUPPORTED_LOCALES, type Locale } from '../hooks/useLocale'
import { LOCALE_LABELS } from '../i18n'

export function LoginPage() {
  const { t, locale, setLocale } = useLocale()
  const [key, setKey] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!key.trim()) { setError(t('login.key_required')); return }
    sessionStorage.setItem('sovereign_api_key', key.trim())
    window.location.href = (import.meta.env.BASE_URL ?? '/') + 'chat'
  }

  return (
    <div style={{ maxWidth: '360px', margin: '80px auto', padding: '24px', border: '1px solid #e5e7eb', borderRadius: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px', marginBottom: '16px' }}>
        {SUPPORTED_LOCALES.map((l: Locale) => (
          <button
            key={l}
            data-testid={`locale-btn-${l}`}
            onClick={() => setLocale(l)}
            aria-pressed={locale === l}
            style={{
              background: locale === l ? '#2563eb' : 'transparent',
              color: locale === l ? '#fff' : '#374151',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              padding: '2px 7px',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontWeight: locale === l ? 700 : 400,
            }}
          >
            {LOCALE_LABELS[l]}
          </button>
        ))}
      </div>
      <h1 style={{ fontSize: '1.4rem', marginBottom: '16px' }}>{t('login.title')}</h1>
      <form onSubmit={handleSubmit}>
        <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem' }}>
          {t('login.api_key')}
          <input
            type="password"
            value={key}
            onChange={e => setKey(e.target.value)}
            placeholder="sk-..."
            style={{ display: 'block', width: '100%', padding: '8px', marginTop: '4px', border: '1px solid #d1d5db', borderRadius: '4px', boxSizing: 'border-box' }}
            autoFocus
          />
        </label>
        {error && <p style={{ color: '#dc2626', fontSize: '0.85rem' }}>{error}</p>}
        <button
          type="submit"
          style={{ width: '100%', padding: '10px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 600 }}
        >
          {t('login.submit')}
        </button>
      </form>
    </div>
  )
}
