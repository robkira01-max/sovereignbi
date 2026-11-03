import { useEffect } from 'react'
import type { ReactNode } from 'react'

export function ApiKeyGuard({ children }: { children: ReactNode }) {
  useEffect(() => {
    const key = localStorage.getItem('sovereign_api_key')
    if (!key) {
      window.location.href = (import.meta.env.BASE_URL ?? '/') + 'login'
    }
  }, [])

  const key = localStorage.getItem('sovereign_api_key')
  if (!key) return null
  return <>{children}</>
}
