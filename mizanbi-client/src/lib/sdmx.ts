// Export SDMX-CSV 2.0 d'une tuile (P-066). Validation côté client alignée sur le serveur ; le serveur reste l'autorité.

export const SDMX_FREQS = ['A', 'S', 'Q', 'M', 'W', 'D'] as const
export type SdmxFreq = (typeof SDMX_FREQS)[number]

export interface SdmxOptions { structureId: string; unit: string; freq: string }
export type SdmxIssue = 'structure' | 'unit' | 'freq'

// AGENCE:IDENTIFIANT(VERSION), ex. INSTAD:CHOMAGE(1.0)
const STRUCTURE_RE = /^[A-Za-z0-9_.-]+:[A-Za-z0-9_@$-]+\(\d+(\.\d+){0,2}\)$/
const UNIT_RE = /^[A-Za-z0-9_.-]{1,40}$/

/** Problèmes bloquants (vide = valide). Les champs vides sont permis : le serveur déduit les valeurs par défaut. */
export function sdmxIssues(o: SdmxOptions): SdmxIssue[] {
  const out: SdmxIssue[] = []
  if (o.structureId.trim() && !STRUCTURE_RE.test(o.structureId.trim())) out.push('structure')
  if (o.unit.trim() && !UNIT_RE.test(o.unit.trim())) out.push('unit')
  if (o.freq && !(SDMX_FREQS as readonly string[]).includes(o.freq)) out.push('freq')
  return out
}

/** Paramètres de requête (champs vides omis), ou null si une option est invalide. */
export function sdmxQuery(o: SdmxOptions): string | null {
  if (sdmxIssues(o).length) return null
  const p = new URLSearchParams()
  if (o.structureId.trim()) p.set('structure_id', o.structureId.trim())
  if (o.unit.trim()) p.set('unit', o.unit.trim())
  if (o.freq) p.set('freq', o.freq)
  const s = p.toString()
  return s ? `?${s}` : ''
}

/** Identifiants de tableau de bord/tuile : on ne les met dans une URL que s'ils sont simples. */
const ID_RE = /^[A-Za-z0-9_-]{1,64}$/

export function sdmxPath(dashId: string, tileId: string, o: SdmxOptions): string | null {
  const q = sdmxQuery(o)
  if (q === null || !ID_RE.test(dashId) || !ID_RE.test(tileId)) return null
  return `/dashboards/${dashId}/tiles/${tileId}/export/sdmx-csv${q}`
}

export function sdmxFilename(dashId: string, tileId: string): string {
  return `${dashId}-${tileId}.sdmx.csv`.replace(/[^A-Za-z0-9._-]/g, '_')
}
