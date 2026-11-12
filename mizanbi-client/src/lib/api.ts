// Couche API MizanBI / SovereignBI.
// VITE_API_BASE vide (par défaut) => mode démo, aucune requête réseau.
// Aucune clé API, aucun token, aucun mot de passe en dur ici : l'authentification
// se fait par POST /auth/login, le token est stocké en sessionStorage (mizan_token),
// ou, à défaut, une clé d'API injectée au runtime (window.__MIZAN_API_KEY__).

export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') || ''

export const isApiConfigured = (): boolean => API_BASE.length > 0

export function authHeaders(): Record<string, string> {
  // Le token de session (Bearer) a priorité : le backend rejette en 401 une requête
  // portant une X-Api-Key invalide même si le Bearer est valide, donc on n'envoie
  // jamais les deux. La clé runtime n'est jamais codée en dur ; son rôle
  // (viewer/editor) est celui de la clé fournie par l'administrateur.
  const token = typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('mizan_token') : null
  if (token && token !== 'demo') return { Authorization: `Bearer ${token}` }
  const runtimeKey = (typeof window !== 'undefined' && (window as unknown as { __MIZAN_API_KEY__?: string }).__MIZAN_API_KEY__) || ''
  return runtimeKey ? { 'X-Api-Key': runtimeKey } : {}
}

/** HTTP error with the status and, when the backend sent one, its FastAPI `detail` string. */
export class ApiError extends Error {
  constructor(public status: number, public detail?: string) {
    super(`HTTP ${status}`)
    this.name = 'ApiError'
  }
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  if (!isApiConfigured()) throw new Error('API non configurée (VITE_API_BASE vide)')
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init.headers as Record<string, string> | undefined) },
  })
  if (!res.ok) {
    let detail: string | undefined
    try {
      const body = (await res.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
    } catch { /* non-JSON error body */ }
    throw new ApiError(res.status, detail)
  }
  return res
}

export async function apiJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, init)
  return (await res.json()) as T
}

export interface ChatResponse {
  answer: string
  sql?: string
  columns?: string[]
  rows?: (string | number)[][]
  data?: { columns?: string[]; rows?: (string | number)[][] }
  confidence?: string
}

export async function postChat(question: string, history: { role: string; content: string }[], useData: boolean): Promise<ChatResponse> {
  // Le handoff documente POST /chat ; l'OpenAPI expose /api/v1/chatbot et /ask.
  // On essaie /api/v1/chatbot d'abord, puis /ask en repli.
  try {
    return await apiJson<ChatResponse>('/api/v1/chatbot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, history, use_data_pipeline: useData }),
    })
  } catch {
    return await apiJson<ChatResponse>('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, history, use_data_pipeline: useData }),
    })
  }
}

export async function login(email: string, password: string): Promise<{ token: string; email: string }> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) throw new Error('login failed')
  const j = (await res.json()) as { token?: string; access_token?: string; email?: string }
  const token = j.token || j.access_token
  if (!token) throw new Error('login failed')
  return { token, email: j.email || email }
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  const res = await apiFetch('/auth/password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  })
  if (res.status !== 204 && !res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: string }
    throw new ApiError(res.status, body.detail)
  }
}

export function getApiBase(): string {
  return API_BASE
}

// ── Dashboard types ───────────────────────────────────────────────────────────

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
  data?: TileData
}

export interface TileData {
  columns: string[]
  rows: unknown[][]
}

// ── Dashboard API methods ─────────────────────────────────────────────────────

export const api = {
  dashboards: () =>
    apiJson<{ dashboards: DashboardSummary[] }>('/dashboards').then(r => r.dashboards),

  getDashboard: (id: string) => apiJson<Dashboard>(`/dashboards/${id}`),

  patchLayout: (id: string, tiles: { id: string; position: number }[]) =>
    apiJson<{ id: string; updated_at: string; order: string[] }>(
      `/dashboards/${id}/layout`,
      { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tiles }) }
    ),

  addTile: (id: string, tile: Omit<Tile, 'position'> & { position?: number }) =>
    apiJson<{ id: string; tile_id: string; updated_at: string }>(
      `/dashboards/${id}/tiles`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(tile) }
    ),

  removeTile: (dashboardId: string, tileId: string) =>
    apiJson<{ id: string; tile_id: string; updated_at: string }>(
      `/dashboards/${dashboardId}/tiles/${tileId}`,
      { method: 'DELETE' }
    ),

  toggleFavorite: (id: string) =>
    apiJson<{ dashboard_id: string; is_favorite: boolean }>(
      `/dashboards/${id}/favorite`,
      { method: 'POST' }
    ),

  setTileNote: (dashboardId: string, tileId: string, note: string) =>
    apiJson<{ dashboard_id: string; tile_id: string; note: string | null; updated_at: string }>(
      `/dashboards/${dashboardId}/tiles/${tileId}/note`,
      { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ note }) }
    ),

  setTileSource: (dashboardId: string, tileId: string, source: string) =>
    apiJson<{ dashboard_id: string; tile_id: string; source: string | null; updated_at: string }>(
      `/dashboards/${dashboardId}/tiles/${tileId}/source`,
      { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source }) }
    ),

  setDashboardTags: (dashboardId: string, tags: string[]) =>
    apiJson<{ dashboard_id: string; tags: string[]; updated_at: string }>(
      `/dashboards/${dashboardId}/tags`,
      { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tags }) }
    ),
}
