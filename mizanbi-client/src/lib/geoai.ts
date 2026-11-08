// P-035 — Types et helpers GeoAI pour mizanbi-client.
// L'API backend est POST /api/v1/geo/ai-query (P-027, sovereignbi).
// En mode démo (VITE_API_BASE vide) : réponses précalculées depuis data/demo.ts.
// Aucun appel réseau sans VITE_API_BASE configuré.

import { REGIONS } from '../data/demo'

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

const INJECTION_RE = /ignore\s+(previous|prior|all)\s+instructions?|jailbreak|system\s*prompt|\[INST\]|act\s+as\s+|you\s+are\s+now\s+|forget\s+everything|disregard\s+|override\s+(your\s+)?instructions?/i

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

// Demo responses for offline / no-backend mode
export const DEMO_QUESTIONS: { label: string; q: string }[] = [
  { label: 'Chômage par région', q: 'Quelle région a le taux de chômage le plus élevé ?' },
  { label: 'Population et densité', q: 'Compare la population et la densité des régions' },
  { label: 'Pauvreté', q: 'Quelles régions ont un taux de pauvreté supérieur à 30 % ?' },
]

function demoChomage(): GeoAIResult {
  const sorted = [...REGIONS].sort((a, b) => b.unemployment - a.unemployment)
  const top = sorted[0]
  const bottom = sorted[sorted.length - 1]
  return {
    intent: { analysis: 'summary', layer_id: 'dj_adm1', params: {}, reasoning: 'Question sur le chômage régional' },
    columns: ['Région', 'Chômage (%)', 'Population'],
    rows: sorted.map((r) => [r.name, r.unemployment, r.population]),
    map_config: { type: 'map', layer_id: 'dj_adm1', value_col: 'unemployment' },
    prose: `${top.name} enregistre le taux de chômage le plus élevé avec ${top.unemployment} % (données démo 2024). La région la moins touchée est ${bottom.name} avec ${bottom.unemployment} %. L'écart entre les deux extrêmes est de ${(top.unemployment - bottom.unemployment).toFixed(1)} points de pourcentage.`,
    error: null,
  }
}

function demoPop(): GeoAIResult {
  const sorted = [...REGIONS].sort((a, b) => b.population - a.population)
  return {
    intent: { analysis: 'density', layer_id: 'dj_adm1', params: {}, reasoning: 'Question population/densité' },
    columns: ['Région', 'Population', 'Densité (hab/km²)'],
    rows: sorted.map((r) => [r.name, r.population, r.density ?? '—']),
    map_config: { type: 'map', layer_id: 'dj_adm1', value_col: 'density' },
    prose: `Djibouti-ville concentre ${sorted[0].population.toLocaleString('fr-FR')} habitants sur une superficie très réduite (densité ${sorted[0].density} hab/km²), soit ${((sorted[0].population / REGIONS.reduce((s, r) => s + r.population, 0)) * 100).toFixed(1)} % de la population totale. Les régions de l'intérieur ont des densités inférieures à 50 hab/km².`,
    error: null,
  }
}

function demoPauvrete(): GeoAIResult {
  const above30 = REGIONS.filter((r) => (r.poverty ?? 0) > 30).sort((a, b) => (b.poverty ?? 0) - (a.poverty ?? 0))
  return {
    intent: { analysis: 'summary', layer_id: 'dj_adm1', params: {}, reasoning: 'Filtre pauvreté > 30 %' },
    columns: ['Région', 'Pauvreté (%)', 'Chômage (%)'],
    rows: above30.map((r) => [r.name, r.poverty ?? '—', r.unemployment]),
    map_config: { type: 'map', layer_id: 'dj_adm1', value_col: 'poverty' },
    prose: `${above30.length} régions dépassent le seuil de 30 % de pauvreté (données démo 2024) : ${above30.map((r) => `${r.name} (${r.poverty} %)`).join(', ')}. Ces régions sont aussi parmi celles avec les taux de chômage les plus élevés.`,
    error: null,
  }
}

export function demoAnswer(q: string): GeoAIResult {
  const lq = q.toLowerCase()
  if (lq.includes('densit') || lq.includes('popul')) return demoPop()
  if (lq.includes('pauv')) return demoPauvrete()
  return demoChomage()
}
