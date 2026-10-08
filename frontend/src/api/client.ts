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

  dashboards: () =>
    apiFetch<{ dashboards: DashboardSummary[] }>('/dashboards').then(r => r.dashboards),
  getDashboard: (id: string) => apiFetch<Dashboard>(`/dashboards/${id}`),

  patchLayout: (id: string, tiles: { id: string; position: number }[]) =>
    apiFetch<{ id: string; updated_at: string; order: string[] }>(
      `/dashboards/${id}/layout`,
      { method: 'PATCH', body: JSON.stringify({ tiles }) }
    ),

  addTile: (id: string, tile: Omit<Tile, 'position'> & { position?: number }) =>
    apiFetch<{ id: string; tile_id: string; updated_at: string }>(
      `/dashboards/${id}/tiles`,
      { method: 'POST', body: JSON.stringify(tile) }
    ),

  removeTile: (dashboardId: string, tileId: string) =>
    apiFetch<{ id: string; tile_id: string; updated_at: string }>(
      `/dashboards/${dashboardId}/tiles/${tileId}`,
      { method: 'DELETE' }
    ),

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

export interface DashboardSummary {
  id: string
  title: string
  scope: string
  updated_at: string
}

export interface Dashboard {
  id: string
  title: string
  scope: string
  tiles: Tile[]
  theme?: { primary_color?: string; font?: string; logo_url?: string }
}

export interface Tile {
  id: string
  type: string
  title: string
  metric?: string
  sql_pinned?: string
  dimensions?: string[]
  position?: number
}
