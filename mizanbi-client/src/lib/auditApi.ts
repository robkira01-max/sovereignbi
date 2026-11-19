// P-079 — Pack Audit : client typé des routes /audit-data, /audit-rules et /financial.
// Règle : aucun calcul financier ici. Les montants restent des CHAÎNES décimales ; on ne fait que les mettre en forme.
import { ApiError, apiFetch, apiJson } from './api'

export const MAX_UPLOAD_MB = 20            // SOVEREIGN_AUDIT_MAX_MB côté serveur (20 Mo par défaut)
export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
export const NORMALIZED_FIELDS = ['entry_date', 'account', 'label', 'reference', 'amount', 'debit', 'credit', 'currency', 'fiscal_year'] as const
export type NormalizedField = (typeof NORMALIZED_FIELDS)[number]
export const REQUIRED_FIELDS: NormalizedField[] = ['entry_date', 'account']

export type Role = 'viewer' | 'editor' | 'admin'
export const canWrite = (role?: string | null): boolean => role === 'editor' || role === 'admin'

export interface AuditDocument {
  document_id: string; sha256?: string; display_name?: string; kind: string; size_bytes?: number; uploaded_by?: string
  uploaded_at: string; rows_total?: number; status: 'uploaded' | 'imported' | string; imported_at?: string | null
  imported_by?: string | null; rows_imported?: number | null; summary_json?: string | null; issue_counts?: Record<string, number>
}
/** Réponse de POST /audit-data/documents : un doublon (même empreinte) renvoie le document existant, sans en créer un second. */
export interface UploadResponse { duplicate: boolean; document: Pick<AuditDocument, 'document_id' | 'status'> & Partial<AuditDocument>; preview?: Preview; suggestions?: Suggestions }
export const uploadedId = (r: UploadResponse): string => r.document.document_id

export interface Preview { headers: string[]; rows: (string | null)[][]; rows_total: number; meta: Record<string, unknown> }
export interface Suggestions { mapping: Partial<Record<NormalizedField, string>>; decimal_separator: ',' | '.' | null; date_formats: string[] }
export interface ImportBody {
  mapping: Partial<Record<NormalizedField, string>>; decimal_separator: ',' | '.'; date_format: string
  default_currency?: string | null; default_fiscal_year?: number | null; sheet?: string | null; dry_run?: boolean
}
export interface Issue {
  issue_id: string; document_id: string; severity: 'error' | 'warning'; code: string; source_row: number | null
  field: string | null; message: string; raw_value: string | null; status: 'open' | 'resolved'
  resolved_by?: string | null; resolved_at?: string | null; justification?: string | null
}
export interface ImportSummary { rows: number; rows_with_errors: number; issue_counts: Record<string, number>; issues_truncated: boolean; totals: Record<string, string> | null }
export interface ImportResult { dry_run: boolean; summary: ImportSummary; issues_preview: Partial<Issue>[] & { severity?: string }[] }

export interface RuleParam { name: string; type: 'int' | 'decimal' | 'date' | 'int_list' | 'budgets'; default: unknown; required: boolean; min?: number | null; max?: number | null }
export interface Rule {
  code: string; version: number; title: string; severity: 'info' | 'warning'; indicative: boolean; description: string
  interpretation: string; requires: string[]; definition_hash: string; params: RuleParam[]
}
export interface RuleOutcome { code: string; version: number; status: string; reason: string | null; findings: number; truncated: boolean; params: Record<string, unknown> }
export interface RulesRun {
  run_id: string; document_id: string; findings_total: number; disclaimer: string
  summary: { ruleset_hash: string; rules: RuleOutcome[]; rows_excluded_for_errors: number }
}
export interface Finding {
  finding_id: string; rule_code: string; rule_version: number; severity: string; indicative: boolean; status: string
  summary: string; source_rows: number[]; amount: string | null; details: Record<string, unknown>
}

export interface FormulaVariable { name: string; label: string; unit: string; required: boolean; allow_negative: boolean; default: string | null }
export interface Formula {
  code: string; family: string; version: number; label: string; description: string; expression: string; result_unit: string
  precision: number; rounding: string; on_zero_division: string; interpretation: string; definition_hash: string; variables: FormulaVariable[]
}
export interface FinRun {
  run_id: string; created_at: string; created_by: string; engine_version: string; ruleset_version: string; formula_code: string
  formula_version: number; definition_hash: string; input_snapshot_hash: string; result_hash: string; status: string; uses_table: boolean | number
  inputs?: Record<string, string>; sources?: Record<string, { explicit?: boolean }>
  result?: { value: string | null; raw_value: string | null; unit: string; status: string; message: string | null } | null
  integrity?: 'ok' | 'mismatch'; definition_status?: 'unchanged' | 'definition_changed' | 'formula_missing'
}
export interface Comparison {
  a: string; b: string; same_formula_and_version: boolean; same_result_hash: boolean; same_inputs: boolean
  input_differences: Record<string, { a: string | null; b: string | null }>; value_a: string | null; value_b: string | null; delta_b_minus_a: string | null
}

const j = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const auditApi = {
  listDocuments: () => apiJson<{ documents: AuditDocument[] }>('/audit-data/documents?limit=100'),
  getDocument: (id: string) => apiJson<AuditDocument>(`/audit-data/documents/${id}`),
  upload: (file: File) => { const f = new FormData(); f.append('file', file); return apiJson<UploadResponse>('/audit-data/documents', { method: 'POST', body: f }) },
  preview: (id: string) => apiJson<{ preview: Preview; suggestions: Suggestions }>(`/audit-data/documents/${id}/preview`),
  integrity: (id: string) => apiJson<{ status: 'ok' | 'mismatch' | 'missing'; sha256: string }>(`/audit-data/documents/${id}/integrity`),
  importDoc: (id: string, body: ImportBody) => apiJson<ImportResult>(`/audit-data/documents/${id}/import`, j(body)),
  issues: (id: string, status?: 'open' | 'resolved') =>
    apiJson<{ issues: Issue[]; counts: Record<string, number> }>(`/audit-data/documents/${id}/issues?limit=200${status ? `&status=${status}` : ''}`),
  resolve: (issueId: string, justification: string) => apiJson<Issue>(`/audit-data/issues/${issueId}/resolve`, j({ justification })),
  rules: () => apiJson<{ ruleset_hash: string; rules: Rule[]; disclaimer: string }>('/audit-rules/rules'),
  runRules: (document_id: string, rules: string[], params: Record<string, Record<string, unknown>>) =>
    apiJson<RulesRun>('/audit-rules/runs', j({ document_id, rules, params })),
  findings: (runId: string, ruleCode?: string) =>
    apiJson<{ findings: Finding[]; disclaimer: string }>(`/audit-rules/runs/${runId}/findings?limit=200${ruleCode ? `&rule_code=${ruleCode}` : ''}`),
  formulas: () => apiJson<{ engine_version: string; formulas: Formula[] }>('/financial/formulas'),
  runFormula: (formula_code: string, version: number, inputs: Record<string, string>) =>
    apiJson<FinRun>('/financial/runs', j({ formula_code, version, inputs })),
  finRuns: (formulaCode?: string) => apiJson<{ runs: FinRun[] }>(`/financial/runs?limit=50${formulaCode ? `&formula_code=${formulaCode}` : ''}`),
  finRun: (id: string) => apiJson<FinRun>(`/financial/runs/${id}`),
  compare: (a: string, b: string) => apiJson<Comparison>(`/financial/runs/${a}/compare/${b}`),
}

// ── Aides pures (testées) ───────────────────────────────────────────────────────

export type FileIssue = 'none' | 'type' | 'empty' | 'size'
/** Contrôle côté navigateur ; le serveur refuse de toute façon (signature, taille, macros…). */
export function fileIssue(f: { name: string; size: number } | null): FileIssue {
  if (!f) return 'none'
  if (!/\.(csv|xlsx)$/i.test(f.name)) return 'type'
  if (f.size === 0) return 'empty'
  if (f.size > MAX_UPLOAD_BYTES) return 'size'
  return 'none'
}

export const MIN_JUSTIFICATION = 10
export const justificationOk = (s: string): boolean => s.trim().length >= MIN_JUSTIFICATION

/** Mise en forme d'un montant décimal fourni par l'API, SANS conversion numérique (aucune perte, aucun arrondi). */
export function formatDecimal(v: string | null | undefined, lang: 'fr' | 'en' = 'fr', keepFraction = false): string {
  if (v == null || v === '') return '—'
  const m = /^(-?)(\d+)(?:\.(\d+))?$/.exec(v.trim())
  if (!m) return v
  const sep = lang === 'fr' ? ' ' : ','
  const int = m[2].replace(/\B(?=(\d{3})+(?!\d))/g, sep)
  const frac = m[3] ? (keepFraction ? m[3] : m[3].replace(/0+$/, '')) : ''
  return `${m[1]}${int}${frac ? (lang === 'fr' ? ',' : '.') + frac : ''}`
}

export type ErrorKind = 'unconfigured' | 'forbidden' | 'unauthorized' | 'not_found' | 'conflict' | 'too_large' | 'invalid' | 'busy' | 'unavailable' | 'server' | 'network'
export function classify(e: unknown): { kind: ErrorKind; message?: string; code?: string } {
  if (e instanceof ApiError) {
    const k: Record<number, ErrorKind> = { 401: 'unauthorized', 403: 'forbidden', 404: 'not_found', 409: 'conflict', 413: 'too_large', 415: 'invalid', 422: 'invalid', 429: 'busy', 503: 'unavailable' }
    return { kind: k[e.status] ?? (e.status >= 500 ? 'server' : 'invalid'), message: e.detail, code: e.code }
  }
  if (e instanceof Error && /non configurée/.test(e.message)) return { kind: 'unconfigured' }
  return { kind: 'network' }
}

/** « compte;devise;montant » par ligne → budgets de l'API (montants gardés en chaînes). */
export function parseBudgets(text: string): { ok: true; value: { account: string; currency: string; amount: string }[] } | { ok: false; line: number } {
  const out: { account: string; currency: string; amount: string }[] = []
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean)
  for (let i = 0; i < lines.length; i++) {
    const p = lines[i].split(/[;\t]/).map(x => x.trim())
    if (p.length !== 3 || !p[0] || !/^[A-Za-z]{3}$/.test(p[1]) || !/^\d+([.,]\d+)?$/.test(p[2])) return { ok: false, line: i + 1 }
    out.push({ account: p[0], currency: p[1].toUpperCase(), amount: p[2].replace(',', '.') })
  }
  return out.length ? { ok: true, value: out } : { ok: false, line: 0 }
}

/** Valeurs saisies → paramètres envoyés ; les champs vides sont omis (le serveur applique ses défauts). */
export function buildParams(rule: Rule, raw: Record<string, string>): { params: Record<string, unknown>; errors: Record<string, string> } {
  const params: Record<string, unknown> = {}
  const errors: Record<string, string> = {}
  for (const p of rule.params) {
    const v = (raw[p.name] ?? '').trim()
    if (!v) { if (p.required && p.default == null) errors[p.name] = 'required'; continue }
    if (p.type === 'int') { /^-?\d+$/.test(v) ? (params[p.name] = Number.parseInt(v, 10)) : (errors[p.name] = 'int') }
    else if (p.type === 'decimal') { /^\d+([.,]\d+)?$/.test(v) ? (params[p.name] = v.replace(',', '.')) : (errors[p.name] = 'decimal') }
    else if (p.type === 'date') { /^\d{4}-\d{2}-\d{2}$/.test(v) ? (params[p.name] = v) : (errors[p.name] = 'date') }
    else if (p.type === 'int_list') {
      const parts = v.split(/[,\s]+/).filter(Boolean)
      parts.length && parts.every(x => /^\d+$/.test(x)) ? (params[p.name] = parts.map(x => Number.parseInt(x, 10))) : (errors[p.name] = 'int_list')
    } else if (p.type === 'budgets') {
      const b = parseBudgets(v)
      b.ok ? (params[p.name] = b.value) : (errors[p.name] = 'budgets')
    }
  }
  return { params, errors }
}

export const unresolvedErrors = (counts?: Record<string, number> | null): number => counts?.open_errors ?? 0

export const IMPORT_DATE_FORMATS = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y/%m/%d'] as const
