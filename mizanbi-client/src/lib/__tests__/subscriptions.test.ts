import { describe, expect, it } from 'vitest'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { buildSubBody, daysOf, describeSchedule, isoDay, subIssues, type SubInput } from '../subscriptions'
import { I18N } from '../i18n'
import SubscriptionsPanel from '../../components/SubscriptionsPanel'

const ok: SubInput = { email: 'agent@instad.dj', frequency: 'weekly', hourUtc: 7, weekday: 0, dayOfMonth: 1, consent: true }

describe('subIssues', () => {
  it('accepts a valid subscription', () => {
    expect(subIssues(ok)).toEqual([])
  })
  it('requires the consent box (no double opt-in on the server, so the editor must affirm it)', () => {
    expect(subIssues({ ...ok, consent: false })).toEqual(['consent'])
  })
  it('rejects malformed addresses, including header-injection attempts', () => {
    for (const bad of ['', 'x', 'a@b', 'a b@c.org', 'a@@c.org', 'a@c..org', 'a@c.org\r\nBcc: x@y.org', '@c.org']) {
      expect(subIssues({ ...ok, email: bad })).toContain('email')
    }
    expect(subIssues({ ...ok, email: ' Agent@Instad.dj ' })).toEqual([])
  })
  it('checks hour, weekday and day of month only where they apply', () => {
    expect(subIssues({ ...ok, hourUtc: 24 })).toEqual(['hour'])
    expect(subIssues({ ...ok, hourUtc: -1 })).toEqual(['hour'])
    expect(subIssues({ ...ok, hourUtc: 7.5 })).toEqual(['hour'])
    expect(subIssues({ ...ok, weekday: 7 })).toEqual(['weekday'])
    expect(subIssues({ ...ok, frequency: 'daily', weekday: 99, dayOfMonth: 99 })).toEqual([])
    expect(subIssues({ ...ok, frequency: 'monthly', dayOfMonth: 29 })).toEqual(['day'])
    expect(subIssues({ ...ok, frequency: 'monthly', dayOfMonth: 28 })).toEqual([])
    expect(subIssues({ ...ok, frequency: 'yearly' })).toEqual(['frequency'])
  })
})

describe('buildSubBody', () => {
  it('lower-cases and trims the address and neutralises the fields that do not apply', () => {
    expect(buildSubBody('d1', { ...ok, email: ' Agent@Instad.DJ ', frequency: 'daily', weekday: 4, dayOfMonth: 20 })).toEqual({
      dashboard_id: 'd1', email: 'agent@instad.dj', frequency: 'daily', hour_utc: 7, weekday: 0, day_of_month: 1,
    })
    expect(buildSubBody('d1', { ...ok, frequency: 'weekly', weekday: 4 })?.weekday).toBe(4)
    expect(buildSubBody('d1', { ...ok, frequency: 'monthly', dayOfMonth: 15 })?.day_of_month).toBe(15)
  })
  it('returns null when invalid or not consented', () => {
    expect(buildSubBody('d1', { ...ok, consent: false })).toBeNull()
    expect(buildSubBody('d1', { ...ok, email: 'x' })).toBeNull()
  })
})

describe('describeSchedule', () => {
  const base = { hour_utc: 7, weekday: 0, day_of_month: 1 }
  it('reads naturally in French and English', () => {
    const fr = I18N.fr.dashboard
    const en = I18N.en.dashboard
    expect(describeSchedule({ ...base, frequency: 'daily' }, fr)).toBe('Chaque jour à 07:00 UTC')
    expect(describeSchedule({ ...base, frequency: 'weekly', weekday: 4 }, fr)).toBe('Chaque vendredi à 07:00 UTC')
    expect(describeSchedule({ ...base, frequency: 'monthly', day_of_month: 15, hour_utc: 18 }, fr)).toBe('Le 15 de chaque mois à 18:00 UTC')
    expect(describeSchedule({ ...base, frequency: 'weekly', weekday: 6 }, en)).toBe('Every Sunday at 07:00 UTC')
    expect(describeSchedule({ ...base, frequency: 'monthly', day_of_month: 3 }, en)).toBe('On day 3 of each month at 07:00 UTC')
  })
  it('never prints undefined for an out-of-range weekday', () => {
    expect(describeSchedule({ ...base, frequency: 'weekly', weekday: 9 }, I18N.fr.dashboard)).not.toContain('undefined')
  })
  it('has seven weekday names in each language', () => {
    expect(daysOf(I18N.fr.dashboard)).toHaveLength(7)
    expect(daysOf(I18N.en.dashboard)).toHaveLength(7)
  })
  it('formats the last-sent timestamp', () => {
    expect(isoDay('2026-11-16T07:00:12.345+00:00')).toBe('2026-11-16 07:00')
    expect(isoDay(null)).toBe('')
  })
})

describe('strings and panel', () => {
  const keys = Object.keys(I18N.fr.dashboard).filter((k) => k.startsWith('sub'))
  it('fr and en define exactly the same subscription texts, all non-empty', () => {
    expect(keys.length).toBeGreaterThan(30)
    expect(Object.keys(I18N.en.dashboard).filter((k) => k.startsWith('sub')).sort()).toEqual([...keys].sort())
    for (const k of keys) {
      expect((I18N.fr.dashboard as Record<string, string>)[k]).toBeTruthy()
      expect((I18N.en.dashboard as Record<string, string>)[k]).toBeTruthy()
    }
  })
  it('states that without SMTP nothing is really sent, and the consent responsibility', () => {
    expect(I18N.fr.dashboard.subModeOutbox).toContain('aucun courriel réel')
    expect(I18N.en.dashboard.subModeOutbox).toContain('no real e-mail')
    expect(I18N.fr.dashboard.subNote).toContain('consentement')
    expect(I18N.en.dashboard.subNote).toContain('consent')
  })
  it('labels the frequency options in plain words (no placeholder left over)', () => {
    for (const lang of ['fr', 'en'] as const) {
      const html = renderToStaticMarkup(createElement(SubscriptionsPanel, { dashId: 'd1', t: I18N[lang].dashboard }))
      expect(html).toContain(`>${I18N[lang].dashboard.subEveryWeek}<`)
      expect(html).toContain(`>${I18N[lang].dashboard.subEveryMonth}<`)
      expect(html).not.toContain('…')
      expect(html).not.toContain('{day}')
    }
  })
  it('renders the form with the consent box and a disabled submit button initially', () => {
    const html = renderToStaticMarkup(createElement(SubscriptionsPanel, { dashId: 'd1', t: I18N.fr.dashboard }))
    expect(html).toContain(I18N.fr.dashboard.subTitle)
    expect(html).toContain('type="checkbox"')
    expect(html).toMatch(/<button[^>]*disabled[^>]*type="submit"|<button[^>]*type="submit"[^>]*disabled/)
  })
})
