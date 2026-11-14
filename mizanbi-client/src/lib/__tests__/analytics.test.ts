import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { isAnalyticsConfigured, isAnalyticsRunning, startAnalytics, stopAnalytics } from '../analytics'

// Mini DOM : seul ce que analytics.ts utilise.
function stubDocument() {
  const head: Record<string, unknown>[] = []
  vi.stubGlobal('document', {
    head: { appendChild: (el: Record<string, unknown>) => { head.push(el) } },
    createElement: () => {
      const attrs: Record<string, string> = {}
      const el: Record<string, unknown> = {
        attrs,
        setAttribute: (k: string, v: string) => { attrs[k] = v },
        remove: () => { head.splice(head.indexOf(el), 1) },
      }
      return el
    },
    getElementById: (id: string) => head.find(e => e.id === id) ?? null,
  })
  return head
}

beforeEach(() => vi.unstubAllEnvs())
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs() })

describe('analytics (consent-gated)', () => {
  it('is not configured and loads nothing by default', () => {
    const head = stubDocument()
    expect(isAnalyticsConfigured()).toBe(false)
    expect(startAnalytics()).toBe(false)
    expect(head).toHaveLength(0)
  })

  it('does nothing without a document (SSR / tests)', () => {
    vi.stubEnv('VITE_ANALYTICS_URL', 'https://stats.example.org/script.js')
    expect(startAnalytics()).toBe(false)
    expect(stopAnalytics()).toBe(false)
  })

  it('injects the script once when configured and started (after consent)', () => {
    vi.stubEnv('VITE_ANALYTICS_URL', 'https://stats.example.org/script.js')
    vi.stubEnv('VITE_ANALYTICS_SITE_ID', 'mizanbi.example.org')
    const head = stubDocument()
    expect(isAnalyticsConfigured()).toBe(true)
    expect(startAnalytics()).toBe(true)
    expect(startAnalytics()).toBe(false)
    expect(head).toHaveLength(1)
    expect(head[0].src).toBe('https://stats.example.org/script.js')
    expect((head[0].attrs as Record<string, string>)['data-domain']).toBe('mizanbi.example.org')
    expect(isAnalyticsRunning()).toBe(true)
  })

  it('stopAnalytics removes the script and reports whether a reload is needed', () => {
    vi.stubEnv('VITE_ANALYTICS_URL', 'https://stats.example.org/script.js')
    const head = stubDocument()
    startAnalytics()
    expect(stopAnalytics()).toBe(true)
    expect(head).toHaveLength(0)
    expect(stopAnalytics()).toBe(false)
  })

  it('nothing calls the analytics loader at startup (consent comes first)', async () => {
    const mains = import.meta.glob('../../main.tsx', { query: '?raw', import: 'default', eager: true }) as Record<string, string>
    for (const src of Object.values(mains)) expect(src).not.toMatch(/analytics/i)
  })
})
