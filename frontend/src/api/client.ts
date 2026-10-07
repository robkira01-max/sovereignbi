const BASE = (typeof import.meta !== 'undefined' && (import.meta as { env?: { VITE_API_BASE?: string } }).env?.VITE_API_BASE) ?? ''

export function getKey(): string {
  if (typeof sessionStorage === 'undefined') return ''
  return sessionStorage.getItem('sovereign_api_key') ?? ''
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: {
      'X-Api-Key': getKey(),
      'Content-Type': 'application/json',
      ...(init.headers as Record<string, string> ?? {})
    }
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const api = {
  ask: (question: string) =>
    apiFetch<AskResponse>('/ask', { method: 'POST', body: JSON.stringify({ question }) }),

  upload: (file: File): Promise<{ tables: string[] }> => {
    const form = new FormData()
    form.append('file', file)
    return fetch(BASE + '/upload', {
      method: 'POST',
      headers: { 'X-Api-Key': getKey() },
      body: form
    }).then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json() })
  },

  dashboards: () => apiFetch<Dashboard[]>('/dashboards'),
  getDashboard: (id: string) => apiFetch<Dashboard>(`/dashboards/${id}`),
  health: () => apiFetch<{ status: string }>('/health'),
}

export interface AskResponse {
  sql: string
  columns: string[]
  rows: unknown[][]
  answer: string
  error: string | null
  attempts: number
  confidence: { score: number; label: string; explanation: string } | null
}

export interface Dashboard {
  id: string
  title: string
  tiles: Tile[]
}

export interface Tile {
  id: string
  type: string
  title: string
  sql_pinned?: string
}
