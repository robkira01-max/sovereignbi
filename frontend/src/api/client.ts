const _env = import.meta.env as Record<string, string | undefined>
const _PROD_API = 'https://sovereignbi-api.147-5-126-188.sslip.io'
const BASE = (_env.VITE_API_BASE ?? _env.VITE_API_URL ?? (typeof window !== 'undefined' && window.location.hostname !== 'localhost' ? _PROD_API : '')).replace(/\/$/, '')

export function getKey(): string {
  if (typeof localStorage === 'undefined') return ''
  return localStorage.getItem('mizan_api_key') ?? ''
}

export function getApiBase(): string {
  return BASE
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const key = getKey()
  const res = await fetch(BASE + path, {
    ...init,
    headers: {
      'X-Api-Key': key,
      'Authorization': key ? `Bearer ${key}` : '',
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

  chat: (question: string, history: ChatTurn[] = [], useDataPipeline = true) =>
    apiFetch<ChatResponse>('/api/v1/chatbot', {
      method: 'POST',
      body: JSON.stringify({ question, history, use_data_pipeline: useDataPipeline }),
    }),

  upload: (file: File): Promise<{ tables: string[] }> => {
    const key = getKey()
    const form = new FormData()
    form.append('file', file)
    return fetch(BASE + '/upload', {
      method: 'POST',
      headers: { 'X-Api-Key': key, 'Authorization': key ? `Bearer ${key}` : '' },
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

  toggleFavorite: (id: string) =>
    apiFetch<{ dashboard_id: string; is_favorite: boolean }>(
      `/dashboards/${id}/favorite`,
      { method: 'POST' }
    ),

  setTileNote: (dashboardId: string, tileId: string, note: string) =>
    apiFetch<{ dashboard_id: string; tile_id: string; note: string | null; updated_at: string }>(
      `/dashboards/${dashboardId}/tiles/${tileId}/note`,
      { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ note }) }
    ),

  setTileSource: (dashboardId: string, tileId: string, source: string) =>
    apiFetch<{ dashboard_id: string; tile_id: string; source: string | null; updated_at: string }>(
      `/dashboards/${dashboardId}/tiles/${tileId}/source`,
      { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source }) }
    ),

  setDashboardTags: (dashboardId: string, tags: string[]) =>
    apiFetch<{ dashboard_id: string; tags: string[]; updated_at: string }>(
      `/dashboards/${dashboardId}/tags`,
      { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tags }) }
    ),

  health: () => apiFetch<{ status: string }>('/health'),
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  answer: string
  mode: 'data' | 'general'
  sql: string | null
  columns: string[]
  rows: unknown[][]
  confidence: { score: number; label: string; explanation: string } | null
  error: string | null
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
  is_favorite?: boolean
  tags?: string[]
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
  options?: Record<string, unknown>
  note?: string | null
  source?: string | null
}
