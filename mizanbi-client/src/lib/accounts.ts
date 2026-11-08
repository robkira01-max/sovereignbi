// P-038 — Gestion des comptes (écran administrateur).
// Mode connecté : /auth/users* du backend (admin uniquement, voir app/auth/users_router.py).
// Mode démo (VITE_API_BASE vide) : simulation en mémoire avec des comptes fictifs et les
// mêmes règles que le serveur ; rien n'est persisté ni envoyé.

import { ApiError, apiFetch, apiJson, isApiConfigured } from './api'

export type Role = 'viewer' | 'editor' | 'admin'
export const ROLES: Role[] = ['viewer', 'editor', 'admin']

export interface Account {
  id: number
  email: string
  role: Role
  is_active: boolean
  created_at: string | null
}

export interface Me { id: number; email: string; role: Role }

export const MIN_PASSWORD_CHARS = 12
const MAX_PASSWORD_BYTES = 72 // bcrypt limit

export type AccountErrorCode =
  | 'exists' | 'lastAdmin' | 'notFound' | 'invalidEmail' | 'passwordShort' | 'passwordLong'
  | 'forbidden' | 'unauthorized' | 'busy' | 'network' | 'unknown'

export class AccountsError extends Error {
  constructor(public code: AccountErrorCode, public detail?: string) {
    super(code)
    this.name = 'AccountsError'
  }
}

// ── Validation (miroir de app/auth/security.py : le serveur reste l'autorité) ─

export function normalizeEmail(email: string): string {
  return email.normalize('NFKC').trim().toLowerCase()
}

const EMAIL_RE = /^[^@\s]{1,64}@[^@\s]+\.[^@\s]+$/

/** Returns the normalised address, or throws AccountsError('invalidEmail'). */
export function validateEmail(email: string): string {
  const e = normalizeEmail(email)
  // \p{C}: control/format (zero-width…), \p{Z}: separators — enable look-alike accounts.
  if (e.length > 254 || !EMAIL_RE.test(e) || /[\p{C}\p{Z}]/u.test(e)) throw new AccountsError('invalidEmail')
  return e
}

export function validatePassword(password: string): void {
  if ([...password].length < MIN_PASSWORD_CHARS) throw new AccountsError('passwordShort')
  if (new TextEncoder().encode(password).length > MAX_PASSWORD_BYTES) throw new AccountsError('passwordLong')
}

// ── Service ──────────────────────────────────────────────────────────────────

export interface AccountsService {
  me(): Promise<Me>
  list(): Promise<Account[]>
  create(email: string, password: string, role: Role): Promise<Account>
  update(id: number, patch: { role?: Role; is_active?: boolean }): Promise<Account>
  resetPassword(id: number, password: string): Promise<void>
}

type Context = 'create' | 'update' | 'other'

/** Maps an HTTP failure to a stable code the UI can localise. */
export function mapApiError(e: unknown, ctx: Context = 'other'): AccountsError {
  if (e instanceof AccountsError) return e
  if (!(e instanceof ApiError)) return new AccountsError('network')
  switch (e.status) {
    case 401: return new AccountsError('unauthorized')
    case 403: return new AccountsError('forbidden')
    case 404: return new AccountsError('notFound')
    case 409: return new AccountsError(ctx === 'create' ? 'exists' : 'lastAdmin')
    case 429:
    case 503: return new AccountsError('busy')
    case 422: {
      const d = (e.detail ?? '').toLowerCase()
      if (d.includes('e-mail')) return new AccountsError('invalidEmail')
      if (d.includes('trop court')) return new AccountsError('passwordShort')
      if (d.includes('trop long')) return new AccountsError('passwordLong')
      return new AccountsError('unknown', e.detail)
    }
    default: return new AccountsError('unknown', e.detail)
  }
}

const json = (body: unknown): RequestInit => ({
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export function createApiAccounts(): AccountsService {
  const guard = async <T>(ctx: Context, run: () => Promise<T>): Promise<T> => {
    try { return await run() } catch (e) { throw mapApiError(e, ctx) }
  }
  return {
    me: () => guard('other', () => apiJson<Me>('/auth/me')),
    list: () => guard('other', () => apiJson<Account[]>('/auth/users')),
    create: (email, password, role) =>
      guard('create', () => apiJson<Account>('/auth/users', { method: 'POST', ...json({ email, password, role }) })),
    update: (id, patch) =>
      guard('update', () => apiJson<Account>(`/auth/users/${id}`, { method: 'PATCH', ...json(patch) })),
    resetPassword: (id, password) =>
      guard('other', async () => { await apiFetch(`/auth/users/${id}/password`, { method: 'PUT', ...json({ password }) }) }),
  }
}

// ── Mode démo : comptes fictifs en mémoire ───────────────────────────────────

export const DEMO_ME: Me = { id: 1, email: 'demo@instad.dj', role: 'admin' }

export function createDemoAccounts(): AccountsService {
  let nextId = 5
  const accounts: Account[] = [
    { id: 1, email: DEMO_ME.email, role: 'admin', is_active: true, created_at: '2026-10-01 09:00:00' },
    { id: 2, email: 'direction@exemple.dj', role: 'admin', is_active: true, created_at: '2026-10-03 14:20:00' },
    { id: 3, email: 'analyste@exemple.dj', role: 'editor', is_active: true, created_at: '2026-10-12 08:45:00' },
    { id: 4, email: 'stagiaire@exemple.dj', role: 'viewer', is_active: false, created_at: '2026-10-20 16:10:00' },
  ]
  const tick = () => new Promise<void>((r) => setTimeout(r, 120))
  const find = (id: number) => {
    const a = accounts.find((x) => x.id === id)
    if (!a) throw new AccountsError('notFound')
    return a
  }
  const activeAdmins = (except?: number) => accounts.filter((a) => a.role === 'admin' && a.is_active && a.id !== except).length

  return {
    async me() { await tick(); return { ...DEMO_ME } },
    async list() { await tick(); return accounts.map((a) => ({ ...a })) },
    async create(email, password, role) {
      await tick()
      const e = validateEmail(email)
      validatePassword(password)
      if (accounts.some((a) => a.email === e)) throw new AccountsError('exists')
      const acc: Account = { id: nextId++, email: e, role, is_active: true, created_at: new Date().toISOString().slice(0, 19).replace('T', ' ') }
      accounts.push(acc)
      return { ...acc }
    },
    async update(id, patch) {
      await tick()
      const a = find(id)
      const role = patch.role ?? a.role
      const active = patch.is_active ?? a.is_active
      if (a.role === 'admin' && a.is_active && (role !== 'admin' || !active) && activeAdmins(id) === 0) {
        throw new AccountsError('lastAdmin')
      }
      a.role = role
      a.is_active = active
      return { ...a }
    },
    async resetPassword(id, password) {
      await tick()
      find(id)
      validatePassword(password)
    },
  }
}

export function createAccountsService(): AccountsService {
  return isApiConfigured() ? createApiAccounts() : createDemoAccounts()
}
