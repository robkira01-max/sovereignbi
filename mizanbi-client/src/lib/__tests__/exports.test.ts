import { describe, it, expect } from 'vitest'
import { tileDataToCsv, dashboardToBulletinHtml } from '../exports'
import type { Tile } from '../api'

const SIMPLE_DATA = {
  columns: ['region', 'taux'],
  rows: [['Ali Sabieh', 25.3], ['Djibouti', 23.1]],
}

const KPI_DATA = {
  columns: ['v'],
  rows: [[23.5]],
}

describe('tileDataToCsv', () => {
  it('generates a header row', () => {
    const csv = tileDataToCsv('Test', SIMPLE_DATA)
    expect(csv.split('\r\n')[0]).toBe('region,taux')
  })

  it('generates data rows', () => {
    const csv = tileDataToCsv('Test', SIMPLE_DATA)
    const lines = csv.split('\r\n')
    expect(lines).toHaveLength(3)
    expect(lines[1]).toBe('Ali Sabieh,25.3')
    expect(lines[2]).toBe('Djibouti,23.1')
  })

  it('escapes values containing commas', () => {
    const csv = tileDataToCsv('Test', {
      columns: ['name', 'note'],
      rows: [['Alpha, Beta', 'ok']],
    })
    expect(csv).toContain('"Alpha, Beta"')
  })

  it('escapes values containing double-quotes', () => {
    const csv = tileDataToCsv('Test', {
      columns: ['v'],
      rows: [['"quoted"']],
    })
    expect(csv).toContain('"""quoted"""')
  })

  it('handles null/undefined values as empty string', () => {
    const csv = tileDataToCsv('Test', {
      columns: ['a', 'b'],
      rows: [[null, undefined]],
    })
    expect(csv.split('\r\n')[1]).toBe(',')
  })

  it('uses CRLF line endings', () => {
    const csv = tileDataToCsv('Test', SIMPLE_DATA)
    expect(csv).toContain('\r\n')
  })
})

describe('dashboardToBulletinHtml', () => {
  const kpiTile: Tile = { id: 'k1', type: 'kpi', title: 'Taux chômage', data: KPI_DATA }
  const tableTile: Tile = { id: 't1', type: 'table', title: 'Régions', data: SIMPLE_DATA }
  const noDataTile: Tile = { id: 'n1', type: 'bar', title: 'Sans données' }

  it('includes the dashboard title', () => {
    const html = dashboardToBulletinHtml('Mon Dashboard', [kpiTile])
    expect(html).toContain('Mon Dashboard')
  })

  it('renders a KPI tile with the value', () => {
    const html = dashboardToBulletinHtml('D', [kpiTile])
    expect(html).toContain('23.5')
    expect(html).toContain('tile-kpi')
  })

  it('renders a table tile with column headers', () => {
    const html = dashboardToBulletinHtml('D', [tableTile])
    expect(html).toContain('<th>region</th>')
    expect(html).toContain('<th>taux</th>')
  })

  it('renders a table tile with data rows', () => {
    const html = dashboardToBulletinHtml('D', [tableTile])
    expect(html).toContain('Ali Sabieh')
  })

  it('renders a tile without data gracefully', () => {
    const html = dashboardToBulletinHtml('D', [noDataTile])
    expect(html).toContain('Sans données')
    expect(html).toContain('Aucune donnée')
  })

  it('includes disclaimer footer', () => {
    const html = dashboardToBulletinHtml('D', [kpiTile])
    expect(html).toContain('MizanBI')
  })

  it('is valid HTML starting with DOCTYPE', () => {
    const html = dashboardToBulletinHtml('D', [kpiTile])
    expect(html.trimStart()).toMatch(/^<!DOCTYPE html>/i)
  })

  it('limits table rows to 50', () => {
    const bigData = {
      columns: ['n'],
      rows: Array.from({ length: 100 }, (_, i) => [i]),
    }
    const tile: Tile = { id: 'b1', type: 'table', title: 'Big', data: bigData }
    const html = dashboardToBulletinHtml('D', [tile])
    const tdCount = (html.match(/<td>/g) ?? []).length
    expect(tdCount).toBeLessThanOrEqual(50)
  })
})
