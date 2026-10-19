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
        gap: '16px',
        padding: '10px 20px',
        background: '#1e40af',
        color: '#fff',
        flexWrap: 'wrap',
      }}
    >
      <strong style={{ marginInlineEnd: '16px' }}>SovereignBI</strong>
      {nav.map(({ href, key }) => (
        <a
          key={href}
          href={href}
          style={{
            color: currentPath === href ? '#bfdbfe' : '#fff',
            textDecoration: 'none',
            fontWeight: currentPath === href ? 700 : 400,
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
              background: locale === l ? '#fff' : 'transparent',
              color: locale === l ? '#1e40af' : '#fff',
              border: '1px solid #93c5fd',
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
        <button
          onClick={handleLogout}
          style={{
            marginInlineStart: '8px',
            background: 'transparent',
            color: '#fff',
            border: '1px solid #93c5fd',
            borderRadius: '4px',
            padding: '4px 10px',
            cursor: 'pointer',
          }}
        >
          {t('nav.logout')}
        </button>
      </div>
    </nav>
  )
}
