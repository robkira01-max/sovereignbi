import { useState, useEffect } from 'react'
import { LocaleProvider } from './hooks/useLocale'
import { LoginPage } from './pages/LoginPage'
import { ChatPage } from './pages/ChatPage'
import { DashboardPage } from './pages/DashboardPage'
import { UploadPage } from './pages/UploadPage'
import { HomePage } from './pages/HomePage'
import { ScrollyPage } from './pages/ScrollyPage'
import { AppShell, type Page } from './components/AppShell'

function getToken(): string {
  if (typeof localStorage === 'undefined') return ''
  return localStorage.getItem('mizan_token') ?? ''
}

function getEmail(): string {
  if (typeof localStorage === 'undefined') return ''
  return localStorage.getItem('mizan_email') ?? ''
}

function Inner() {
  const [token, setToken]       = useState(getToken)
  const [userEmail, setUserEmail] = useState(getEmail)
  const [page, setPage]         = useState<Page>('home')

  useEffect(() => {
    const sync = () => { setToken(getToken()); setUserEmail(getEmail()) }
    window.addEventListener('storage', sync)
    const interval = setInterval(sync, 300)
    return () => { window.removeEventListener('storage', sync); clearInterval(interval) }
  }, [])

  if (!token) {
    return <LoginPage onLogin={(email) => { setToken(getToken()); setUserEmail(email) }} />
  }

  const handleLogout = () => {
    localStorage.removeItem('mizan_token')
    localStorage.removeItem('mizan_email')
    setToken('')
    setUserEmail('')
  }

  let content: React.ReactNode
  if (page === 'home')            content = <HomePage onNavigate={setPage} />
  else if (page === 'chat')       content = <ChatPage />
  else if (page === 'dashboards') content = <DashboardPage />
  else if (page === 'data')       content = <UploadPage />
  else if (page === 'scrolly')    content = <ScrollyPage onNavigate={setPage} />
  else                            content = <HomePage onNavigate={setPage} />

  return (
    <AppShell current={page} onNavigate={setPage} onLogout={handleLogout} userEmail={userEmail}>
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
