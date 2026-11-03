import { useLocale, SUPPORTED_LOCALES, type Locale } from '../hooks/useLocale'
import { LOCALE_LABELS } from '../i18n'

interface Props {
  currentPath: string
}

export function NavBar({ currentPath }: Props) {
  const { t, locale, setLocale } = useLocale()

  const base = import.meta.env.BASE_URL ?? '/'
  const nav = [
    { href: base + 'chat', key: 'nav.chat' },
    { href: base + 'dashboards', key: 'nav.dashboards' },
    { href: base + 'upload', key: 'nav.import' },
  ]

  const handleLogout = () => {
    sessionStorage.removeItem('sovereign_api_key')
    window.location.href = base + 'login'
  }

  return (
    <nav
      data-testid="navbar"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '24px',
        padding: '0 24px',
        height: '56px',
        background: 'var(--brand)',
        color: '#fff',
        flexWrap: 'wrap',
      }}
    >
      <strong style={{ marginInlineEnd: '8px', fontSize: '1rem', letterSpacing: '-0.01em' }}>SovereignBI</strong>
      {nav.map(({ href, key }) => (
        <a
          key={href}
          href={href}
          style={{
            color: currentPath === href ? '#fff' : 'rgba(255,255,255,0.72)',
            textDecoration: 'none',
            fontWeight: currentPath === href ? 600 : 400,
            fontSize: '0.9375rem',
            transition: 'color 0.15s',
          }}
        >
          {t(key)}
        </a>
      ))}

      <div style={{ marginInlineStart: 'auto', display: 'flex', alignItems: 'center', gap: '6px' }}>
        {SUPPORTED_LOCALES.map((l: Locale) => (
          <button
            key={l}
            data-testid={`locale-btn-${l}`}
            onClick={() => setLocale(l)}
            aria-pressed={locale === l}
            style={{
              background: locale === l ? 'rgba(255,255,255,0.15)' : 'transparent',
              color: '#fff',
              border: locale === l ? '1px solid rgba(255,255,255,0.6)' : '1px solid rgba(255,255,255,0.3)',
              borderRadius: '999px',
              padding: '2px 10px',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontWeight: locale === l ? 600 : 400,
              fontFamily: 'inherit',
              transition: 'background 0.15s, border-color 0.15s',
            }}
          >
            {LOCALE_LABELS[l]}
          </button>
        ))}
        <button
          onClick={handleLogout}
          style={{
            marginInlineStart: '8px',
            background: 'transparent',
            color: 'rgba(255,255,255,0.85)',
            border: '1px solid rgba(255,255,255,0.3)',
            borderRadius: '8px',
            padding: '5px 12px',
            cursor: 'pointer',
            fontSize: '0.8125rem',
            fontFamily: 'inherit',
          }}
        >
          {t('nav.logout')}
        </button>
      </div>
    </nav>
  )
}
