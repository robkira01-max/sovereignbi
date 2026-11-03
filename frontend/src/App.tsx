import { useState, useEffect } from 'react'
import { LocaleProvider } from './hooks/useLocale'
import { LoginPage } from './pages/LoginPage'
import { ChatPage } from './pages/ChatPage'
import { DashboardPage } from './pages/DashboardPage'
import { UploadPage } from './pages/UploadPage'
import { HomePage } from './pages/HomePage'
import { AppShell, type Page } from './components/AppShell'

function getApiKey(): string {
  if (typeof localStorage === 'undefined') return ''
  return localStorage.getItem('sovereign_api_key') ?? ''
}

function Inner() {
  const [apiKey, setApiKey] = useState(getApiKey)
  const [page, setPage] = useState<Page>('home')

  useEffect(() => {
    const onStorage = () => setApiKey(getApiKey())
    window.addEventListener('storage', onStorage)
    const interval = setInterval(() => setApiKey(getApiKey()), 300)
    return () => {
      window.removeEventListener('storage', onStorage)
      clearInterval(interval)
    }
  }, [])

  if (!apiKey) {
    return <LoginPage onLogin={() => setApiKey(getApiKey())} />
  }

  const handleLogout = () => {
    localStorage.removeItem('sovereign_api_key')
    setApiKey('')
  }

  let content: React.ReactNode
  if (page === 'home')            content = <HomePage onNavigate={setPage} />
  else if (page === 'chat')       content = <ChatPage />
  else if (page === 'dashboards') content = <DashboardPage />
  else if (page === 'data')       content = <UploadPage />
  else                            content = <HomePage onNavigate={setPage} />

  return (
    <AppShell current={page} onNavigate={setPage} onLogout={handleLogout}>
      {content}
    </AppShell>
  )
}

export default function App() {
  return (
    <LocaleProvider>
      <Inner />
    </LocaleProvider>
  )
}
