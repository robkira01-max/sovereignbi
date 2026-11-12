// P-035/P-036 — Types et helpers GeoAI pour mizanbi-client (fr/en/ar).
// L'API backend est POST /api/v1/geo/ai-query (P-027, sovereignbi).
// En mode démo (VITE_API_BASE vide) : réponses précalculées depuis data/demo.ts.
// Aucun appel réseau sans VITE_API_BASE configuré.

import { REGIONS } from '../data/demo'
import { I18N, type Lang } from './i18n'

export interface GeoAIIntent {
  analysis: string
  layer_id: string
  params: Record<string, unknown>
  reasoning: string
}

export interface GeoAIResult {
  intent: GeoAIIntent
  columns: string[]
  rows: (string | number | null)[][]
  map_config: { type: string; layer_id: string; value_col?: string } | null
  prose: string
  error: string | null
}

export interface GeoAIRequest {
  question: string
  locale?: string
}

export const QUESTION_MAX = 500

// Garde côté client (confort d'usage) : le backend applique son propre contrôle.
const INJECTION_RE = new RegExp(
  [
    // en
    'ignore\\s+(previous|prior|all)\\s+instructions?', 'jailbreak', 'system\\s*prompt', '\\[INST\\]',
    'act\\s+as\\s+', 'you\\s+are\\s+now\\s+', 'forget\\s+everything', 'disregard\\s+',
    'override\\s+(your\\s+)?instructions?',
    // fr
    'ignore[rz]?\\s+(toutes?\\s+)?(les\\s+)?(instructions|consignes)', 'oublie[rz]?\\s+tout',
    'prompt\\s+syst[eè]me', 'fais\\s+comme\\s+si', 'tu\\s+es\\s+maintenant', 'ne\\s+tiens\\s+pas\\s+compte',
    // ar
    'تجاهل\\s+(كل\\s+)?(ال)?(تعليمات|أوامر)', 'انس\\s+(كل|جميع)', 'موجه\\s+النظام',
  ].join('|'),
  'i',
)

export function guardInjection(q: string): boolean {
  return INJECTION_RE.test(q)
}

export function parseGeoAIResult(raw: unknown): GeoAIResult {
  if (!raw || typeof raw !== 'object') throw new Error('Réponse invalide')
  const r = raw as Record<string, unknown>
  return {
    intent: (r.intent as GeoAIIntent) ?? { analysis: '', layer_id: '', params: {}, reasoning: '' },
    columns: Array.isArray(r.columns) ? (r.columns as string[]) : [],
    rows: Array.isArray(r.rows) ? (r.rows as (string | number | null)[][]) : [],
    map_config: (r.map_config as GeoAIResult['map_config']) ?? null,
    prose: typeof r.prose === 'string' ? r.prose : '',
    error: typeof r.error === 'string' ? r.error : null,
  }
}

// ── Localisation ─────────────────────────────────────────────────────────────

const NUM_LOCALE: Record<Lang, string> = { fr: 'fr-FR', en: 'en-US' }

export const numberLocale = (lang: Lang): string => NUM_LOCALE[lang]

const num = (lang: Lang, v: number, digits = 0): string =>
  new Intl.NumberFormat(NUM_LOCALE[lang], { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v)

const pct = (lang: Lang, v: number): string => `${num(lang, v, 1)}${lang === 'fr' ? ' %' : '%'}`

export function fmt(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (m, k: string) => (k in vars ? String(vars[k]) : m))
}

export function demoQuestions(lang: Lang): { label: string; q: string }[] {
  const g = I18N[lang].geoai
  return [
    { label: g.exUnemploymentLabel, q: g.exUnemploymentQ },
    { label: g.exPopulationLabel, q: g.exPopulationQ },
    { label: g.exPovertyLabel, q: g.exPovertyQ },
  ]
}

export const DEMO_QUESTIONS = demoQuestions('fr')

// ── Réponses de démonstration ────────────────────────────────────────────────

function demoChomage(lang: Lang): GeoAIResult {
  const g = I18N[lang].geoai
  const sorted = [...REGIONS].sort((a, b) => b.unemployment - a.unemployment)
  const top = sorted[0]
  const bottom = sorted[sorted.length - 1]
  return {
    intent: { analysis: 'summary', layer_id: 'dj_adm1', params: {}, reasoning: g.reasonUnemployment },
    columns: [g.colRegion, g.colUnemployment, g.colPopulation],
    rows: sorted.map((r) => [r.name, r.unemployment, r.population]),
    map_config: { type: 'map', layer_id: 'dj_adm1', value_col: 'unemployment' },
    prose: fmt(g.proseUnemployment, {
      top: top.name, topRate: num(lang, top.unemployment, 1),
      bottom: bottom.name, bottomRate: num(lang, bottom.unemployment, 1),
      gap: num(lang, top.unemployment - bottom.unemployment, 1),
    }),
    error: null,
  }
}

function demoPop(lang: Lang): GeoAIResult {
  const g = I18N[lang].geoai
  const sorted = [...REGIONS].sort((a, b) => b.population - a.population)
  const city = sorted[0]
  const total = REGIONS.reduce((s, r) => s + r.population, 0)
  const maxOther = Math.max(...sorted.slice(1).map((r) => r.density ?? 0))
  return {
    intent: { analysis: 'density', layer_id: 'dj_adm1', params: {}, reasoning: g.reasonPopulation },
    columns: [g.colRegion, g.colPopulation, g.colDensity],
    rows: sorted.map((r) => [r.name, r.population, r.density ?? '—']),
    map_config: { type: 'map', layer_id: 'dj_adm1', value_col: 'density' },
    prose: fmt(g.prosePopulation, {
      city: city.name, pop: num(lang, city.population), density: num(lang, city.density ?? 0),
      share: num(lang, (city.population / total) * 100, 1), maxOther: num(lang, maxOther),
    }),
    error: null,
  }
}

function demoPauvrete(lang: Lang): GeoAIResult {
  const g = I18N[lang].geoai
  const above30 = REGIONS.filter((r) => (r.poverty ?? 0) > 30).sort((a, b) => (b.poverty ?? 0) - (a.poverty ?? 0))
  return {
    intent: { analysis: 'summary', layer_id: 'dj_adm1', params: {}, reasoning: g.reasonPoverty },
    columns: [g.colRegion, g.colPoverty, g.colUnemployment],
    rows: above30.map((r) => [r.name, r.poverty ?? '—', r.unemployment]),
    map_config: { type: 'map', layer_id: 'dj_adm1', value_col: 'poverty' },
    prose: fmt(g.prosePoverty, {
      list: above30.map((r) => `${r.name} (${pct(lang, r.poverty ?? 0)})`).join(', ') || '—',
      n: above30.length,
    }),
    error: null,
  }
}

const POPULATION_RE = /densit|popul|كثاف|سكان/i
const POVERTY_RE = /pauv|poverty|فقر/i

export function demoAnswer(q: string, lang: Lang = 'fr'): GeoAIResult {
  if (POPULATION_RE.test(q)) return demoPop(lang)
  if (POVERTY_RE.test(q)) return demoPauvrete(lang)
  return demoChomage(lang)
}
