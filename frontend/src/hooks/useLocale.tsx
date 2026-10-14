import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import {
  getTranslation,
  tplStr,
  type Locale,
  SUPPORTED_LOCALES,
  DEFAULT_LOCALE,
} from '../i18n'

export type { Locale }
export { SUPPORTED_LOCALES }

type TFunc = (key: string) => string
type TplFunc = (key: string, vars: Record<string, string | number>) => string

interface LocaleContextValue {
  locale: Locale
  setLocale: (l: Locale) => void
  t: TFunc
  tpl: TplFunc
}

const STORAGE_KEY = 'sovereign_locale'

function makeT(locale: Locale): TFunc {
  return (key: string) => getTranslation(locale, key)
}

function makeTpl(locale: Locale): TplFunc {
  return (key: string, vars: Record<string, string | number>) =>
    tplStr(getTranslation(locale, key), vars)
}

const defaultCtx: LocaleContextValue = {
  locale: DEFAULT_LOCALE,
  setLocale: () => {},
  t: makeT(DEFAULT_LOCALE),
  tpl: makeTpl(DEFAULT_LOCALE),
}

export const LocaleContext = createContext<LocaleContextValue>(defaultCtx)

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (typeof window === 'undefined') return DEFAULT_LOCALE
    const stored = localStorage.getItem(STORAGE_KEY) as Locale | null
    return stored && SUPPORTED_LOCALES.includes(stored) ? stored : DEFAULT_LOCALE
  })

  useEffect(() => {
    document.documentElement.lang = locale
    document.documentElement.dir = locale === 'ar' ? 'rtl' : 'ltr'
  }, [locale])

  const setLocale = (l: Locale) => {
    setLocaleState(l)
    localStorage.setItem(STORAGE_KEY, l)
  }

  const value: LocaleContextValue = {
    locale,
    setLocale,
    t: makeT(locale),
    tpl: makeTpl(locale),
  }

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
}

export function useLocale(): LocaleContextValue {
  return useContext(LocaleContext)
}
