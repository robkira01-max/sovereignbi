import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { I18N, LANGS, dirOf, type Lang } from './lib/i18n'
import { DEMO_USER } from './data/demo'
import { isApiConfigured } from './lib/api'
import { DEMO_ME, createAccountsService, type Me } from './lib/accounts'
import { THEME_LIST, THEME_MODE_KEY, applyTheme, loadThemeMode, resolveTheme, type IndicatorId, type ThemeId, type ThemeMode } from './lib/theme'
import LoginPage from './pages/Login'
import HomePage from './pages/Home'
import ChatPage from './pages/Chat'
import DashboardsPage from './pages/Dashboards'
import ImportPage from './pages/Import'
import SigPage from './pages/Sig'
import BulletinsPage from './pages/Bulletins'
import CertificatePage from './pages/Certificate'
import CanadaPage from './pages/Canada'
import CanadaNationalPage from './pages/CanadaNational'
import AncientMapsPage from './pages/AncientMaps'
import BiePage from './pages/Bie'
import BcdPage from './pages/Bcd'
import GeoAIPage from './pages/GeoAI'
import AdminPage from './pages/Admin'
import PrivacyPage from './pages/Privacy'
import TermsPage from './pages/Terms'
import ChangePasswordModal from './components/ChangePasswordModal'
import CookieBanner, { useCookieConsent } from './components/CookieBanner'

export type Page = 'home' | 'dash' | 'upload' | 'sig' | 'bulletins' | 'cert' | 'canada' | 'canadanat' | 'ancient' | 'bie' | 'bcd' | 'geoai' | 'admin' | 'privacy' | 'terms'
export type View = 'all' | 'bi' | 'sig'

const NAV: { page: Page; label: (t: (typeof I18N)['fr']) => string; icon: string }[] = [
  { page: 'home', label: (t) => t.home, icon: 'M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM9 22V12h6v10' },
  { page: 'dash', label: (t) => t.dashboards, icon: 'M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z' },
  { page: 'sig', label: (t) => t.sig, icon: 'M9 20l-5.5-2.5v-13L9 7l6-2.5L20.5 7v13L15 17.5 9 20zM9 7v13M15 4.5v13' },
  { page: 'ancient', label: (t) => t.ancientMaps, icon: 'M12 2l9 5-9 5-9-5 9-5zM3 12l9 5 9-5M3 17l9 5 9-5' },
  { page: 'upload', label: (t) => t.import, icon: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12' },
  { page: 'bulletins', label: (t) => t.bulletins, icon: 'M4 19.5A2.5 2.5 0 0 1 6.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z' },
  { page: 'cert', label: (t) => t.certificate, icon: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z' },
  { page: 'canada', label: (t) => t.canada, icon: 'M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6' },
  { page: 'canadanat', label: (t) => t.canadaNational, icon: 'M3 3h18v18H3zM3 9h18M9 21V9' },
  { page: 'bie', label: (t) => t.bie, icon: 'M3 21h18M6 21V11M11 21V4M16 21v-8M21 21V8' },
  { page: 'bcd', label: (t) => t.bcd, icon: 'M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6' },
  { page: 'admin', label: (t) => t.admin.title, icon: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75' },
  { page: 'geoai', label: (t) => t.geoai.title, icon: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z' },
]

export default function App() {
  const [lang, setLang] = useState<Lang>('fr')
  const [token, setToken] = useState<string | null>(() => {
    const tk = sessionStorage.getItem('mizan_token')
    // Un token « demo » périmé n'ouvre pas de session quand l'API est configurée.
    return tk === 'demo' && isApiConfigured() ? null : tk
  })
  const [email, setEmail] = useState<string>(() => localStorage.getItem('mizan_email') || '')
  // P-032 — Nom affiché : Robleh Hassan en mode démo (DEMO_USER), sinon l'email de connexion.
  const [userName, setUserName] = useState<string>(() => localStorage.getItem('mizan_user_name') || '')
  const [page, setPage] = useState<Page>('home')
  const [view, setView] = useState<View>('all')
  // P-028 : thème dynamique. Auto = suit la page et l'indicateur ; manuel = fixe.
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => loadThemeMode())
  const [cookieConsent, setCookieConsent] = useCookieConsent()
  const [showCookieBanner, setShowCookieBanner] = useState(cookieConsent === null)
  const [indicator, setIndicator] = useState<IndicatorId>('unemployment')
  const [themeMenuOpen, setThemeMenuOpen] = useState(false)
  const themeMenuRef = useRef<HTMLDivElement>(null)
  const [showChangePwd, setShowChangePwd] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [chatMounted, setChatMounted] = useState(false)

  const t = I18N[lang]

  // P-038 — identité/rôle de l'utilisateur connecté : l'écran Comptes n'est proposé qu'aux admins
  // (le serveur reste l'autorité : /auth/users* refuse tout autre rôle).
  const accounts = useMemo(() => createAccountsService(), [])
  const [me, setMe] = useState<Me | null>(null)
  const refreshMe = useCallback(() => {
    if (token === 'demo') { setMe(DEMO_ME); return }
    if (!token || !isApiConfigured()) { setMe(null); return }
    accounts.me().then(setMe).catch(() => setMe(null))
  }, [token, accounts])
  useEffect(() => { refreshMe() }, [refreshMe])
  useEffect(() => { if (page === 'admin' && me && me.role !== 'admin') setPage('home') }, [page, me])

  // Appliqué pendant le rendu (pas en effet différé) : les pages enfants lisent
  // le thème courant via currentTheme() dans le même rendu, donc la carte et
  // les KPI changent de couleurs en même temps que le fond.
  const resolvedThemeId = resolveTheme(themeMode, page)
  const resolvedTheme = applyTheme(resolvedThemeId, indicator)

  useEffect(() => {
    if (!themeMenuOpen) return
    const onClick = (e: MouseEvent) => {
      if (themeMenuRef.current && !themeMenuRef.current.contains(e.target as Node)) setThemeMenuOpen(false)
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setThemeMenuOpen(false) }
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onClick); document.removeEventListener('keydown', onKey) }
  }, [themeMenuOpen])

  const changeThemeMode = (m: ThemeMode) => {
    setThemeMode(m)
    localStorage.setItem(THEME_MODE_KEY, m)
    setThemeMenuOpen(false)
  }

  useEffect(() => {
    document.documentElement.lang = lang
    document.documentElement.dir = dirOf(lang)
  }, [lang])

  const go = (p: string) => {
    setPage(p as Page)
    if (p === 'sig') { setView('sig') }
    if (p === 'ancient') { setView('sig') }
    if (p === 'home' || p === 'dash' || p === 'upload' || p === 'bulletins' || p === 'cert' || p === 'canada' || p === 'canadanat' || p === 'bie' || p === 'bcd' || p === 'geoai' || p === 'admin' || p === 'privacy' || p === 'terms') setView((v) => (v === 'sig' ? 'bi' : v))
    window.scrollTo(0, 0)
  }

  const enter = (tk: string, em: string) => {
    const name = tk === 'demo' ? DEMO_USER.name : em
    sessionStorage.setItem('mizan_token', tk)
    localStorage.setItem('mizan_email', em)
    localStorage.setItem('mizan_user_name', name)
    setToken(tk)
    setEmail(em)
    setUserName(name)
    setPage('home')
  }

  const logout = () => {
    sessionStorage.removeItem('mizan_token')
    localStorage.removeItem('mizan_email')
    localStorage.removeItem('mizan_user_name')
    setToken(null)
    setEmail('')
    setUserName('')
    setPage('home')
  }

  if (!token) {
    return (
      <div dir={dirOf(lang)}>
        <LoginPage t={t} lang={lang} setLang={setLang} onEnter={enter} />
      </div>
    )
  }

  const pageTitle: Record<Page, string> = { home: t.home, dash: t.dashboards, upload: t.import, sig: t.sig, bulletins: t.bulletins, cert: t.certificate, canada: t.canada, canadanat: t.canadaNational, ancient: t.ancientMaps, bie: t.bie, bcd: t.bcd, geoai: t.geoai.title, admin: t.admin.title, privacy: t.privacy.title, terms: t.terms.title }
  const showBi = view !== 'sig'
  const showSig = view !== 'bi'

  return (
    <div dir={dirOf(lang)} className="app">
      <nav className="sidebar" aria-label="Navigation principale">
        <div className="logo">M</div>
        {NAV.filter((n) => n.page !== 'admin' || me?.role === 'admin').map((n) => (
          <button key={n.page} title={n.label(t)} aria-label={n.label(t)} onClick={() => go(n.page)} className={`nav-btn${page === n.page ? ' active' : ''}`}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={n.icon} /></svg>
          </button>
        ))}
      </nav>
      <header className="topbar">
        <div className="topbar-title">{pageTitle[page]}</div>
        <div className="topbar-right">
          <div className="view-switch" role="tablist" aria-label="Volets">
            <button className={view === 'all' ? 'active' : ''} onClick={() => setView('all')}>{t.overview}</button>
            <button className={view === 'bi' ? 'active' : ''} onClick={() => { setView('bi'); if (page === 'sig') setPage('home') }}>{t.voletBi}</button>
            <button className={view === 'sig' ? 'active' : ''} onClick={() => { setView('sig'); setPage('sig') }}>{t.voletSig}</button>
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            {LANGS.map((l) => (
              <button key={l} onClick={() => setLang(l)} className={`lang-btn${lang === l ? ' active' : ''}`}>{l.toUpperCase()}</button>
            ))}
          </div>
          <div ref={themeMenuRef} style={{ position: 'relative' }}>
            <button className="btn-ghost theme-btn" onClick={() => setThemeMenuOpen((o) => !o)} aria-haspopup="menu" aria-expanded={themeMenuOpen} aria-label={t.theme} title={t.theme}>
              <span className="theme-swatch" style={{ background: resolvedTheme.swatch[0] }} />
              <span className="theme-swatch" style={{ background: resolvedTheme.swatch[1] }} />
              <span>{themeMode === 'auto' ? `${t.themeAuto} · ${resolvedTheme.label}` : resolvedTheme.label}</span>
            </button>
            {themeMenuOpen && (
              <div role="menu" aria-label={t.theme} className="theme-menu">
                <button role="menuitemradio" aria-checked={themeMode === 'auto'} className={`theme-item${themeMode === 'auto' ? ' active' : ''}`} onClick={() => changeThemeMode('auto')}>
                  <span className="theme-swatch" style={{ background: 'linear-gradient(135deg, oklch(65% 0.22 265) 50%, oklch(68% 0.18 155) 50%)' }} />
                  <span className="theme-swatch" style={{ background: 'linear-gradient(135deg, oklch(62% 0.16 190) 50%, oklch(72% 0.18 55) 50%)' }} />
                  <span>{t.themeAuto}</span>
                  <span className="muted" style={{ marginInlineStart: 'auto' }}>Djibouti → Teal/Ocre · Canada → Violet/Vert</span>
                </button>
                {THEME_LIST.map((th) => (
                  <button key={th.id} role="menuitemradio" aria-checked={themeMode === th.id} className={`theme-item${themeMode === th.id ? ' active' : ''}`} onClick={() => changeThemeMode(th.id as ThemeId)}>
                    <span className="theme-swatch" style={{ background: th.swatch[0] }} />
                    <span className="theme-swatch" style={{ background: th.swatch[1] }} />
                    <span>{th.label}</span>
                    {themeMode === th.id && <span style={{ marginInlineStart: 'auto' }}>✓</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }} title={token === 'demo' ? t.demoAccount : email}>
            <span aria-hidden style={{ width: 30, height: 30, borderRadius: '50%', background: 'linear-gradient(135deg, oklch(65% 0.22 265), oklch(68% 0.18 155))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 12, color: '#070711' }}>
              {token === 'demo' ? DEMO_USER.initials : (userName || email).slice(0, 2).toUpperCase()}
            </span>
            <span style={{ fontSize: 13, fontWeight: 600 }}>{userName || email}</span>
          </span>
          {token !== 'demo' && (
            <button onClick={() => setShowChangePwd(true)} className="btn-ghost" style={{ padding: '5px 12px' }} title={t.changePwd.title}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            </button>
          )}
          <button onClick={logout} className="btn-ghost" style={{ padding: '5px 12px' }}>{t.logout}</button>
        </div>
      </header>
      {showChangePwd && (
        <ChangePasswordModal
          t={t}
          service={accounts}
          isDemo={token === 'demo'}
          onClose={() => setShowChangePwd(false)}
        />
      )}
      <main>
        {page === 'home' && (
          <>
            {showBi && <HomePage t={t} go={go} />}
            {showSig && (
              <div style={{ marginTop: showBi ? 28 : 0 }}>
                <SigPage t={t} onIndicator={setIndicator} />
              </div>
            )}
          </>
        )}
        {page === 'dash' && showBi && <DashboardsPage t={t} />}
        {page === 'upload' && showBi && <ImportPage t={t} />}
        {page === 'bulletins' && showBi && <BulletinsPage t={t} />}
        {page === 'cert' && showBi && <CertificatePage t={t} />}
        {page === 'canada' && showBi && <CanadaPage t={t} onIndicator={setIndicator} />}
        {page === 'canadanat' && showBi && <CanadaNationalPage t={t} />}
        {page === 'bie' && showBi && <BiePage t={t} />}
        {page === 'bcd' && showBi && <BcdPage t={t} />}
        {page === 'geoai' && showBi && <GeoAIPage t={t} lang={lang} go={go} />}
        {page === 'admin' && showBi && <AdminPage t={t} lang={lang} service={accounts} me={me} onSelfChanged={refreshMe} />}
        {page === 'ancient' && <AncientMapsPage t={t} />}
        {page === 'sig' && <SigPage t={t} onIndicator={setIndicator} onAncient={() => go('ancient')} />}
        {page === 'privacy' && <PrivacyPage t={t} go={go} />}
        {page === 'terms' && <TermsPage t={t} go={go} />}
      </main>
      <footer style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', fontSize: 12, color: 'var(--muted)', display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <span>© {new Date().getFullYear()} MizanBI</span>
        <button onClick={() => go('privacy')} style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 12, textDecoration: 'underline', padding: 0 }}>{t.footer.privacy}</button>
        <button onClick={() => go('terms')} style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 12, textDecoration: 'underline', padding: 0 }}>{t.footer.terms}</button>
      </footer>
      {chatOpen && <div className="chat-drawer-overlay" onClick={() => setChatOpen(false)} aria-hidden="true" />}
      <aside
        className={`chat-drawer${chatOpen ? ' chat-drawer--open' : ''}`}
        aria-label={t.chat}
        aria-hidden={!chatOpen}
      >
        <div className="chat-drawer-header">
          <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>ChatBI</span>
          <button
            onClick={() => setChatOpen(false)}
            className="btn-ghost"
            style={{ padding: '5px 10px' }}
            aria-label="Fermer"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="chat-drawer-body">
          {chatMounted && (showBi
            ? <ChatPage t={t} />
            : <p className="muted" style={{ padding: 16 }}>ChatBI — {t.voletBi}. {t.overview}.</p>
          )}
        </div>
      </aside>
      <button
        onClick={() => { setChatOpen(o => !o); setChatMounted(true) }}
        aria-label={chatOpen ? 'Fermer ChatBI' : t.chatBubble}
        title={chatOpen ? 'Fermer ChatBI' : t.chatBubble}
        className="chat-bubble"
      >
        {chatOpen ? (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        )}
      </button>
      {showCookieBanner && (
        <CookieBanner
          t={t}
          onAccept={() => { setCookieConsent(true); setShowCookieBanner(false) }}
          onDecline={() => { setCookieConsent(false); setShowCookieBanner(false) }}
        />
      )}
    </div>
  )
}
