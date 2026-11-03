import { ReactNode } from 'react'
import { useLocale } from '../hooks/useLocale'
import { SUPPORTED_LOCALES, type Locale } from '../i18n'

export type Page = 'home' | 'chat' | 'dashboards' | 'data'

interface AppShellProps {
  current: Page
  children: ReactNode
  onNavigate: (page: Page) => void
  onLogout: () => void
}

const NAV_ITEMS: { id: Page; icon: string; labelKey: string }[] = [
  { id: 'home',       icon: '⊞',  labelKey: 'nav.home' },
  { id: 'chat',       icon: '💬', labelKey: 'nav.chat' },
  { id: 'dashboards', icon: '📊', labelKey: 'nav.dashboards' },
  { id: 'data',       icon: '📁', labelKey: 'nav.import' },
]

export function AppShell({ current, children, onNavigate, onLogout }: AppShellProps) {
  const { t, locale, setLocale } = useLocale()
  const isRtl = locale === 'ar'

  const topbarLabel = current === 'home'
    ? t('nav.home')
    : current === 'data'
    ? t('nav.import')
    : current === 'dashboards'
    ? t('nav.dashboards')
    : t('nav.chat')

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      overflow: 'hidden',
      direction: isRtl ? 'rtl' : 'ltr',
    }}>
      {/* ── Sidebar ── */}
      <aside style={{
        width: 'var(--sidebar-w)',
        minWidth: 'var(--sidebar-w)',
        background: 'var(--sidebar-bg)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 10,
        userSelect: 'none',
      }}>
        {/* Logo */}
        <div style={{
          height: 'var(--topbar-h)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 16px',
          gap: 10,
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          flexShrink: 0,
        }}>
          <span style={{ fontSize: '1.3rem' }}>⬡</span>
          <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#fff', letterSpacing: '-0.01em' }}>
            SovereignBI
          </span>
        </div>

        {/* Nav items */}
        <nav style={{ flex: 1, padding: '8px 0', overflowY: 'auto' }}>
          {NAV_ITEMS.map(item => {
            const active = current === item.id
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  width: 'calc(100% - 16px)',
                  margin: '1px 8px',
                  padding: '10px 12px',
                  background: active ? 'var(--sidebar-active)' : 'transparent',
                  color: active ? 'var(--sidebar-text-active)' : 'var(--sidebar-text)',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontFamily: 'inherit',
                  fontWeight: active ? 600 : 400,
                  textAlign: isRtl ? 'right' : 'left',
                  borderRadius: '6px',
                  transition: 'background 0.15s, color 0.15s',
                }}
                onMouseEnter={e => { if (!active) (e.currentTarget as HTMLButtonElement).style.background = 'var(--sidebar-hover)' }}
                onMouseLeave={e => { if (!active) (e.currentTarget as HTMLButtonElement).style.background = 'transparent' }}
              >
                <span style={{ fontSize: '1.05rem', width: 20, textAlign: 'center', flexShrink: 0 }}>{item.icon}</span>
                <span>{t(item.labelKey)}</span>
              </button>
            )
          })}
        </nav>

        {/* Logout */}
        <div style={{ padding: '8px', borderTop: '1px solid rgba(255,255,255,0.08)', flexShrink: 0 }}>
          <button
            onClick={onLogout}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              width: 'calc(100% - 0px)', padding: '10px 12px',
              background: 'transparent', color: 'var(--sidebar-text)',
              border: 'none', cursor: 'pointer',
              fontSize: '0.875rem', fontFamily: 'inherit',
              borderRadius: '6px', textAlign: isRtl ? 'right' : 'left',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--sidebar-hover)' }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent' }}
          >
            <span style={{ fontSize: '1.05rem', width: 20, textAlign: 'center', flexShrink: 0 }}>⎋</span>
            <span>{t('nav.logout')}</span>
          </button>
        </div>
      </aside>

      {/* ── Right panel ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
        {/* Topbar */}
        <header style={{
          height: 'var(--topbar-h)',
          minHeight: 'var(--topbar-h)',
          background: 'var(--surface)',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 24px',
          gap: 12,
          flexShrink: 0,
        }}>
          <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text)', flex: 1 }}>
            {topbarLabel}
          </span>

          {/* Locale switcher */}
          <div style={{ display: 'flex', gap: 4 }}>
            {SUPPORTED_LOCALES.map((l: Locale) => (
              <button
                key={l}
                onClick={() => setLocale(l)}
                style={{
                  padding: '3px 9px',
                  borderRadius: '999px',
                  border: '1px solid var(--border)',
                  background: locale === l ? 'var(--brand)' : 'transparent',
                  color: locale === l ? '#fff' : 'var(--muted)',
                  fontSize: '0.72rem', fontWeight: locale === l ? 600 : 400,
                  cursor: 'pointer', fontFamily: 'inherit',
                }}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </header>

        {/* Content */}
        <main style={{
          flex: 1,
          overflow: 'auto',
          background: 'var(--bg)',
          padding: '28px 32px',
        }}>
          {children}
        </main>
      </div>
    </div>
  )
}
