// Couche API MizanBI / SovereignBI.
// VITE_API_BASE vide (par défaut) => mode démo, aucune requête réseau.
// Aucune clé API, aucun token, aucun mot de passe en dur ici : l'authentification
// se fait par POST /auth/login, le token est stocké en localStorage (mizan_token),
// et les en-têtes X-Api-Key viewer/editor sont fournis au runtime par l'administrateur.

export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') || ''

export const isApiConfigured = (): boolean => API_BASE.length > 0

export function authHeaders(write = false): Record<string, string> {
  // La clé API n'est jamais codée en dur : elle peut être injectée au runtime
  // via une variable globale (par ex. window.__MIZAN_API_KEY__), sinon les
  // appels authentifiés passent par le token de session (Bearer).
  const runtimeKey = (typeof window !== 'undefined' && (window as unknown as { __MIZAN_API_KEY__?: string }).__MIZAN_API_KEY__) || ''
  const headers: Record<string, string> = {}
  if (runtimeKey) headers['X-Api-Key'] = write ? 'editor' : 'viewer'
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('mizan_token') : null
  if (token && token !== 'demo') headers['Authorization'] = `Bearer ${token}`
  return headers
}

export async function apiFetch(path: string, init: RequestInit = {}, write = false): Promise<Response> {
  if (!isApiConfigured()) throw new Error('API non configurée (VITE_API_BASE vide)')
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...authHeaders(write), ...(init.headers as Record<string, string> | undefined) },
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res
}

export async function apiJson<T>(path: string, init: RequestInit = {}, write = false): Promise<T> {
  const res = await apiFetch(path, init, write)
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
  return { token: j.token || j.access_token || '', email: j.email || email }
}
