// Import SDMX-CSV (P-066) : POST /sdmx/import. Prévalidation côté client alignée sur le serveur ; le serveur reste l'autorité.
import { apiFetch, ApiError } from './api'

export const MAX_SDMX_BYTES = 50 * 1024 * 1024        // même limite que le serveur (SOVEREIGN_MAX_UPLOAD_MB par défaut)

export interface SdmxImportResult {
  table: string
  structure_id: string
  version: string
  action: string
  columns: string[]
  rows: number
  has_time_period: boolean
  loaded: boolean
}

export type FileIssue = 'none' | 'type' | 'size' | 'empty'
export type TableIssue = 'table'

/** Seuls les .csv et .txt sont acceptés (le SDMX-ML, en XML, est refusé par le serveur). */
export function fileIssue(f: { name: string; size: number } | null | undefined): FileIssue {
  if (!f) return 'none'
  if (!/\.(csv|txt)$/i.test(f.name)) return 'type'
  if (f.size === 0) return 'empty'
  if (f.size > MAX_SDMX_BYTES) return 'size'
  return 'none'
}

const TABLE_RE = /^[A-Za-z][A-Za-z0-9_]{0,60}$/

/** Nom de table facultatif : vide = déduit par le serveur de l'identifiant SDMX. */
export function tableIssue(name: string): TableIssue | null {
  const n = name.trim()
  return n === '' || TABLE_RE.test(n) ? null : 'table'
}

export interface ImportOptions { table: string; replace: boolean; dryRun: boolean }

export function importQuery(o: ImportOptions): string {
  const p = new URLSearchParams()
  if (o.table.trim()) p.set('table', o.table.trim())
  if (o.replace) p.set('replace', 'true')
  if (o.dryRun) p.set('dry_run', 'true')
  const s = p.toString()
  return s ? `?${s}` : ''
}

export async function sdmxImport(file: File, o: ImportOptions): Promise<SdmxImportResult> {
  if (fileIssue(file) !== 'none' || tableIssue(o.table)) throw new Error('invalid')
  const fd = new FormData()
  fd.append('file', file)
  const res = await apiFetch(`/sdmx/import${importQuery(o)}`, { method: 'POST', body: fd })
  const r = (await res.json()) as Partial<SdmxImportResult>
  if (typeof r.table !== 'string' || !Array.isArray(r.columns) || typeof r.rows !== 'number') throw new Error('bad response')
  return r as SdmxImportResult
}

export type ErrorKind = 'exists' | 'forbidden' | 'unauthorized' | 'server' | 'network'

/** Classe une erreur : 'server' = message du serveur (déjà en français, avec numéro de ligne) à afficher tel quel. */
export function classifyError(e: unknown): { kind: ErrorKind; detail?: string } {
  if (e instanceof ApiError) {
    if (e.status === 409) return { kind: 'exists', detail: e.detail }
    if (e.status === 403) return { kind: 'forbidden' }
    if (e.status === 401) return { kind: 'unauthorized' }
    if ([400, 413, 422].includes(e.status) && e.detail) return { kind: 'server', detail: e.detail }
  }
  return { kind: 'network' }
}

export const sameRequest = (a: { file: File | null; table: string; replace: boolean }, b: { file: File | null; table: string; replace: boolean }): boolean =>
  a.file === b.file && a.table.trim() === b.table.trim() && a.replace === b.replace
