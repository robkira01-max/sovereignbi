// P-079 — Pack Audit : aides pures, états des écrans (vide / erreur / succès), règles de rôle, vocabulaire.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { ApiError } from '../api'
import { I18N } from '../i18n'
import {
  MAX_UPLOAD_BYTES, uploadedId, buildParams, canWrite, classify, fileIssue, formatDecimal, justificationOk, parseBudgets, unresolvedErrors,
  type Comparison, type Finding, type FinRun, type Issue, type Rule, type RulesRun,
} from '../auditApi'
import { DocumentsTable, ImportSummaryView, IssuesList } from '../../pages/AuditData'
import { FindingsTable, RunSummaryView } from '../../pages/AuditRules'
import { ComparisonView, FormulaDetail, ResultCard } from '../../pages/Financial'
import { ErrorBox } from '../../components/audit/common'

const a = I18N.fr.audit
const html = (el: ReturnType<typeof createElement>) => renderToStaticMarkup(el)

describe('fileIssue', () => {
  it('accepts csv/xlsx within the 20 MB server limit only', () => {
    expect(fileIssue(null)).toBe('none')
    expect(fileIssue({ name: 'grand-livre.CSV', size: 10 })).toBe('none')
    expect(fileIssue({ name: 'a.xlsx', size: MAX_UPLOAD_BYTES })).toBe('none')
    expect(fileIssue({ name: 'a.xlsx', size: MAX_UPLOAD_BYTES + 1 })).toBe('size')
    expect(fileIssue({ name: 'a.xlsm', size: 10 })).toBe('type')
    expect(fileIssue({ name: 'a.csv.exe', size: 10 })).toBe('type')
    expect(fileIssue({ name: 'a.csv', size: 0 })).toBe('empty')
  })
})

describe('justificationOk', () => {
  it('requires 10 non-blank characters', () => {
    expect(justificationOk('court')).toBe(false)
    expect(justificationOk('          ')).toBe(false)
    expect(justificationOk('  facture annulée  ')).toBe(true)
  })
})

describe('formatDecimal — no numeric conversion, no precision loss', () => {
  it('groups thousands on the string and keeps every digit', () => {
    expect(formatDecimal('114000000.50', 'fr')).toBe('114 000 000,5')
    expect(formatDecimal('12345678901234567890.123456', 'en')).toBe('12,345,678,901,234,567,890.123456')   // > 2^53 : un Number() la corromprait
    expect(formatDecimal('-1200', 'en')).toBe('-1,200')
  })
  it('keeps trailing zeros when asked (95,00 %)', () => {
    expect(formatDecimal('95.00', 'fr', true)).toBe('95,00')
    expect(formatDecimal('95.00', 'fr')).toBe('95')
  })
  it('shows a dash for missing values and passes unparsable text through untouched', () => {
    expect(formatDecimal(null)).toBe('—')
    expect(formatDecimal('')).toBe('—')
    expect(formatDecimal('1e5')).toBe('1e5')
  })
})

describe('classify', () => {
  it('maps server answers to actionable kinds and keeps the structured code', () => {
    expect(classify(new ApiError(403, 'x')).kind).toBe('forbidden')
    expect(classify(new ApiError(409)).kind).toBe('conflict')
    expect(classify(new ApiError(429)).kind).toBe('busy')
    expect(classify(new ApiError(503)).kind).toBe('unavailable')
    expect(classify(new ApiError(500)).kind).toBe('server')
    expect(classify(new ApiError(422, 'Format de date à déclarer', 'date_format_required'))).toMatchObject({ kind: 'invalid', code: 'date_format_required' })
    expect(classify(new Error('API non configurée (VITE_API_BASE vide)')).kind).toBe('unconfigured')
    expect(classify(new TypeError('Failed to fetch')).kind).toBe('network')
  })
})

describe('parseBudgets / buildParams', () => {
  it('parses account;currency;amount lines and keeps amounts as strings', () => {
    expect(parseBudgets('601;djf;1500000,50\n602;DJF;10')).toEqual({ ok: true, value: [
      { account: '601', currency: 'DJF', amount: '1500000.50' }, { account: '602', currency: 'DJF', amount: '10' }] })
    expect(parseBudgets('601;DJF')).toEqual({ ok: false, line: 1 })
    expect(parseBudgets('601;DJF;abc')).toEqual({ ok: false, line: 1 })
    expect(parseBudgets('  ')).toEqual({ ok: false, line: 0 })
  })
  const rule = (params: Rule['params']): Rule => ({ code: 'AUD005', version: 1, title: 't', severity: 'warning', indicative: false, description: 'd', interpretation: 'i', requires: [], definition_hash: 'h', params })
  it('omits blank optional fields, flags missing required ones and rejects malformed values', () => {
    const r = rule([
      { name: 'threshold', type: 'decimal', default: null, required: true }, { name: 'window_days', type: 'int', default: 3, required: false },
      { name: 'weekend_days', type: 'int_list', default: [6, 7], required: false }, { name: 'period_start', type: 'date', default: '1900-01-01', required: false }])
    expect(buildParams(r, {})).toEqual({ params: {}, errors: { threshold: 'required' } })
    expect(buildParams(r, { threshold: '1500,5', window_days: '5', weekend_days: '6, 7', period_start: '2026-01-01' }))
      .toEqual({ params: { threshold: '1500.5', window_days: 5, weekend_days: [6, 7], period_start: '2026-01-01' }, errors: {} })
    expect(buildParams(r, { threshold: 'x', window_days: '1.5', weekend_days: 'a', period_start: '01/01/2026' }).errors)
      .toEqual({ threshold: 'decimal', window_days: 'int', weekend_days: 'int_list', period_start: 'date' })
  })
})

describe('uploadedId — forme réelle de POST /audit-data/documents', () => {
  it('reads the id under `document`, for a new file and for a duplicate', () => {
    expect(uploadedId({ duplicate: false, document: { document_id: 'abc', status: 'uploaded' }, preview: { headers: [], rows: [], rows_total: 0, meta: {} } })).toBe('abc')
    expect(uploadedId({ duplicate: true, document: { document_id: 'xyz', status: 'imported' } })).toBe('xyz')
  })
})

describe('roles', () => {
  it('only editors and admins write; counts read open_errors', () => {
    expect(canWrite('viewer')).toBe(false); expect(canWrite('editor')).toBe(true); expect(canWrite('admin')).toBe(true); expect(canWrite(undefined)).toBe(false)
    expect(unresolvedErrors({ open_errors: 3 })).toBe(3); expect(unresolvedErrors(undefined)).toBe(0)
  })
})

describe('Données — états', () => {
  it('shows the empty state and the documents list', () => {
    expect(html(createElement(DocumentsTable, { docs: [], selected: null, onSelect: () => {}, a }))).toContain(a.data.noDocs)
    const out = html(createElement(DocumentsTable, { docs: [{ document_id: 'd'.repeat(36), display_name: 'gl.csv', kind: 'csv', uploaded_at: '2026-11-19T10:00:00', status: 'imported', rows_imported: 12 }], selected: null, onSelect: () => {}, a }))
    expect(out).toContain('gl.csv'); expect(out).toContain(a.data.statusImported)
  })

  const err: Issue = { issue_id: 'i1', document_id: 'd', severity: 'error', code: 'invalid_date', source_row: 4, field: 'entry_date', message: 'Date invalide', raw_value: '31/02/2026', status: 'open' }
  const warn: Issue = { ...err, issue_id: 'i2', severity: 'warning', code: 'duplicate_row' }
  const resolveBtn = (role: string, i: Issue) => html(createElement(IssuesList, { issues: [i], role, a, onResolve: () => {} })).includes(`>${a.data.resolve}<`)

  it('empty list', () => expect(html(createElement(IssuesList, { issues: [], role: 'admin', a }))).toContain(a.data.noIssues))
  it('a viewer never gets a resolve button; an editor only for warnings; an admin for both', () => {
    expect(resolveBtn('viewer', warn)).toBe(false)
    expect(resolveBtn('editor', warn)).toBe(true)
    expect(resolveBtn('editor', err)).toBe(false)
    expect(resolveBtn('admin', err)).toBe(true)
  })
  it('explains why an editor cannot close a blocking issue', () => {
    expect(html(createElement(IssuesList, { issues: [err], role: 'editor', a }))).toContain(a.data.adminOnlyNote)
  })
  it('labels severity and keeps the original value visible', () => {
    const out = html(createElement(IssuesList, { issues: [err, warn], role: 'viewer', a }))
    expect(out).toContain(a.data.blocking); expect(out).toContain(a.data.toReview); expect(out).toContain('31/02/2026')
  })
  it('import summary distinguishes simulation from import and formats totals', () => {
    const r = { dry_run: true, summary: { rows: 2, rows_with_errors: 1, issue_counts: { invalid_date: 1 }, issues_truncated: false, totals: { debit: '1200.50' } }, issues_preview: [] }
    const out = html(createElement(ImportSummaryView, { result: r, a, lang: 'fr' }))
    expect(out).toContain(a.data.dryRunTitle); expect(out).toContain('1 200,5')
    expect(html(createElement(ImportSummaryView, { result: { ...r, dry_run: false }, a, lang: 'fr' }))).toContain(a.data.importDone)
  })
})

describe('Contrôles — états', () => {
  const f: Finding = { finding_id: 'f1', rule_code: 'AUD004', rule_version: 1, severity: 'info', indicative: true, status: 'to_review', summary: 'Facture saisie un dimanche', source_rows: [3, 9], amount: '2500000.00', details: {} }
  it('empty', () => expect(html(createElement(FindingsTable, { findings: [], a, lang: 'fr' }))).toContain(a.rules.noFindings))
  it('every finding is a "signal de risque", indicative rules are marked, amounts are formatted', () => {
    const out = html(createElement(FindingsTable, { findings: [f], a, lang: 'fr' }))
    expect(out).toContain(a.rules.signal); expect(out).toContain(a.rules.indicative); expect(out).toContain('2 500 000')
  })
  it('run summary shows versions, fingerprints, excluded rows and not-applicable reasons', () => {
    const run: RulesRun = { run_id: 'r'.repeat(36), document_id: 'd', findings_total: 1, disclaimer: '', summary: { ruleset_hash: 'a'.repeat(64), rows_excluded_for_errors: 2, rules: [
      { code: 'AUD004', version: 1, status: 'ran', reason: null, findings: 1, truncated: false, params: {} },
      { code: 'AUD007', version: 1, status: 'not_applicable', reason: 'aucun champ bancaire', findings: 0, truncated: false, params: {} }] } }
    const out = html(createElement(RunSummaryView, { run, rules: [], docSha: 'b'.repeat(64), a }))
    expect(out).toContain('AUD004'); expect(out).toContain('v1'); expect(out).toContain(a.rules.status.not_applicable); expect(out).toContain('aucun champ bancaire')
    expect(out).toContain('2 ligne(s) en erreur exclue(s)')
  })
})

describe('Formules — états', () => {
  const run: FinRun = { run_id: 'e'.repeat(36), created_at: '2026-11-19T10:00:00', created_by: 'u', engine_version: '1.0', ruleset_version: 'x', formula_code: 'TAUX_EXEC', formula_version: 1,
    definition_hash: 'd', input_snapshot_hash: 's'.repeat(64), result_hash: 'r'.repeat(64), status: 'ok', uses_table: false, integrity: 'ok', definition_status: 'unchanged',
    result: { value: '95.00', raw_value: '95', unit: '%', status: 'ok', message: '' } }
  it('result card shows « Calculé », the exact value with unit and the fingerprints', () => {
    const out = html(createElement(ResultCard, { run, a, lang: 'fr' }))
    expect(out).toContain(a.fin.computed); expect(out).toContain('95,00 %'); expect(out).toContain(a.fin.integrityOk); expect(out).toContain('s'.repeat(12))
  })
  it('an undefined result is not presented as calculated', () => {
    const out = html(createElement(ResultCard, { run: { ...run, result: { value: null, raw_value: null, unit: '%', status: 'undefined', message: 'Division par zéro' } }, a, lang: 'fr' }))
    expect(out).not.toContain(`>${a.fin.computed}<`); expect(out).toContain(a.fin.undefinedResult); expect(out).toContain('Division par zéro')
  })
  it('flags tampered integrity and changed definitions', () => {
    const out = html(createElement(ResultCard, { run: { ...run, integrity: 'mismatch', definition_status: 'definition_changed' }, a, lang: 'fr' }))
    expect(out).toContain(a.fin.integrityBad); expect(out).toContain(a.fin.defChanged)
  })
  it('comparison says identical only when inputs and result match', () => {
    const c: Comparison = { a: '1', b: '2', same_formula_and_version: true, same_result_hash: true, same_inputs: true, input_differences: {}, value_a: '95.00', value_b: '95.00', delta_b_minus_a: '0' }
    expect(html(createElement(ComparisonView, { c, a, lang: 'fr' }))).toContain(a.fin.identical)
    expect(html(createElement(ComparisonView, { c: { ...c, same_result_hash: false, delta_b_minus_a: '1.5' }, a, lang: 'fr' }))).toContain(a.fin.different)
  })
  it('formula detail lists expression, rounding, zero-division behaviour and variables', () => {
    const out = html(createElement(FormulaDetail, { a, f: { code: 'TAUX_EXEC', family: 'budget', version: 2, label: 'Taux', description: 'desc', expression: 'realise / budget * 100', result_unit: '%', precision: 2, rounding: 'half_up', on_zero_division: 'undefined', interpretation: '', definition_hash: 'h', variables: [{ name: 'budget', label: 'Budget', unit: 'DJF', required: true, allow_negative: false, default: null }] } }))
    expect(out).toContain('realise / budget * 100'); expect(out).toContain('half_up'); expect(out).toContain('undefined'); expect(out).toContain('budget')
  })
})

describe('ErrorBox', () => {
  it('explains each failure in plain language and shows the server detail', () => {
    expect(html(createElement(ErrorBox, { error: new ApiError(403, 'Séparation des tâches'), a }))).toContain('Séparation des tâches')
    expect(html(createElement(ErrorBox, { error: new Error('API non configurée (VITE_API_BASE vide)'), a }))).toContain(a.errors.unconfigured)
    expect(html(createElement(ErrorBox, { error: new TypeError('x'), a }))).toContain(a.errors.network)
  })
})

describe('Vocabulaire et traductions', () => {
  const strings = (o: unknown): string[] => typeof o === 'string' ? [o] : o && typeof o === 'object' ? Object.values(o).flatMap(strings) : []
  const keys = (o: unknown, p = ''): string[] => o && typeof o === 'object' ? Object.entries(o).flatMap(([k, v]) => keys(v, `${p}.${k}`)) : [p]
  it('never uses the word « fraude » / « fraud » in the Pack Audit interface', () => {
    for (const s of [...strings(I18N.fr.audit), ...strings(I18N.en.audit)]) expect(s).not.toMatch(/fraud/i)
  })
  it('states the fixed risk-signal wording in both languages', () => {
    expect(I18N.fr.audit.disclaimer.toLowerCase()).toContain('signal de risque'); expect(I18N.en.audit.disclaimer.toLowerCase()).toContain('risk signal')
  })
  it('fr and en expose the same keys and no empty string', () => {
    expect(keys(I18N.en.audit).sort()).toEqual(keys(I18N.fr.audit).sort())
    for (const s of [...strings(I18N.fr.audit), ...strings(I18N.en.audit)]) expect(s.trim()).not.toBe('')
  })
})

describe('api.ts — erreurs structurées', () => {
  afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.resetModules() })
  it('keeps the message and code of a {code, message} detail (import / calcul)', async () => {
    vi.stubEnv('VITE_API_BASE', 'http://api.test')
    vi.stubGlobal('sessionStorage', { getItem: () => null })
    vi.stubGlobal('fetch', async () => new Response(JSON.stringify({ detail: { code: 'date_format_required', message: 'Format de date à déclarer' } }), { status: 422 }))
    vi.resetModules()
    const { apiFetch, ApiError: AE } = await import('../api')
    const e = await apiFetch('/x').catch(x => x)
    expect(e).toBeInstanceOf(AE); expect(e.status).toBe(422); expect(e.detail).toBe('Format de date à déclarer'); expect(e.code).toBe('date_format_required')
  })
})
