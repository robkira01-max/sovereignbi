import { LocaleProvider } from './hooks/useLocale'
import { LoginPage } from './pages/LoginPage'
import { ChatPage } from './pages/ChatPage'
import { DashboardPage } from './pages/DashboardPage'
import { UploadPage } from './pages/UploadPage'
import { ApiKeyGuard } from './components/ApiKeyGuard'
import { NavBar } from './components/NavBar'

// Strip the Vite base prefix so route comparisons work regardless of mount point.
// import.meta.env.BASE_URL is '/app/' in production, '/' in dev.
const BASE = import.meta.env.BASE_URL ?? '/'
const rawPath = typeof window !== 'undefined' ? window.location.pathname : BASE + 'chat'
const path = (() => {
  const base = BASE.endsWith('/') ? BASE.slice(0, -1) : BASE  // '/app'
  return rawPath.startsWith(base) ? rawPath.slice(base.length) || '/' : rawPath
})()

function Inner() {
  if (path === '/login' || path === '/') {
    return <LoginPage />
  }

  let page
  if (path === '/chat') page = <ChatPage />
  else if (path === '/dashboards') page = <DashboardPage />
  else if (path === '/upload') page = <UploadPage />
  else page = <ChatPage />

  return (
    <ApiKeyGuard>
      <div style={{ minHeight: '100vh', fontFamily: 'system-ui, sans-serif' }}>
        <NavBar currentPath={path} />
        {page}
      </div>
    </ApiKeyGuard>
  )
}

export default function App() {
  return (
    <LocaleProvider>
      <Inner />
    </LocaleProvider>
  )
}
