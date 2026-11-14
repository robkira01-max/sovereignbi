import { describe, it, expect, beforeEach } from 'vitest'
import { LEGAL, PLACEHOLDER_RE, unresolvedConfig, type LegalConfig } from '../legalConfig'
import { LEGAL_DOCS, fill, legalText, type LegalKind } from '../legalContent'
import { acceptTerms, hasAcceptedTerms, markTermsAccepted, TERMS_KEY } from '../termsConsent'

const KINDS: LegalKind[] = ['privacy', 'terms', 'cookies', 'legal']

// Tous les fichiers source de l'application (hors tests et données embarquées).
const sources = import.meta.glob(['../../**/*.{ts,tsx}', '!../../**/__tests__/**', '!../../data/**'], {
  query: '?raw', import: 'default', eager: true,
}) as Record<string, string>

describe('legal documents', () => {
  it('fr and en define the same four documents with the same structure', () => {
    for (const k of KINDS) {
      const fr = LEGAL_DOCS.fr[k]
      const en = LEGAL_DOCS.en[k]
      expect(fr.sections.length, k).toBe(en.sections.length)
      fr.sections.forEach((s, i) => {
        expect(en.sections[i].bullets?.length, `${k}#${i} bullets`).toBe(s.bullets?.length)
        expect(en.sections[i].paragraphs?.length, `${k}#${i} paragraphs`).toBe(s.paragraphs?.length)
      })
    }
  })

  it('every {{token}} resolves to a config value (unknown tokens throw)', () => {
    for (const lang of ['fr', 'en'] as const) {
      for (const k of KINDS) expect(() => legalText(LEGAL_DOCS[lang][k])).not.toThrow()
    }
    expect(() => fill('{{nope}}')).toThrow(/inconnu/)
  })

  it('fill substitutes config values', () => {
    const cfg = { ...LEGAL, company: 'ACME Inc.' } as LegalConfig
    expect(fill('Organisation : {{company}}', cfg)).toBe('Organisation : ACME Inc.')
  })

  it('no longer claims that data never leaves the server, and discloses external AI mode', () => {
    for (const lang of ['fr', 'en'] as const) {
      const txt = legalText(LEGAL_DOCS[lang].privacy)
      expect(txt).not.toMatch(/ne quittent jamais|never leaves/i)
      expect(txt).toContain(LEGAL.aiProvider)
    }
  })

  it('the legal notice carries the publisher fields', () => {
    const txt = legalText(LEGAL_DOCS.fr.legal)
    for (const v of [LEGAL.company, LEGAL.address, LEGAL.registration, LEGAL.host]) expect(txt).toContain(v)
  })
})

describe('publication guard', () => {
  it('placeholders are only tolerated while LEGAL.draft is true', () => {
    if (LEGAL.draft) return
    expect(unresolvedConfig()).toEqual([])
    for (const lang of ['fr', 'en'] as const) {
      for (const k of KINDS) expect(legalText(LEGAL_DOCS[lang][k]).match(PLACEHOLDER_RE) ?? []).toEqual([])
    }
  })

  it('unresolvedConfig detects placeholders', () => {
    expect(unresolvedConfig({ ...LEGAL, company: '[À COMPLÉTER : x]', address: '1 rue X' } as LegalConfig)).toContain('company')
    expect(unresolvedConfig({ ...LEGAL, company: 'ACME' } as LegalConfig)).not.toContain('company')
  })

  it('consent version matches the AAAA-MM format accepted by the backend', () => {
    expect(LEGAL.version).toMatch(/^[0-9]{4}-[0-9]{2}$/)
  })
})

describe('cookie policy matches what the code really does', () => {
  const storageKeys = new Set<string>()
  for (const src of Object.values(sources)) {
    for (const m of src.matchAll(/['"](mizan_[a-z0-9_]+)['"]/g)) storageKeys.add(m[1])
  }

  it('finds the storage keys used by the app', () => {
    expect(storageKeys.size).toBeGreaterThanOrEqual(6)
    expect([...storageKeys]).toEqual(expect.arrayContaining(['mizan_token', 'mizan_cookie_consent', 'mizan_terms_accepted']))
  })

  it('documents every storage key in both languages', () => {
    for (const lang of ['fr', 'en'] as const) {
      const txt = legalText(LEGAL_DOCS[lang].cookies)
      for (const key of storageKeys) expect(txt, `${lang}: ${key}`).toContain(key)
    }
  })

  it('never sets an HTTP cookie from the client', () => {
    for (const [file, src] of Object.entries(sources)) expect(src, file).not.toMatch(/document\.cookie\s*=/)
  })

  it('loads no third-party service automatically (fonts, CDN, analytics)', () => {
    const banned = /fonts\.googleapis|fonts\.gstatic|openmaptiles|cdn\.jsdelivr|unpkg\.com|googletagmanager|google-analytics|plausible\.io|umami|facebook\.net/
    for (const [file, src] of Object.entries(sources)) expect(src, file).not.toMatch(banned)
  })
})

describe('terms acceptance', () => {
  beforeEach(() => {
    const mem = new Map<string, string>()
    ;(globalThis as unknown as { localStorage: Storage }).localStorage = {
      getItem: (k: string) => mem.get(k) ?? null,
      setItem: (k: string, v: string) => { mem.set(k, v) },
      removeItem: (k: string) => { mem.delete(k) },
      clear: () => mem.clear(),
      key: () => null,
      length: 0,
    } as Storage
  })

  it('is not accepted by default, and is per account and per version', () => {
    expect(hasAcceptedTerms('a@x.org')).toBe(false)
    markTermsAccepted('a@x.org', '2026-11')
    expect(hasAcceptedTerms('A@X.org', '2026-11')).toBe(true)
    expect(hasAcceptedTerms('b@x.org', '2026-11')).toBe(false)
    expect(hasAcceptedTerms('a@x.org', '2027-01')).toBe(false)
  })

  it('acceptTerms stores the acceptance locally when no API is configured (demo mode)', async () => {
    await acceptTerms('demo@instad.dj', 'demo')
    expect(hasAcceptedTerms('demo@instad.dj')).toBe(true)
    expect(JSON.parse(localStorage.getItem(TERMS_KEY) as string)['demo@instad.dj']).toBe(LEGAL.version)
  })

  it('survives corrupted storage', () => {
    localStorage.setItem(TERMS_KEY, '{not json')
    expect(hasAcceptedTerms('a@x.org')).toBe(false)
    markTermsAccepted('a@x.org')
    expect(hasAcceptedTerms('a@x.org')).toBe(true)
  })
})
