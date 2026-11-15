import { describe, expect, it } from 'vitest'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { badgeFor, buildCertifyBody, indexByTable, toValidUntil, type CertInfo } from '../certification'
import CertificationAdmin from '../../components/CertificationAdmin'
import { I18N } from '../i18n'
import CertificationBadge from '../../components/CertificationBadge'

const base: CertInfo = { table: 'pib', status: 'certified', certifier: 'INSTAD', reference: 'Note 2026-14', certified_at: '2026-11-12T10:00:00+00:00' }

describe('indexByTable', () => {
  it('indexes known statuses by table name', () => {
    const m = indexByTable({ tables: [base, { table: 'x', status: 'none' }] })
    expect(Object.keys(m).sort()).toEqual(['pib', 'x'])
  })
  it('never invents a certification from malformed or unknown data', () => {
    expect(indexByTable(null)).toEqual({})
    expect(indexByTable({})).toEqual({})
    expect(indexByTable({ tables: 'oui' })).toEqual({})
    expect(indexByTable({ tables: [{ table: 'pib', status: 'super-certifie' }, { status: 'certified' }, null, 3] })).toEqual({})
  })
})

describe('badgeFor', () => {
  for (const lang of ['fr', 'en'] as const) {
    const t = I18N[lang]
    it(`${lang}: no badge for uncertified or unknown tables`, () => {
      expect(badgeFor(undefined, t)).toBeNull()
      expect(badgeFor({ table: 'x', status: 'none' }, t)).toBeNull()
    })
    it(`${lang}: certified shows the institution, reference, date and the honesty note`, () => {
      const b = badgeFor(base, t)!
      expect(b.tone).toBe('ok')
      expect(b.label).toContain('INSTAD')
      expect(b.title).toContain('Note 2026-14')
      expect(b.title).toContain('2026-11-12')
      expect(b.title).toContain(t.certNotVerified)
    })
    it(`${lang}: stale, expired are warnings; revoked and tampered are errors, each with its own text`, () => {
      const tone = (status: CertInfo['status']) => badgeFor({ ...base, status }, t)!
      expect(tone('stale').tone).toBe('warn')
      expect(tone('stale').title).toContain(t.certStaleHint)
      expect(tone('expired').tone).toBe('warn')
      expect(tone('revoked').tone).toBe('bad')
      expect(tone('tampered').tone).toBe('bad')
      const labels = (['certified', 'stale', 'expired', 'revoked', 'tampered'] as const).map((s) => tone(s).label)
      expect(new Set(labels).size).toBe(5)
    })
  }
  it('shows the revocation reason', () => {
    const b = badgeFor({ ...base, status: 'revoked', revoked_reason: 'Erreur de source' }, I18N.fr)!
    expect(b.title).toContain('Erreur de source')
  })
  it('fr and en define every certification text', () => {
    for (const k of ['certCertified', 'certStale', 'certExpired', 'certRevoked', 'certTampered', 'certBy', 'certRef', 'certOn', 'certStaleHint', 'certNotVerified'] as const) {
      expect(I18N.fr[k]).toBeTruthy()
      expect(I18N.en[k]).toBeTruthy()
      expect(I18N.en[k]).not.toBe(I18N.fr[k])
    }
  })
})

describe('CertificationBadge', () => {
  it('renders nothing when the table is not certified', () => {
    expect(renderToStaticMarkup(createElement(CertificationBadge, { info: undefined, t: I18N.fr }))).toBe('')
  })
  it('renders icon + text (not colour alone), a tooltip and an accessible label', () => {
    const html = renderToStaticMarkup(createElement(CertificationBadge, { info: base, t: I18N.fr }))
    expect(html).toContain('cert-ok')
    expect(html).toContain('Validé — INSTAD')
    expect(html).toContain('aria-label="Validé — INSTAD"')
    expect(html).toContain('title="')
    expect(html).toContain('✔')
  })
  it('escapes a hostile institution name (no markup injection)', () => {
    const html = renderToStaticMarkup(createElement(CertificationBadge, { info: { ...base, certifier: '<img src=x onerror=alert(1)>' }, t: I18N.fr }))
    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;img')
  })
})


describe('toValidUntil / buildCertifyBody', () => {
  it('turns a day into end of day UTC, empty into null, anything else into undefined', () => {
    expect(toValidUntil('2027-03-31')).toBe('2027-03-31T23:59:59+00:00')
    expect(toValidUntil('')).toBeNull()
    expect(toValidUntil('  ')).toBeNull()
    for (const bad of ['demain', '31/03/2027', '2027-13-45', '2027-3-1', '2027-03-31T00:00']) expect(toValidUntil(bad)).toBeUndefined()
  })
  const ok = { table: 'pib', certifier: ' INSTAD ', reference: ' Note 14 ', validUntil: '' }
  it('trims fields and builds the request body', () => {
    expect(buildCertifyBody(ok)).toEqual({ table: 'pib', certifier: 'INSTAD', reference: 'Note 14', valid_until: null })
    expect(buildCertifyBody({ ...ok, validUntil: '2027-01-01' })?.valid_until).toBe('2027-01-01T23:59:59+00:00')
  })
  it('refuses a missing table, institution or reference, and a bad date', () => {
    for (const bad of [{ table: '' }, { certifier: '  ' }, { reference: '' }, { validUntil: 'bientôt' }]) {
      expect(buildCertifyBody({ ...ok, ...bad })).toBeNull()
    }
  })
})

describe('CertificationAdmin', () => {
  it('in demo mode (no API) shows the notice and no form, so nothing can be recorded', () => {
    const html = renderToStaticMarkup(createElement(CertificationAdmin, { t: I18N.fr }))
    expect(html).toContain(I18N.fr.admin.certSection)
    expect(html).toContain('mode démo')            // l'apostrophe est échappée en HTML : on teste un fragment sans apostrophe
    expect(html).not.toContain('<form')
    expect(html).not.toContain('<input')
  })
  it('fr and en define every admin certification text', () => {
    const keys = Object.keys(I18N.fr.admin).filter((k) => k.startsWith('cert')) as (keyof typeof I18N.fr.admin)[]
    expect(keys.length).toBe(18)
    for (const k of keys) {
      expect(I18N.en.admin[k]).toBeTruthy()
    }
    expect(Object.keys(I18N.en.admin).filter((k) => k.startsWith('cert')).sort()).toEqual(keys.map(String).sort())
  })
  it('the intro states that the institution is not verified', () => {
    expect(I18N.fr.admin.certIntro).toContain('ne vérifie pas')
    expect(I18N.en.admin.certIntro).toContain('does not verify')
  })
})
