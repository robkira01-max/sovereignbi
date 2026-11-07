import { ReactNode, useState } from 'react'
import { useLocale } from '../hooks/useLocale'
import { SUPPORTED_LOCALES, type Locale } from '../i18n'

export type Page = 'home' | 'chat' | 'dashboards' | 'data' | 'scrolly'

interface AppShellProps {
  current: Page
  children: ReactNode
  onNavigate: (page: Page) => void
  onLogout: () => void
  userEmail?: string
}

const HOME_ICON  = 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6'
const DASH_ICON  = 'M4 5a1 1 0 011-1h4a1 1 0 011 1v5a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h4a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM14 5a1 1 0 011-1h4a1 1 0 011 1v3a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM14 11a1 1 0 011-1h4a1 1 0 011 1v8a1 1 0 01-1 1h-4a1 1 0 01-1-1v-8z'
const DATA_ICON  = 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12'
const CHAT_ICON  = 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z'

const NAV_ITEMS: { id: Page; icon: string; label: string }[] = [
  { id: 'home',       icon: HOME_ICON, label: 'Accueil' },
  { id: 'dashboards', icon: DASH_ICON, label: 'Rapports' },
  { id: 'data',       icon: DATA_ICON, label: 'Données' },
]

const PAGE_LABEL: Record<Page, string> = {
  home:       'Accueil',
  chat:       'Q&A',
  dashboards: 'Rapports',
  data:       'Données',
  scrolly:    'Rapport narratif',
}

export function AppShell({ current, children, onNavigate, onLogout, userEmail }: AppShellProps) {
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
      {/* ── Background ── */}
      <div style={{
        position: 'fixed', inset: 0, zIndex: 0,
        background: 'var(--mesh-bg)',
        pointerEvents: 'none',
      }} />

      {/* ── Sidebar 60px ── */}
      <aside style={{
        position: 'fixed',
        [isRtl ? 'right' : 'left']: 0,
        top: 0, bottom: 0,
        width: '60px',
        zIndex: 20,
        background: 'oklch(10% 0.025 265 / 0.8)',
        borderRight: isRtl ? 'none' : '1px solid oklch(25% 0.04 265 / 0.6)',
        borderLeft: isRtl ? '1px solid oklch(25% 0.04 265 / 0.6)' : 'none',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '12px 0',
        gap: 6,
        userSelect: 'none',
      }}>
        {/* Logo "M" */}
        <div
          onClick={() => onNavigate('home')}
          title="MizanBI"
          style={{
            width: 34, height: 34, borderRadius: 10,
            background: 'linear-gradient(135deg, oklch(65% 0.22 265), oklch(68% 0.18 155))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 16, fontWeight: 700, cursor: 'pointer', marginBottom: 14,
            color: '#070711',
          }}
        >M</div>

        {/* Nav items */}
        {NAV_ITEMS.map(item => {
          const active = current === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              title={item.label}
              aria-label={item.label}
              style={{
                width: 42, height: 42, borderRadius: 12,
                border: 'none', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: active ? 'oklch(25% 0.09 265)' : 'transparent',
                color: active ? 'oklch(75% 0.22 265)' : 'oklch(65% 0.03 265)',
                transition: 'all 0.15s',
                fontFamily: 'inherit',
              }}
              onMouseEnter={e => { if (!active) (e.currentTarget as HTMLElement).style.background = 'oklch(22% 0.06 265)' }}
              onMouseLeave={e => { if (!active) (e.currentTarget as HTMLElement).style.background = 'transparent' }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="1.8"
                strokeLinecap="round" strokeLinejoin="round">
                <path d={item.icon} />
              </svg>
            </button>
          )
        })}
      </aside>

      {/* ── Topbar 56px ── */}
      <header style={{
        position: 'fixed',
        [isRtl ? 'right' : 'left']: '60px',
        [isRtl ? 'left' : 'right']: 0,
        top: 0,
        height: '56px',
        zIndex: 15,
        background: 'oklch(10% 0.025 265 / 0.6)',
        backdropFilter: 'blur(10px)',
        borderBottom: '1px solid oklch(25% 0.04 265 / 0.6)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        gap: 14,
      }}>
        {/* Page title */}
        <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--text)', flex: 1 }}>
          {PAGE_LABEL[current]}
        </div>

        {/* Locale switcher */}
        <div style={{ display: 'flex', gap: 4 }}>
          {SUPPORTED_LOCALES.map((l: Locale) => (
            <button
              key={l}
              onClick={() => setLocale(l)}
              style={{
                padding: '5px 10px', borderRadius: 8, border: 'none',
                background: locale === l ? 'oklch(25% 0.08 265)' : 'transparent',
                color: '#f0f0fa',
                fontSize: 12, fontWeight: locale === l ? 600 : 400,
                cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.15s',
              }}
            >
              {l.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Email */}
        {userEmail && (
          <span style={{ color: 'oklch(68% 0.03 265)', fontSize: 12 }}>
            {userEmail}
          </span>
        )}

        {/* ⌘K */}
        <button
          onClick={() => setCmdK(v => !v)}
          style={{
            display: 'flex', alignItems: 'center', gap: 8,
            background: 'oklch(16% 0.03 265 / 0.8)',
            border: '1px solid var(--border)',
            borderRadius: 8, padding: '5px 12px',
            fontSize: 12, color: 'var(--text-muted)',
            cursor: 'pointer', fontFamily: "'JetBrains Mono', monospace",
          }}
        >⌘K</button>

        {/* Logout */}
        <button
          onClick={onLogout}
          style={{
            cursor: 'pointer', border: '1px solid oklch(25% 0.04 265 / 0.8)',
            background: 'transparent', color: '#f0f0fa',
            borderRadius: 8, padding: '5px 12px',
            fontSize: 12, fontWeight: 500, fontFamily: 'inherit',
            transition: 'border-color 0.15s',
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = 'oklch(58% 0.22 25)' }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'oklch(25% 0.04 265 / 0.8)' }}
        >Déconnexion</button>
      </header>

      {/* ── Main content ── */}
      <main style={{
        position: 'fixed',
        [isRtl ? 'right' : 'left']: '60px',
        [isRtl ? 'left' : 'right']: 0,
        top: '56px',
        bottom: 0,
        overflow: 'auto',
        zIndex: 1,
        padding: '28px',
      }}>
        {children}
      </main>

      {/* ── Floating chat bubble (all pages except chat) ── */}
      {current !== 'chat' && (
        <button
          onClick={() => onNavigate('chat')}
          title="Q&A"
          aria-label="Ouvrir Q&A"
          style={{
            position: 'fixed', bottom: 24,
            [isRtl ? 'left' : 'right']: 24,
            zIndex: 30,
            width: 56, height: 56, borderRadius: '50%',
            border: 'none', cursor: 'pointer',
            background: 'linear-gradient(135deg, oklch(65% 0.22 265), oklch(55% 0.22 290))',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 8px 24px oklch(40% 0.2 265 / 0.55)',
            transition: 'transform 0.15s, box-shadow 0.15s',
          }}
          onMouseEnter={e => { const b = e.currentTarget as HTMLElement; b.style.transform = 'scale(1.08)'; b.style.boxShadow = '0 12px 32px oklch(40% 0.2 265 / 0.65)' }}
          onMouseLeave={e => { const b = e.currentTarget as HTMLElement; b.style.transform = 'scale(1)'; b.style.boxShadow = '0 8px 24px oklch(40% 0.2 265 / 0.55)' }}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
            stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d={CHAT_ICON} />
          </svg>
        </button>
      )}

      {/* ── ⌘K modal ── */}
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
              borderRadius: 16, overflow: 'hidden',
              boxShadow: '0 24px 80px rgba(0,0,0,0.6)',
            }}
          >
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '14px 20px', borderBottom: '1px solid oklch(25% 0.04 265 / 0.6)',
            }}>
              <span style={{ color: 'var(--text-muted)', fontSize: 16 }}>⌘</span>
              <span style={{ fontSize: 14, color: 'var(--text-muted)' }}>Navigation rapide…</span>
            </div>
            <div style={{ padding: '8px 0' }}>
              {([...NAV_ITEMS, { id: 'chat' as Page, icon: CHAT_ICON, label: 'Q&A' }]).map((item, i) => (
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
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" strokeWidth="1.8"
                    strokeLinecap="round" strokeLinejoin="round">
                    <path d={item.icon} />
                  </svg>
                  <span>{item.label}</span>
                  <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-dim)', fontFamily: "'JetBrains Mono', monospace" }}>
                    ⌘{i + 1}
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
