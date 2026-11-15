import { describe, expect, it } from 'vitest'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { SDMX_FREQS, sdmxFilename, sdmxIssues, sdmxPath, sdmxQuery } from '../sdmx'
import { I18N } from '../i18n'
import SdmxExportButton from '../../components/SdmxExportButton'

const none = { structureId: '', unit: '', freq: '' }

describe('sdmxIssues', () => {
  it('accepts empty options (the server infers defaults)', () => {
    expect(sdmxIssues(none)).toEqual([])
  })
  it('accepts AGENCY:ID(VERSION) and rejects anything else', () => {
    for (const ok of ['INSTAD:CHOMAGE(1.0)', 'MIZANBI:D_SDMX_T1(2)', 'a.b-c:X@Y(1.2.3)']) expect(sdmxIssues({ ...none, structureId: ok })).toEqual([])
    for (const bad of ['chomage', 'INSTAD:CHOMAGE', 'INSTAD:CHOMAGE(v1)', 'IN STAD:X(1.0)', 'X:Y(1.0)&evil=1', 'X:Y(1.0)\nX:Z(1.0)']) {
      expect(sdmxIssues({ ...none, structureId: bad })).toEqual(['structure'])
    }
  })
  it('trims surrounding spaces before validating and sending', () => {
    expect(sdmxQuery({ ...none, structureId: ' INSTAD:X(1.0)\n', unit: ' PCT ' })).toBe('?structure_id=INSTAD%3AX%281.0%29&unit=PCT')
  })
  it('restricts the unit and the frequency', () => {
    expect(sdmxIssues({ ...none, unit: 'PCT' })).toEqual([])
    expect(sdmxIssues({ ...none, unit: 'a b' })).toEqual(['unit'])
    expect(sdmxIssues({ ...none, unit: 'x'.repeat(41) })).toEqual(['unit'])
    expect(sdmxIssues({ ...none, freq: 'Z' })).toEqual(['freq'])
    for (const f of SDMX_FREQS) expect(sdmxIssues({ ...none, freq: f })).toEqual([])
  })
})

describe('sdmxQuery / sdmxPath', () => {
  it('omits empty fields and encodes the rest', () => {
    expect(sdmxQuery(none)).toBe('')
    expect(sdmxQuery({ structureId: 'INSTAD:X(1.0)', unit: 'PCT', freq: 'A' })).toBe('?structure_id=INSTAD%3AX%281.0%29&unit=PCT&freq=A')
  })
  it('returns null when an option is invalid, so nothing is requested', () => {
    expect(sdmxQuery({ ...none, unit: '../x' })).toBeNull()
    expect(sdmxPath('d1', 't1', { ...none, freq: 'Z' })).toBeNull()
  })
  it('builds the export path and refuses ids that are not simple (no path injection)', () => {
    expect(sdmxPath('d1', 't1', none)).toBe('/dashboards/d1/tiles/t1/export/sdmx-csv')
    expect(sdmxPath('d1', 't1', { ...none, unit: 'PCT' })).toBe('/dashboards/d1/tiles/t1/export/sdmx-csv?unit=PCT')
    for (const bad of ['../etc', 'a/b', 'a b', '', 'x'.repeat(65), 'a?b']) {
      expect(sdmxPath(bad, 't1', none)).toBeNull()
      expect(sdmxPath('d1', bad, none)).toBeNull()
    }
  })
  it('makes a safe file name', () => {
    expect(sdmxFilename('d1', 't1')).toBe('d1-t1.sdmx.csv')
    expect(sdmxFilename('d 1', 't/1')).toBe('d_1-t_1.sdmx.csv')
  })
})

describe('strings and component', () => {
  const keys = ['sdmxButton', 'sdmxTitle', 'sdmxStructure', 'sdmxUnit', 'sdmxFreq', 'sdmxFreqAuto', 'sdmxFreqA', 'sdmxFreqS', 'sdmxFreqQ', 'sdmxFreqM', 'sdmxFreqW', 'sdmxFreqD',
    'sdmxDownload', 'sdmxCancel', 'sdmxError', 'sdmxErrStructure', 'sdmxErrUnit', 'sdmxNote'] as const
  it('fr and en define every SDMX text, and every frequency has a label', () => {
    for (const k of keys) {
      expect(I18N.fr.dashboard[k]).toBeTruthy()
      expect(I18N.en.dashboard[k]).toBeTruthy()
    }
    expect(Object.keys(I18N.fr.dashboard).filter((k) => k.startsWith('sdmx')).sort()).toEqual([...keys].sort())
    expect(Object.keys(I18N.en.dashboard).filter((k) => k.startsWith('sdmx')).sort()).toEqual([...keys].sort())
  })
  it('the note states the default agency and that no official registry validated the file', () => {
    expect(I18N.fr.dashboard.sdmxNote).toContain('MIZANBI')
    expect(I18N.fr.dashboard.sdmxNote).toContain('non validé')
    expect(I18N.en.dashboard.sdmxNote).toContain('not validated')
  })
  it('renders a closed button by default, with an accessible title and no form', () => {
    const html = renderToStaticMarkup(createElement(SdmxExportButton, { dashId: 'd1', tileId: 't1', t: I18N.fr.dashboard, onError: () => {} }))
    expect(html).toContain('data-testid="export-sdmx-t1"')
    expect(html).toContain('↓ SDMX')
    expect(html).toContain('aria-expanded="false"')
    expect(html).not.toContain('<form')
  })
})
