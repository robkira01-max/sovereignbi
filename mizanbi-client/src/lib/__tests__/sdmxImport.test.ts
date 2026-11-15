import { describe, expect, it } from 'vitest'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { ApiError } from '../api'
import { MAX_SDMX_BYTES, classifyError, fileIssue, importQuery, sameRequest, tableIssue } from '../sdmxImport'
import { I18N } from '../i18n'
import SdmxImport from '../../components/SdmxImport'

describe('fileIssue', () => {
  it('accepts .csv and .txt files of a sensible size', () => {
    expect(fileIssue({ name: 'chomage.csv', size: 1200 })).toBe('none')
    expect(fileIssue({ name: 'DATA.CSV', size: 1 })).toBe('none')
    expect(fileIssue({ name: 'export.txt', size: 10 })).toBe('none')
    expect(fileIssue(null)).toBe('none')
  })
  it('refuses XML (SDMX-ML), spreadsheets, empty and oversized files', () => {
    expect(fileIssue({ name: 'structure.xml', size: 10 })).toBe('type')
    expect(fileIssue({ name: 'data.xlsx', size: 10 })).toBe('type')
    expect(fileIssue({ name: 'data.csv.exe', size: 10 })).toBe('type')
    expect(fileIssue({ name: 'a.csv', size: 0 })).toBe('empty')
    expect(fileIssue({ name: 'a.csv', size: MAX_SDMX_BYTES + 1 })).toBe('size')
    expect(fileIssue({ name: 'a.csv', size: MAX_SDMX_BYTES })).toBe('none')
  })
})

describe('tableIssue / importQuery', () => {
  it('allows an empty name and simple identifiers only', () => {
    for (const ok of ['', '  ', 'chomage', 'Pib_2024', 'a'.repeat(61)]) expect(tableIssue(ok)).toBeNull()
    for (const bad of ['1abc', 'a b', 'a;DROP TABLE x', 'é', 'a'.repeat(62), '../x', 'a-b']) expect(tableIssue(bad)).toBe('table')
  })
  it('builds the query string, omitting defaults', () => {
    expect(importQuery({ table: '', replace: false, dryRun: false })).toBe('')
    expect(importQuery({ table: ' pib ', replace: true, dryRun: true })).toBe('?table=pib&replace=true&dry_run=true')
    expect(importQuery({ table: '', replace: false, dryRun: true })).toBe('?dry_run=true')
  })
})

describe('classifyError', () => {
  it('maps the server answers the user can act on', () => {
    expect(classifyError(new ApiError(409, 'existe déjà')).kind).toBe('exists')
    expect(classifyError(new ApiError(403)).kind).toBe('forbidden')
    expect(classifyError(new ApiError(401)).kind).toBe('unauthorized')
  })
  it('keeps the server message (with its line number) for validation errors', () => {
    for (const status of [400, 413, 422]) {
      expect(classifyError(new ApiError(status, 'Ligne 3 : OBS_VALUE non numérique « abc »'))).toEqual({ kind: 'server', detail: 'Ligne 3 : OBS_VALUE non numérique « abc »' })
    }
  })
  it('treats anything else, including a 422 without message, as a generic failure', () => {
    expect(classifyError(new ApiError(422)).kind).toBe('network')
    expect(classifyError(new ApiError(500, 'boom')).kind).toBe('network')
    expect(classifyError(new Error('x')).kind).toBe('network')
  })
})

describe('sameRequest (the load button only applies to what was checked)', () => {
  const f = new File(['x'], 'a.csv')
  const base = { file: f, table: 'pib', replace: false }
  it('is true only for the identical file, trimmed table and replace flag', () => {
    expect(sameRequest(base, { ...base, table: ' pib ' })).toBe(true)
    expect(sameRequest(base, { ...base, table: 'autre' })).toBe(false)
    expect(sameRequest(base, { ...base, replace: true })).toBe(false)
    expect(sameRequest(base, { ...base, file: new File(['x'], 'a.csv') })).toBe(false)
    expect(sameRequest(base, { ...base, file: null })).toBe(false)
  })
})

describe('strings and component', () => {
  it('fr and en define the same non-empty texts', () => {
    const fr = I18N.fr.sdmxImport as Record<string, string>
    const en = I18N.en.sdmxImport as Record<string, string>
    expect(Object.keys(fr).length).toBeGreaterThanOrEqual(25)
    expect(Object.keys(en).sort()).toEqual(Object.keys(fr).sort())
    for (const k of Object.keys(fr)) { expect(fr[k]).toBeTruthy(); expect(en[k]).toBeTruthy() }
  })
  it('states the SDMX-ML limit and that nothing is loaded before confirmation', () => {
    expect(I18N.fr.sdmxImport.note).toContain('pas de SDMX-ML')
    expect(I18N.en.sdmxImport.note).toContain('no SDMX-ML')
    expect(I18N.fr.sdmxImport.dryOk).toContain('Rien n’est encore chargé')
  })
  it('in demo mode (no API) shows the notice and no file input, so nothing can be sent', () => {
    const html = renderToStaticMarkup(createElement(SdmxImport, { t: I18N.fr.sdmxImport }))
    expect(html).toContain(I18N.fr.sdmxImport.title)
    expect(html).toContain('mode démo')
    expect(html).not.toContain('type="file"')
  })
})
