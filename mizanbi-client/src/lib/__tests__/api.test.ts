// Revue de sécurité — en-têtes d'authentification du client standalone.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { authHeaders, login } from '../api'

function stubBrowser(opts: { token?: string | null; key?: string }) {
  vi.stubGlobal('sessionStorage', { getItem: (k: string) => (k === 'mizan_token' ? opts.token ?? null : null) })
  // Une clé placée dans window (ancien mécanisme d'injection) ne doit jamais être lue.
  vi.stubGlobal('window', opts.key ? { __MIZAN_API_KEY__: opts.key } : {})
}

beforeEach(() => stubBrowser({}))
afterEach(() => vi.unstubAllGlobals())

describe('authHeaders', () => {
  it('sends nothing when anonymous', () => {
    expect(authHeaders()).toEqual({})
  })

  it('sends the Bearer session token', () => {
    stubBrowser({ token: 'abc123' })
    expect(authHeaders()).toEqual({ Authorization: 'Bearer abc123' })
  })

  it('never sends the demo token', () => {
    stubBrowser({ token: 'demo' })
    expect(authHeaders()).toEqual({})
  })

  it('ignores any API key injected in window: a secret in the browser is readable by every user', () => {
    stubBrowser({ key: 'k-secret-123' })
    expect(authHeaders()).toEqual({})
    stubBrowser({ token: 'abc123', key: 'k-secret-123' })
    const h = authHeaders()
    expect(h).toEqual({ Authorization: 'Bearer abc123' })
    expect('X-Api-Key' in h).toBe(false)
  })

  it('does not fall back to an injected key when only the demo token is present', () => {
    stubBrowser({ token: 'demo', key: 'k-secret-123' })
    expect(authHeaders()).toEqual({})
  })
})

describe('login', () => {
  const respond = (body: unknown, ok = true) =>
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok, json: async () => body }))

  it('returns token and email', async () => {
    respond({ token: 't1', email: 'a@b.dj' })
    expect(await login('x@y.dj', 'pw')).toEqual({ token: 't1', email: 'a@b.dj' })
  })

  it('accepts access_token as an alias', async () => {
    respond({ access_token: 't2' })
    expect((await login('x@y.dj', 'pw')).token).toBe('t2')
  })

  it('rejects a 200 response without a token instead of "logging in" with an empty one', async () => {
    respond({ email: 'a@b.dj' })
    await expect(login('x@y.dj', 'pw')).rejects.toThrow('login failed')
  })

  it('rejects on HTTP error', async () => {
    respond({}, false)
    await expect(login('x@y.dj', 'pw')).rejects.toThrow('login failed')
  })
})
