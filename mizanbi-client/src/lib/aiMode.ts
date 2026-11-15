// Indicateur du mode IA (P-070) : lit GET /compliance/notice. Logique pure.
// Règle de prudence : une réponse absente ou mal formée n'affiche RIEN (jamais un état rassurant par défaut).
import { apiJson, isApiConfigured } from './api'

export type AiModeKind = 'local' | 'external-strict' | 'external-open'
export type Tone = 'ok' | 'warn'

export interface AiNotice {
  ai_provider?: unknown
  ai_external?: unknown
  ai_strict_mode?: unknown
  data_location?: unknown
  purposes?: unknown
}

export interface AiMode {
  kind: AiModeKind
  provider: string
  dataLocation: string
  description: string
}

const str = (v: unknown): string => (typeof v === 'string' ? v : '')

/** null = pas d'indicateur (données absentes ou incohérentes). */
export function parseAiMode(n: unknown): AiMode | null {
  if (!n || typeof n !== 'object') return null
  const a = n as AiNotice
  if (typeof a.ai_external !== 'boolean') return null
  let kind: AiModeKind
  if (!a.ai_external) kind = 'local'
  else if (a.ai_strict_mode === true) kind = 'external-strict'
  else if (a.ai_strict_mode === false) kind = 'external-open'
  else return null
  const purposes = Array.isArray(a.purposes) ? (a.purposes as { id?: unknown; description?: unknown }[]) : []
  const description = str(purposes.find((p) => p && p.id === 'ai_processing')?.description)
  return { kind, provider: str(a.ai_provider), dataLocation: str(a.data_location), description }
}

export const toneOf = (k: AiModeKind): Tone => (k === 'external-open' ? 'warn' : 'ok')
export const iconOf = (k: AiModeKind): string => (k === 'external-open' ? '⚠' : k === 'local' ? '●' : '◐')

export interface AiLabels {
  aiLocal: string; aiExternalStrict: string; aiExternalOpen: string; aiProvider: string; aiLocation: string
}

export function labelOf(k: AiModeKind, t: AiLabels): string {
  return k === 'local' ? t.aiLocal : k === 'external-strict' ? t.aiExternalStrict : t.aiExternalOpen
}

/** Infobulle : libellé, fournisseur, lieu des données et description complète du traitement. */
export function titleOf(m: AiMode, t: AiLabels): string {
  return [labelOf(m.kind, t), m.provider && `${t.aiProvider} : ${m.provider}`, m.dataLocation && `${t.aiLocation} : ${m.dataLocation}`, m.description]
    .filter(Boolean).join('\n')
}

export async function fetchAiMode(): Promise<AiMode | null> {
  if (!isApiConfigured()) return null
  return parseAiMode(await apiJson<unknown>('/compliance/notice'))
}
