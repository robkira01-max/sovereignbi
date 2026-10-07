import { LoginPage } from './pages/LoginPage'
import { ChatPage } from './pages/ChatPage'
import { DashboardPage } from './pages/DashboardPage'
import { UploadPage } from './pages/UploadPage'
import { ApiKeyGuard } from './components/ApiKeyGuard'
import { NavBar } from './components/NavBar'

const path = typeof window !== 'undefined' ? window.location.pathname : '/chat'

export default function App() {
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
