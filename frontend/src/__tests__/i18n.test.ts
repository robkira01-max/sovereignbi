import { describe, it, expect } from 'vitest'
import {
  getTranslation,
  tplStr,
  getAllKeys,
  SUPPORTED_LOCALES,
  DEFAULT_LOCALE,
  type Locale,
} from '../i18n'

describe('SUPPORTED_LOCALES', () => {
  it('contains ar, en, es', () => {
    expect(SUPPORTED_LOCALES).toContain('ar')
    expect(SUPPORTED_LOCALES).toContain('en')
    expect(SUPPORTED_LOCALES).toContain('es')
  })

  it('has exactly 3 locales', () => {
    expect(SUPPORTED_LOCALES).toHaveLength(3)
  })
})

describe('DEFAULT_LOCALE', () => {
  it('is a supported locale', () => {
    expect(SUPPORTED_LOCALES).toContain(DEFAULT_LOCALE)
  })
})

describe('getTranslation', () => {
  it('resolves a nested key for English', () => {
    expect(getTranslation('en', 'nav.dashboards')).toBe('Dashboards')
  })

  it('resolves a nested key for Arabic', () => {
    expect(getTranslation('ar', 'nav.dashboards')).toBe('لوحات البيانات')
  })

  it('resolves a nested key for Spanish', () => {
    expect(getTranslation('es', 'nav.logout')).toBe('Cerrar sesión')
  })

  it('returns the key itself for a missing key', () => {
    expect(getTranslation('en', 'nonexistent.key')).toBe('nonexistent.key')
  })

  it('returns the key for a partial path pointing to an object', () => {
    expect(getTranslation('en', 'nav')).toBe('nav')
  })

  it('resolves login.submit for all locales', () => {
    expect(getTranslation('ar', 'login.submit')).toBe('دخول')
    expect(getTranslation('en', 'login.submit')).toBe('Login')
    expect(getTranslation('es', 'login.submit')).toBe('Iniciar sesión')
  })

  it('resolves confidence labels for all locales', () => {
    expect(getTranslation('ar', 'confidence.high')).toBe('عالية')
    expect(getTranslation('en', 'confidence.high')).toBe('high')
    expect(getTranslation('es', 'confidence.high')).toBe('alta')
  })

  it('resolves sql copy/copied for all locales', () => {
    expect(getTranslation('en', 'sql.copy')).toBe('Copy')
    expect(getTranslation('en', 'sql.copied')).toBe('Copied!')
    expect(getTranslation('ar', 'sql.copy')).toBe('نسخ')
    expect(getTranslation('es', 'sql.copy')).toBe('Copiar')
  })

  it('resolves chat.results template string', () => {
    const raw = getTranslation('en', 'chat.results')
    expect(raw).toContain('{n}')
  })
})

describe('tplStr', () => {
  it('replaces {n} in a string', () => {
    expect(tplStr('Results ({n} rows)', { n: 42 })).toBe('Results (42 rows)')
  })

  it('replaces multiple placeholders', () => {
    expect(tplStr('{a} and {b}', { a: 'foo', b: 'bar' })).toBe('foo and bar')
  })

  it('leaves unknown placeholders intact', () => {
    expect(tplStr('{x} test', {})).toBe('{x} test')
  })
})

describe('locale completeness', () => {
  const referenceLocale: Locale = 'en'
  const referenceKeys = getAllKeys(referenceLocale)

  it('reference locale has keys', () => {
    expect(referenceKeys.length).toBeGreaterThan(20)
  })

  for (const locale of SUPPORTED_LOCALES) {
    if (locale === referenceLocale) continue

    it(`${locale} has all keys that ${referenceLocale} has`, () => {
      const localeKeys = new Set(getAllKeys(locale))
      const missing = referenceKeys.filter(k => !localeKeys.has(k))
      expect(missing, `Missing keys in ${locale}: ${missing.join(', ')}`).toHaveLength(0)
    })

    it(`${locale} has no extra keys vs ${referenceLocale}`, () => {
      const refKeySet = new Set(referenceKeys)
      const extra = getAllKeys(locale).filter(k => !refKeySet.has(k))
      expect(extra, `Extra keys in ${locale}: ${extra.join(', ')}`).toHaveLength(0)
    })
  }
})
