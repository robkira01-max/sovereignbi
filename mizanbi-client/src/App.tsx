import { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { I18N, LANGS, dirOf, type Lang, type Dict } from './lib/i18n'
import { DEMO_USER } from './data/demo'
import { isApiConfigured } from './lib/api'
import { DEMO_ME, createAccountsService, type Me } from './lib/accounts'
import { THEME_LIST, THEME_MODE_KEY, applyTheme, loadThemeMode, resolveTheme, type IndicatorId, type ThemeId, type ThemeMode } from './lib/theme'
import LoginPage from './pages/Login'
import LegalPage from './pages/LegalPage'
import TermsGate from './components/TermsGate'
import { acceptTerms, hasAcceptedTerms } from './lib/termsConsent'
import type { LegalKind } from './lib/legalContent'
import { startAnalytics, stopAnalytics } from './lib/analytics'
import { documentTitle } from './lib/pageTitle'
import ChangePasswordModal from './components/ChangePasswordModal'
import CookieBanner, { useCookieConsent } from './components/CookieBanner'

// Pages chargées à la demande : le premier chargement (connexion) ne télécharge plus les graphiques, cartes et jeux de données embarqués.
const HomePage = lazy(() => import('./pages/Home'))
const ChatPage = lazy(() => import('./pages/Chat'))
const DashboardsPage = lazy(() => import('./pages/Dashboards'))
const ImportPage = lazy(() => import('./pages/Import'))
const SigPage = lazy(() => import('./pages/Sig'))
const BulletinsPage = lazy(() => import('./pages/Bulletins'))
const CertificatePage = lazy(() => import('./pages/Certificate'))
const CanadaPage = lazy(() => import('./pages/Canada'))
const CanadaNationalPage = lazy(() => import('./pages/CanadaNational'))
const AncientMapsPage = lazy(() => import('./pages/AncientMaps'))
const BiePage = lazy(() => import('./pages/Bie'))
const BcdPage = lazy(() => import('./pages/Bcd'))
const GeoAIPage = lazy(() => import('./pages/GeoAI'))
const AdminPage = lazy(() => import('./pages/Admin'))

export type Page = 'home' | 'dash' | 'upload' | 'sig' | 'bulletins' | 'cert' | 'canada' | 'canadanat' | 'ancient' | 'bie' | 'bcd' | 'geoai' | 'admin' | 'privacy' | 'terms' | 'legal' | 'cookies'
export type Section = 'home' | 'bi' | 'sig' | 'settings'

function pageSection(p: Page): Section {
  if (p === 'home') return 'home'
  if (['dash', 'bulletins', 'cert', 'upload', 'bie', 'bcd', 'canada', 'canadanat'].includes(p)) return 'bi'
  if (['sig', 'ancient', 'geoai'].includes(p)) return 'sig'
  return 'settings'
}

const SECTION_NAV: { id: Section; getLabel: (t: Dict) => string; icon: string; defaultPage: Page }[] = [
  { id: 'home', getLabel: t => t.home, icon: 'M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM9 22V12h6v10', defaultPage: 'home' },
  { id: 'bi', getLabel: t => t.voletBi, icon: 'M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z', defaultPage: 'dash' },
  { id: 'sig', getLabel: t => t.voletSig, icon: 'M9 20l-5.5-2.5v-13L9 7l6-2.5L20.5 7v13L15 17.5 9 20zM9 7v13M15 4.5v13', defaultPage: 'sig' },
  { id: 'settings', getLabel: t => t.settingsSection, icon: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z', defaultPage: 'privacy' },
]

const BI_PAGES: { page: Page; getLabel: (t: Dict) => string }[] = [
  { page: 'dash', getLabel: t => t.dashboards },
  { page: 'bulletins', getLabel: t => t.bulletins },
  { page: 'cert', getLabel: t => t.certificate },
  { page: 'upload', getLabel: t => t.import },
  { page: 'bie', getLabel: t => t.bie },
  { page: 'bcd', getLabel: t => t.bcd },
  { page: 'canada', getLabel: t => t.canada },
  { page: 'canadanat', getLabel: t => t.canadaNational },
]

const SIG_PAGES: { page: Page; getLabel: (t: Dict) => string }[] = [
  { page: 'sig', getLabel: t => t.sig },
  { page: 'ancient', getLabel: t => t.ancientMaps },
  { page: 'geoai', getLabel: t => t.geoai.title },
]

const SETTINGS_PAGES: { page: Page; getLabel: (t: Dict) => string; adminOnly: boolean }[] = [
  { page: 'admin', getLabel: t => t.admin.title, adminOnly: true },
  { page: 'privacy', getLabel: t => t.privacy.title, adminOnly: false },
  { page: 'terms', getLabel: t => t.terms.title, adminOnly: false },
  { page: 'cookies', getLabel: t => t.cookiesPolicy.title, adminOnly: false },
  { page: 'legal', getLabel: t => t.legalNotice.title, adminOnly: false },
]

export default function App() {
  const [lang, setLang] = useState<Lang>('fr')
  const [token, setToken] = useState<string | null>(() => {
    const tk = sessionStorage.getItem('mizan_token')
    return tk === 'demo' && isApiConfigured() ? null : tk
  })
  const [email, setEmail] = useState<string>(() => localStorage.getItem('mizan_email') || '')
  const [userName, setUserName] = useState<string>(() => localStorage.getItem('mizan_user_name') || '')
  const [page, setPage] = useState<Page>('home')
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => loadThemeMode())
  const [cookieConsent, setCookieConsent] = useCookieConsent()
  const [showCookieBanner, setShowCookieBanner] = useState(cookieConsent === null)
  const [cookieChoice, setCookieChoice] = useState<boolean | null>(cookieConsent)
  const [publicDoc, setPublicDoc] = useState<LegalKind | null>(null)
  // Mesure d'audience : chargée uniquement après consentement ; un retrait arrête le script (rechargement si déjà actif).
  useEffect(() => {
    if (cookieChoice === true) startAnalytics()
    else if (cookieChoice === false && stopAnalytics()) window.location.reload()
  }, [cookieChoice])
  const [termsTick, setTermsTick] = useState(0)
  const [indicator, setIndicator] = useState<IndicatorId>('unemployment')
  const [themeMenuOpen, setThemeMenuOpen] = useState(false)
  const themeMenuRef = useRef<HTMLDivElement>(null)
  const [showChangePwd, setShowChangePwd] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [chatMounted, setChatMounted] = useState(false)

  const t = I18N[lang]
  const section = pageSection(page)
  const pageTitle: Record<Page, string> = { home: t.home, dash: t.dashboards, upload: t.import, sig: t.sig, bulletins: t.bulletins, cert: t.certificate, canada: t.canada, canadanat: t.canadaNational, ancient: t.ancientMaps, bie: t.bie, bcd: t.bcd, geoai: t.geoai.title, admin: t.admin.title, privacy: t.privacy.title, terms: t.terms.title, legal: t.legalNotice.title, cookies: t.cookiesPolicy.title }
  const legalTitles: Record<LegalKind, string> = { privacy: t.privacy.title, terms: t.terms.title, legal: t.legalNotice.title, cookies: t.cookiesPolicy.title }

  // Un titre d'onglet par écran (accessibilité, historique, lecteurs d'écran).
  useEffect(() => {
    document.title = documentTitle(token ? pageTitle[page] : publicDoc ? legalTitles[publicDoc] : null)
  }, [token, page, publicDoc, lang]) // eslint-disable-line react-hooks/exhaustive-deps

  const accounts = useMemo(() => createAccountsService(), [])
  const [me, setMe] = useState<Me | null>(null)
  const refreshMe = useCallback(() => {
    if (token === 'demo') { setMe(DEMO_ME); return }
    if (!token || !isApiConfigured()) { setMe(null); return }
    accounts.me().then(setMe).catch(() => setMe(null))
  }, [token, accounts])
  useEffect(() => { refreshMe() }, [refreshMe])
  useEffect(() => { if (page === 'admin' && me && me.role !== 'admin') setPage('home') }, [page, me])

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
    window.scrollTo(0, 0)
  }

  const goSection = (sid: Section) => {
    if (sid === 'home') { go('home'); return }
    if (sid === 'bi') { go('dash'); return }
    if (sid === 'sig') { go('sig'); return }
    if (sid === 'settings') {
      const first = SETTINGS_PAGES.find(p => !p.adminOnly || me?.role === 'admin')
      go(first?.page ?? 'privacy')
    }
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

  const bannerNode = showCookieBanner && (
    <CookieBanner
      t={t}
      onAccept={() => { setCookieConsent(true); setCookieChoice(true); setShowCookieBanner(false) }}
      onDecline={() => { setCookieConsent(false); setCookieChoice(false); setShowCookieBanner(false) }}
      onPolicy={() => (token ? go('cookies') : setPublicDoc('cookies'))}
    />
  )

  if (!token) {
    return (
      <div dir={dirOf(lang)}>
        {publicDoc
          ? <LegalPage kind={publicDoc} t={t} lang={lang} onBack={() => setPublicDoc(null)} onManageCookies={() => setShowCookieBanner(true)} cookieChoice={cookieChoice} />
          : <LoginPage t={t} lang={lang} setLang={setLang} onEnter={enter} onLegal={setPublicDoc} />}
        {bannerNode}
      </div>
    )
  }


  const subItems = section === 'bi'
    ? BI_PAGES
    : section === 'sig'
    ? SIG_PAGES
    : section === 'settings'
    ? SETTINGS_PAGES.filter(p => !p.adminOnly || me?.role === 'admin')
    : []

  return (
    <div dir={dirOf(lang)} className="app">
      <nav className="sidebar" aria-label="Navigation principale">
        <div className="logo">M</div>
        {SECTION_NAV.map((s) => (
          <button key={s.id} title={s.getLabel(t)} aria-label={s.getLabel(t)} onClick={() => goSection(s.id)} className={`nav-btn${section === s.id ? ' active' : ''}`}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={s.icon} /></svg>
          </button>
        ))}
      </nav>
      <header className="topbar">
        <div className="topbar-title">{pageTitle[page]}</div>
        <div className="topbar-right">
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
        {subItems.length > 0 && (
          <nav aria-label="Sous-navigation" style={{ display: 'flex', gap: 4, padding: '10px 20px', borderBottom: '1px solid var(--border)', background: 'var(--surface)', position: 'sticky', top: 56, zIndex: 9, flexWrap: 'wrap', backdropFilter: 'blur(10px)' }}>
            {subItems.map((item) => (
              <button
                key={item.page}
                onClick={() => go(item.page)}
                className="btn-ghost"
                style={{ fontSize: 13, padding: '5px 14px', ...(page === item.page ? { background: 'var(--brand)', color: '#fff', borderColor: 'transparent' } : {}) }}
              >
                {item.getLabel(t)}
              </button>
            ))}
          </nav>
        )}
        <Suspense fallback={<p role="status" aria-live="polite" className="muted" style={{ padding: 24 }}>{t.admin.loading}</p>}>
        {page === 'home' && <HomePage t={t} go={go} />}
        {page === 'dash' && <DashboardsPage t={t} />}
        {page === 'upload' && <ImportPage t={t} />}
        {page === 'bulletins' && <BulletinsPage t={t} />}
        {page === 'cert' && <CertificatePage t={t} />}
        {page === 'canada' && <CanadaPage t={t} onIndicator={setIndicator} />}
        {page === 'canadanat' && <CanadaNationalPage t={t} />}
        {page === 'bie' && <BiePage t={t} />}
        {page === 'bcd' && <BcdPage t={t} />}
        {page === 'geoai' && <GeoAIPage t={t} lang={lang} go={go} />}
        {page === 'admin' && <AdminPage t={t} lang={lang} service={accounts} me={me} onSelfChanged={refreshMe} />}
        {page === 'ancient' && <AncientMapsPage t={t} />}
        {page === 'sig' && <SigPage t={t} lang={lang} isEditor={me?.role === 'editor' || me?.role === 'admin'} onIndicator={setIndicator} onAncient={() => go('ancient')} />}
        </Suspense>
        {(page === 'privacy' || page === 'terms' || page === 'legal' || page === 'cookies') && (
          <LegalPage kind={page} t={t} lang={lang} onBack={() => go('home')} onManageCookies={() => setShowCookieBanner(true)} cookieChoice={cookieChoice} />
        )}
      </main>
      <footer style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', fontSize: 12, color: 'var(--muted)', display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <span>© {new Date().getFullYear()} MizanBI</span>
        <button onClick={() => go('privacy')} style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 12, textDecoration: 'underline', padding: 0 }}>{t.footer.privacy}</button>
        <button onClick={() => go('terms')} style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 12, textDecoration: 'underline', padding: 0 }}>{t.footer.terms}</button>
        <button onClick={() => go('legal')} style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 12, textDecoration: 'underline', padding: 0 }}>{t.footer.legal}</button>
        <button onClick={() => go('cookies')} style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 12, textDecoration: 'underline', padding: 0 }}>{t.footer.cookies}</button>
        <button onClick={() => setShowCookieBanner(true)} style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 12, textDecoration: 'underline', padding: 0 }}>{t.footer.manageCookies}</button>
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
          {chatMounted && (
            section !== 'sig'
              ? <Suspense fallback={<p role="status" className="muted" style={{ padding: 16 }}>{t.admin.loading}</p>}><ChatPage t={t} /></Suspense>
              : <p className="muted" style={{ padding: 16 }}>ChatBI — {t.voletBi}.</p>
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
      {token && !hasAcceptedTerms(email) && termsTick >= 0 && (
        <TermsGate
          t={t}
          lang={lang}
          onAccept={async () => { await acceptTerms(email, token); setTermsTick(n => n + 1) }}
          onRefuse={logout}
        />
      )}
      {bannerNode}
    </div>
  )
}
