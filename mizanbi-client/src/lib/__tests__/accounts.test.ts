// P-038 — couche de données de l'écran administrateur.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  AccountsError, createDemoAccounts, mapApiError, normalizeEmail, validateEmail, validatePassword,
  type AccountErrorCode,
} from '../accounts'
import { ApiError } from '../api'

const code = (fn: () => unknown): string | undefined => {
  try { fn() } catch (e) { return (e as AccountsError).code }
  return undefined
}
const rejectsWith = async (p: Promise<unknown>): Promise<AccountErrorCode | undefined> => {
  try { await p } catch (e) { return (e as AccountsError).code }
  return undefined
}

describe('validateEmail', () => {
  it('normalises case, spaces and compatibility look-alikes', () => {
    expect(validateEmail('  Ops@Example.ORG ')).toBe('ops@example.org')
    expect(validateEmail('Kelvin@example.org')).toBe('kelvin@example.org') // KELVIN SIGN
    expect(normalizeEmail(' A@B.CO ')).toBe('a@b.co')
  })

  it.each(['', 'no-at', 'a@b', '@example.org', 'a@@example.org', 'a b@example.org',
    'a​b@example.org', 'a\tb@example.org', 'a b@example.org', 'ab@exam‍ple.org',
    `${'a'.repeat(250)}@example.org`])('rejects %j', (e) => {
    expect(code(() => validateEmail(e))).toBe('invalidEmail')
  })
})

describe('validatePassword', () => {
  it('requires 12 characters', () => {
    expect(code(() => validatePassword('a'.repeat(11)))).toBe('passwordShort')
    expect(code(() => validatePassword('a'.repeat(12)))).toBeUndefined()
  })

  it('caps at 72 bytes, not 72 characters', () => {
    expect(code(() => validatePassword('é'.repeat(36)))).toBeUndefined() // 72 bytes
    expect(code(() => validatePassword('é'.repeat(37)))).toBe('passwordLong') // 74 bytes
    expect(code(() => validatePassword('a'.repeat(73)))).toBe('passwordLong')
  })

  it('counts characters by code point (emoji are one character)', () => {
    expect(code(() => validatePassword('😀'.repeat(12)))).toBeUndefined() // 12 chars, 48 bytes
    expect(code(() => validatePassword('😀'.repeat(11)))).toBe('passwordShort')
  })
})

describe('mapApiError', () => {
  const map = (status: number, ctx: 'create' | 'update' | 'other', detail?: string) =>
    mapApiError(new ApiError(status, detail), ctx).code

  it.each([
    [401, 'other', 'unauthorized'], [403, 'other', 'forbidden'], [404, 'update', 'notFound'],
    [409, 'create', 'exists'], [409, 'update', 'lastAdmin'], [429, 'other', 'busy'], [503, 'other', 'busy'],
    [500, 'other', 'unknown'],
  ] as const)('%i in %s context -> %s', (status, ctx, expected) => {
    expect(map(status, ctx)).toBe(expected)
  })

  it('reads 422 details from the backend', () => {
    expect(map(422, 'create', 'Adresse e-mail invalide.')).toBe('invalidEmail')
    expect(map(422, 'create', 'Mot de passe trop court (12 caractères minimum).')).toBe('passwordShort')
    expect(map(422, 'create', 'Mot de passe trop long (72 octets maximum).')).toBe('passwordLong')
    expect(mapApiError(new ApiError(422, 'autre'), 'create')).toMatchObject({ code: 'unknown', detail: 'autre' })
  })

  it('treats non-HTTP failures as network errors and keeps AccountsError untouched', () => {
    expect(mapApiError(new TypeError('Failed to fetch')).code).toBe('network')
    const e = new AccountsError('exists')
    expect(mapApiError(e)).toBe(e)
  })
})

describe('API service (requests actually sent)', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    vi.resetModules()
    vi.stubEnv('VITE_API_BASE', 'http://api.test/')
    vi.stubGlobal('localStorage', { getItem: (k: string) => (k === 'mizan_token' ? 'tok123' : null) })
    vi.stubGlobal('window', {})
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })
  afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals() })

  const svc = async () => (await import('../accounts')).createApiAccounts()
  const ok = (body: unknown, status = 200) => ({ ok: true, status, json: async () => body })
  const fail = (status: number, body: unknown = {}) => ({ ok: false, status, json: async () => body })
  const lastCall = () => {
    const [url, init] = fetchMock.mock.calls[fetchMock.mock.calls.length - 1] as [string, RequestInit]
    return { url, init, headers: init.headers as Record<string, string>, body: init.body ? JSON.parse(init.body as string) : undefined }
  }

  it('lists accounts with the Bearer token', async () => {
    fetchMock.mockResolvedValue(ok([{ id: 1 }]))
    expect(await (await svc()).list()).toEqual([{ id: 1 }])
    const c = lastCall()
    expect(c.url).toBe('http://api.test/auth/users')
    expect(c.headers.Authorization).toBe('Bearer tok123')
    expect(c.init.method).toBeUndefined() // GET
  })

  it('creates with POST and a JSON body', async () => {
    fetchMock.mockResolvedValue(ok({ id: 9 }, 201))
    await (await svc()).create('a@b.co', 'long-enough-pw!', 'editor')
    const c = lastCall()
    expect(c.url).toBe('http://api.test/auth/users')
    expect(c.init.method).toBe('POST')
    expect(c.headers['Content-Type']).toBe('application/json')
    expect(c.body).toEqual({ email: 'a@b.co', password: 'long-enough-pw!', role: 'editor' })
  })

  it('updates with PATCH (the method CORS used to block)', async () => {
    fetchMock.mockResolvedValue(ok({ id: 5 }))
    await (await svc()).update(5, { role: 'viewer' })
    const c = lastCall()
    expect(c.url).toBe('http://api.test/auth/users/5')
    expect(c.init.method).toBe('PATCH')
    expect(c.body).toEqual({ role: 'viewer' })
  })

  it('resets a password with PUT and tolerates the empty 204 body', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 204, json: async () => { throw new SyntaxError('empty') } })
    await expect((await svc()).resetPassword(5, 'another-long-pw!')).resolves.toBeUndefined()
    const c = lastCall()
    expect(c.url).toBe('http://api.test/auth/users/5/password')
    expect(c.init.method).toBe('PUT')
    expect(c.body).toEqual({ password: 'another-long-pw!' })
  })

  it('reads /auth/me', async () => {
    fetchMock.mockResolvedValue(ok({ id: 1, email: 'a@b.co', role: 'admin' }))
    expect((await (await svc()).me()).role).toBe('admin')
    expect(lastCall().url).toBe('http://api.test/auth/me')
  })

  it('maps failures with the right context', async () => {
    const s = await svc()
    fetchMock.mockResolvedValue(fail(409, { detail: 'Un compte existe déjà avec cette adresse.' }))
    expect(await rejectsWith(s.create('a@b.co', 'long-enough-pw!', 'viewer'))).toBe('exists')
    fetchMock.mockResolvedValue(fail(409, { detail: 'Impossible : ce serait le dernier administrateur actif.' }))
    expect(await rejectsWith(s.update(1, { role: 'viewer' }))).toBe('lastAdmin')
    fetchMock.mockResolvedValue(fail(403))
    expect(await rejectsWith(s.list())).toBe('forbidden')
    fetchMock.mockResolvedValue(fail(422, { detail: 'Mot de passe trop court (12 caractères minimum).' }))
    expect(await rejectsWith(s.create('a@b.co', 'x', 'viewer'))).toBe('passwordShort')
    fetchMock.mockResolvedValue({ ok: false, status: 502, json: async () => { throw new SyntaxError('html') } })
    expect(await rejectsWith(s.list())).toBe('unknown')
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
    expect(await rejectsWith(s.list())).toBe('network')
  })
})

describe('demo service (same rules as the server, nothing persisted)', () => {
  it('starts with fictional accounts and a demo admin', async () => {
    const s = createDemoAccounts()
    const list = await s.list()
    expect(list.length).toBeGreaterThanOrEqual(4)
    expect(list.every((a) => a.email.endsWith('@exemple.dj') || a.email === 'demo@instad.dj')).toBe(true)
    expect((await s.me()).role).toBe('admin')
  })

  it('instances are isolated', async () => {
    const a = createDemoAccounts(), b = createDemoAccounts()
    await a.create('new@exemple.dj', 'long-enough-pw!', 'viewer')
    expect((await a.list()).length).toBe((await b.list()).length + 1)
  })

  it('creates normalised accounts with increasing ids; rejects duplicates case-insensitively', async () => {
    const s = createDemoAccounts()
    const a = await s.create('  New@Exemple.DJ ', 'long-enough-pw!', 'editor')
    expect(a).toMatchObject({ email: 'new@exemple.dj', role: 'editor', is_active: true })
    const b = await s.create('other@exemple.dj', 'long-enough-pw!', 'viewer')
    expect(b.id).toBe(a.id + 1)
    expect(await rejectsWith(s.create('NEW@exemple.dj', 'long-enough-pw!', 'viewer'))).toBe('exists')
  })

  it('validates input like the server', async () => {
    const s = createDemoAccounts()
    expect(await rejectsWith(s.create('not-an-email', 'long-enough-pw!', 'viewer'))).toBe('invalidEmail')
    expect(await rejectsWith(s.create('a@exemple.dj', 'short', 'viewer'))).toBe('passwordShort')
    expect(await rejectsWith(s.create('a@exemple.dj', 'é'.repeat(40), 'viewer'))).toBe('passwordLong')
    expect((await s.list()).some((a) => a.email === 'a@exemple.dj')).toBe(false)
  })

  it('updates role and activation', async () => {
    const s = createDemoAccounts()
    expect(await s.update(3, { role: 'viewer' })).toMatchObject({ id: 3, role: 'viewer' })
    expect(await s.update(3, { is_active: false })).toMatchObject({ is_active: false, role: 'viewer' })
    expect(await rejectsWith(s.update(999, { role: 'viewer' }))).toBe('notFound')
  })

  it('never removes the last active admin', async () => {
    const s = createDemoAccounts()
    await s.update(2, { role: 'editor' }) // two admins -> one left
    expect(await rejectsWith(s.update(1, { role: 'viewer' }))).toBe('lastAdmin')
    expect(await rejectsWith(s.update(1, { is_active: false }))).toBe('lastAdmin')
    expect((await s.list()).find((a) => a.id === 1)).toMatchObject({ role: 'admin', is_active: true })
    await s.update(1, { role: 'admin' }) // no-op is fine
  })

  it('does not count inactive admins', async () => {
    const s = createDemoAccounts()
    await s.update(2, { is_active: false })
    expect(await rejectsWith(s.update(1, { role: 'viewer' }))).toBe('lastAdmin')
  })

  it('resets passwords with validation and a not-found check', async () => {
    const s = createDemoAccounts()
    await expect(s.resetPassword(3, 'another-long-pw!')).resolves.toBeUndefined()
    expect(await rejectsWith(s.resetPassword(3, 'short'))).toBe('passwordShort')
    expect(await rejectsWith(s.resetPassword(999, 'another-long-pw!'))).toBe('notFound')
  })

  it('changePassword validates new password strength', async () => {
    const s = createDemoAccounts()
    await expect(s.changePassword('any-old-pwd', 'new-strong-pw!')).resolves.toBeUndefined()
    expect(await rejectsWith(s.changePassword('any-old-pwd', 'short'))).toBe('passwordShort')
    expect(await rejectsWith(s.changePassword('any-old-pwd', 'é'.repeat(40)))).toBe('passwordLong')
  })
})

describe('mapApiError — changePwd context', () => {
  it('maps 403 to wrongPassword', () => {
    expect(mapApiError(new ApiError(403, 'wrong'), 'changePwd').code).toBe('wrongPassword')
  })

  it('still maps 403 to forbidden in other contexts', () => {
    expect(mapApiError(new ApiError(403, ''), 'other').code).toBe('forbidden')
    expect(mapApiError(new ApiError(403, ''), 'create').code).toBe('forbidden')
  })
})

describe('API service — changePassword', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    vi.resetModules()
    vi.stubEnv('VITE_API_BASE', 'http://api.test/')
    vi.stubGlobal('localStorage', { getItem: (k: string) => (k === 'mizan_token' ? 'tok123' : null) })
    vi.stubGlobal('window', {})
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })
  afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals() })

  it('sends POST /auth/password with correct body', async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 204, json: async () => { throw new SyntaxError('empty') } })
    const s = (await import('../accounts')).createApiAccounts()
    await expect(s.changePassword('old-secret-pw!', 'new-secret-pw!')).resolves.toBeUndefined()
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://api.test/auth/password')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ current_password: 'old-secret-pw!', new_password: 'new-secret-pw!' })
  })

  it('maps 403 to wrongPassword', async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 403, json: async () => ({ detail: 'Mot de passe actuel incorrect.' }) })
    const s = (await import('../accounts')).createApiAccounts()
    expect(await rejectsWith(s.changePassword('bad-pw', 'new-secret-pw!'))).toBe('wrongPassword')
  })
})
