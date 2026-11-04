import { ReactNode, useState } from 'react'
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
  { id: 'chat',       icon: '◎',  labelKey: 'nav.chat' },
  { id: 'dashboards', icon: '▦',  labelKey: 'nav.dashboards' },
  { id: 'data',       icon: '⬆',  labelKey: 'nav.import' },
]

const PAGE_LABEL: Record<Page, string> = {
  home:       'Accueil',
  chat:       'Q&A',
  dashboards: 'Rapports',
  data:       'Données',
}

export function AppShell({ current, children, onNavigate, onLogout }: AppShellProps) {
  const { locale, setLocale } = useLocale()
  const isRtl = locale === 'ar'
  const [cmdK, setCmdK] = useState(false)

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      overflow: 'hidden',
      direction: isRtl ? 'rtl' : 'ltr',
      background: 'var(--bg)',
      position: 'relative',
    }}>
      {/* ── Mesh background ── */}
      <div style={{
        position: 'fixed', inset: 0, zIndex: 0,
        background: 'var(--mesh-bg)',
        pointerEvents: 'none',
      }} />

      {/* ── Neural Sidebar ── */}
      <aside style={{
        position: 'fixed',
        [isRtl ? 'right' : 'left']: 0,
        top: 0, bottom: 0,
        width: 'var(--sidebar-w)',
        zIndex: 20,
        background: 'oklch(12% 0.02 265 / 0.92)',
        borderRight: isRtl ? 'none' : '1px solid var(--border-subtle)',
        borderLeft: isRtl ? '1px solid var(--border-subtle)' : 'none',
        backdropFilter: 'blur(20px)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '20px 0',
        gap: 4,
        userSelect: 'none',
      }}>
        {/* Logo */}
        <div
          onClick={() => onNavigate('home')}
          title="SovereignBI"
          style={{
            width: 36, height: 36, borderRadius: 10,
            background: 'linear-gradient(135deg, var(--brand), oklch(55% 0.2 290))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16, cursor: 'pointer', marginBottom: 24,
            boxShadow: '0 0 20px var(--brand-glow)',
            color: '#fff', fontWeight: 700,
          }}
        >⬡</div>

        {/* Nav items */}
        {NAV_ITEMS.map(item => {
          const active = current === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              title={PAGE_LABEL[item.id]}
              style={{
                width: 44, height: 44, borderRadius: 12,
                border: 'none', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 18, position: 'relative',
                background: active ? 'var(--brand-dim)' : 'transparent',
                color: active ? 'var(--brand)' : 'var(--text-dim)',
                boxShadow: active ? '0 0 12px var(--brand-glow)' : 'none',
                transition: 'all 0.15s',
                fontFamily: 'inherit',
              }}
              onMouseEnter={e => {
                if (!active) (e.currentTarget as HTMLElement).style.background = 'oklch(20% 0.03 265 / 0.6)'
              }}
              onMouseLeave={e => {
                if (!active) (e.currentTarget as HTMLElement).style.background = 'transparent'
              }}
            >
              {item.icon}
              {/* Active pulse dot */}
              {active && (
                <span style={{
                  position: 'absolute', top: 8, right: 8,
                  width: 6, height: 6, borderRadius: '50%',
                  background: 'var(--accent)',
                  boxShadow: '0 0 6px var(--accent)',
                }} />
              )}
            </button>
          )
        })}

        <div style={{ flex: 1 }} />

        {/* Settings */}
        <button
          title="Paramètres"
          style={{
            width: 44, height: 44, borderRadius: 12, border: 'none',
            background: 'transparent', color: 'var(--text-dim)',
            cursor: 'pointer', fontSize: 17, fontFamily: 'inherit',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >⚙</button>

        {/* Avatar / logout */}
        <button
          onClick={onLogout}
          title="Déconnexion"
          style={{
            width: 36, height: 36, borderRadius: 10, border: 'none',
            background: 'oklch(25% 0.05 265)',
            color: 'var(--text)',
            cursor: 'pointer', fontSize: 13, fontWeight: 700,
            fontFamily: 'inherit', marginTop: 4,
          }}
        >R</button>
      </aside>

      {/* ── Topbar ── */}
      <header style={{
        position: 'fixed',
        [isRtl ? 'right' : 'left']: 'var(--sidebar-w)',
        right: isRtl ? 'var(--sidebar-w)' : 0,
        top: 0,
        height: 'var(--topbar-h)',
        zIndex: 15,
        background: 'oklch(10% 0.02 265 / 0.75)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 28px',
        gap: 16,
      }}>
        {/* Breadcrumb */}
        <div style={{ fontSize: 14, color: 'var(--text-muted)' }}>
          SovereignBI{' '}
          <span style={{ color: 'oklch(70% 0.02 265)', fontWeight: 500 }}>
            / {PAGE_LABEL[current]}
          </span>
        </div>

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* ⌘K */}
          <button
            onClick={() => setCmdK(v => !v)}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              background: 'oklch(16% 0.03 265 / 0.8)',
              border: '1px solid var(--border)',
              borderRadius: 8, padding: '6px 14px',
              fontSize: 12, color: 'var(--text-muted)',
              cursor: 'pointer', fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            ⌘K{' '}
            <kbd style={{
              background: 'oklch(22% 0.04 265)', borderRadius: 4,
              padding: '1px 5px', fontSize: 11,
            }}>Commande</kbd>
          </button>

          {/* Locale switcher */}
          <div style={{ display: 'flex', gap: 4 }}>
            {SUPPORTED_LOCALES.map((l: Locale) => (
              <button
                key={l}
                onClick={() => setLocale(l)}
                style={{
                  padding: '4px 10px', borderRadius: 6,
                  border: '1px solid var(--border)',
                  background: locale === l ? 'var(--brand-dim)' : 'transparent',
                  color: locale === l ? 'oklch(75% 0.2 265)' : 'var(--text-dim)',
                  fontSize: 12, fontWeight: locale === l ? 600 : 400,
                  cursor: 'pointer', fontFamily: 'inherit',
                  transition: 'all 0.15s',
                }}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* ── Main content ── */}
      <main style={{
        position: 'fixed',
        [isRtl ? 'right' : 'left']: 'var(--sidebar-w)',
        right: isRtl ? 'var(--sidebar-w)' : 0,
        top: 'var(--topbar-h)',
        bottom: 0,
        overflow: 'auto',
        zIndex: 1,
        padding: '32px',
      }}>
        {children}
      </main>

      {/* ── Sovereign badge ── */}
      <div style={{
        position: 'fixed', bottom: 20, right: 24, zIndex: 30,
        background: 'oklch(13% 0.025 265 / 0.9)',
        border: '1px solid oklch(68% 0.18 155 / 0.3)',
        borderRadius: 10, padding: '7px 14px',
        display: 'flex', alignItems: 'center', gap: 8,
        backdropFilter: 'blur(16px)',
        fontSize: 11,
        boxShadow: '0 0 20px oklch(68% 0.18 155 / 0.1)',
      }}>
        <span style={{
          width: 7, height: 7, borderRadius: '50%',
          background: 'var(--accent)',
          boxShadow: '0 0 8px var(--accent)',
          display: 'inline-block',
        }} />
        <span style={{ color: 'var(--accent)', fontWeight: 500 }}>Données locales</span>
        <span style={{ color: 'var(--text-dim)' }}>·</span>
        <span style={{ color: 'var(--text-muted)' }}>Oracle ARM · Djibouti</span>
      </div>

      {/* ── ⌘K modal overlay ── */}
      {cmdK && (
        <div
          onClick={() => setCmdK(false)}
          style={{
            position: 'fixed', inset: 0, zIndex: 50,
            background: 'rgba(7,7,17,0.7)', backdropFilter: 'blur(8px)',
            display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
            paddingTop: 120,
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              width: 560,
              background: 'oklch(14% 0.03 265)',
              border: '1px solid var(--border)',
              borderRadius: 16,
              overflow: 'hidden',
              boxShadow: '0 24px 80px rgba(0,0,0,0.6)',
            }}
          >
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '14px 20px', borderBottom: '1px solid var(--border-subtle)',
            }}>
              <span style={{ color: 'var(--text-muted)', fontSize: 16 }}>⌘</span>
              <span style={{ fontSize: 14, color: 'var(--text-muted)' }}>Navigation rapide…</span>
            </div>
            <div style={{ padding: '8px 0' }}>
              {NAV_ITEMS.map(item => (
                <button
                  key={item.id}
                  onClick={() => { onNavigate(item.id); setCmdK(false) }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 14,
                    width: '100%', padding: '12px 20px',
                    background: 'transparent', border: 'none',
                    color: 'var(--text)', fontSize: 14, cursor: 'pointer',
                    fontFamily: 'inherit', textAlign: 'left',
                  }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'oklch(20% 0.03 265 / 0.6)' }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent' }}
                >
                  <span style={{ fontSize: 18, width: 24, textAlign: 'center' }}>{item.icon}</span>
                  <span>{PAGE_LABEL[item.id]}</span>
                  <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-dim)', fontFamily: "'JetBrains Mono', monospace" }}>
                    {item.id === 'home' ? '⌘1' : item.id === 'chat' ? '⌘2' : item.id === 'dashboards' ? '⌘3' : '⌘4'}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
