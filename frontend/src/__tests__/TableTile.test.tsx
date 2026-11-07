/**
 * P-018 — TableTile: sort and filter tests.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TableTile } from '../components/TableTile'

vi.mock('../hooks/useLocale', () => ({
  useLocale: () => ({ t: (k: string) => k, locale: 'fr' }),
}))

const DATA = {
  columns: ['region', 'emplois'],
  rows: [
    ['Djibouti', 45000],
    ['Ali Sabieh', 8200],
    ['Tadjourah', 3100],
    ['Obock', 2900],
  ],
}

describe('TableTile (P-018)', () => {
  it('renders all rows initially', () => {
    render(<TableTile data={DATA} />)
    expect(screen.getByText('Djibouti')).toBeTruthy()
    expect(screen.getByText('Ali Sabieh')).toBeTruthy()
    expect(screen.getByText('Tadjourah')).toBeTruthy()
    expect(screen.getByText('Obock')).toBeTruthy()
  })

  it('filters rows by text — only matching rows visible', () => {
    render(<TableTile data={DATA} />)
    const input = screen.getByTestId('table-filter-input') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'ali' } })
    expect(screen.queryByText('Djibouti')).toBeNull()
    expect(screen.getByText('Ali Sabieh')).toBeTruthy()
  })

  it('sorts column asc on first click', () => {
    render(<TableTile data={DATA} />)
    const header = screen.getByTestId('table-col-header-emplois')
    fireEvent.click(header)
    // After asc sort: Obock (2900) should come before Djibouti (45000)
    const cells = screen.getAllByRole('cell')
    const values = cells.map(c => c.textContent)
    const obockIdx = values.indexOf('Obock')
    const djiboutiIdx = values.indexOf('Djibouti')
    expect(obockIdx).toBeLessThan(djiboutiIdx)
  })

  it('sorts column desc on second click', () => {
    render(<TableTile data={DATA} />)
    const header = screen.getByTestId('table-col-header-emplois')
    fireEvent.click(header)
    fireEvent.click(header)
    // After desc sort: Djibouti (45000) should come first
    const cells = screen.getAllByRole('cell')
    expect(cells[0].textContent).toBe('Djibouti')
  })

  it('resets sort on third click', () => {
    render(<TableTile data={DATA} />)
    const header = screen.getByTestId('table-col-header-emplois')
    fireEvent.click(header)  // asc
    fireEvent.click(header)  // desc
    fireEvent.click(header)  // reset
    // No sort: original order — Djibouti first
    const cells = screen.getAllByRole('cell')
    expect(cells[0].textContent).toBe('Djibouti')
  })

  it('shows empty state row when filter matches nothing', () => {
    render(<TableTile data={DATA} />)
    const input = screen.getByTestId('table-filter-input') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'zzz-no-match' } })
    // tbody should have one row with the empty-state cell
    const cells = screen.getAllByRole('cell')
    expect(cells.length).toBe(1)
    expect(cells[0].textContent).toBe('—')
  })
})
