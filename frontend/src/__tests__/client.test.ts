import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getKey, apiFetch } from '../api/client'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

beforeEach(() => {
  mockFetch.mockReset()
  sessionStorage.clear()
})

describe('getKey', () => {
  it('returns empty string when no key stored', () => {
    expect(getKey()).toBe('')
  })

  it('returns stored key', () => {
    sessionStorage.setItem('sovereign_api_key', 'test-key-123')
    expect(getKey()).toBe('test-key-123')
  })
})

describe('apiFetch', () => {
  it('adds X-Api-Key header from sessionStorage', async () => {
    sessionStorage.setItem('sovereign_api_key', 'my-key')
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ ok: true }) })
    await apiFetch('/test')
    const callArgs = mockFetch.mock.calls[0][1] as RequestInit
    expect((callArgs.headers as Record<string, string>)['X-Api-Key']).toBe('my-key')
  })

  it('throws on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 401, statusText: 'Unauthorized' })
    await expect(apiFetch('/test')).rejects.toThrow('401 Unauthorized')
  })

  it('sends POST with JSON body for /ask', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ sql: '', columns: [], rows: [], answer: '', error: null, attempts: 1, confidence: null }) })
    const { api } = await import('../api/client')
    await api.ask('CA total ?')
    expect(mockFetch.mock.calls[0][0]).toContain('/ask')
    expect(mockFetch.mock.calls[0][1].method).toBe('POST')
    expect(JSON.parse(mockFetch.mock.calls[0][1].body)).toEqual({ question: 'CA total ?' })
  })
})
