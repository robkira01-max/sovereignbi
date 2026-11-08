import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HeatmapTile } from '../components/HeatmapTile'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const DATA_1D = {
  columns: ['mois', 'exportations_musd'],
  rows: [
    ['jan', 120], ['fév', 95], ['mars', 145],
    ['avr', 160], ['mai', 110], ['juin', 88],
  ],
}

const DATA_2D = {
  columns: ['heure', 'valeur', 'region'],
  rows: [
    ['08h', 50, 'Djibouti'],
    ['08h', 30, 'Ali Sabieh'],
    ['12h', 80, 'Djibouti'],
    ['12h', 45, 'Ali Sabieh'],
    ['18h', 60, 'Djibouti'],
    ['18h', 20, 'Ali Sabieh'],
  ],
}

const DATA_EMPTY = { columns: ['période', 'valeur'], rows: [] }

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('HeatmapTile', () => {
  it('renders heatmap container', () => {
    render(<HeatmapTile data={DATA_1D} title="Exportations" />)
    expect(screen.getByTestId('tile-heatmap')).toBeDefined()
  })

  it('renders correct number of cells for 1D data', () => {
    render(<HeatmapTile data={DATA_1D} title="Exportations" />)
    // 6 months × 1 row = 6 cells
    const cells = screen.getAllByTestId(/^heatmap-cell-/)
    expect(cells).toHaveLength(6)
  })

  it('renders correct number of cells for 2D data', () => {
    render(<HeatmapTile data={DATA_2D} title="Flux" />)
    // 3 hours × 2 regions = 6 cells
    const cells = screen.getAllByTestId(/^heatmap-cell-/)
    expect(cells).toHaveLength(6)
  })

  it('renders legend', () => {
    render(<HeatmapTile data={DATA_1D} title="Exportations" />)
    expect(screen.getByTestId('heatmap-legend')).toBeDefined()
  })

  it('handles empty data without crash', () => {
    render(<HeatmapTile data={DATA_EMPTY} title="Vide" />)
    expect(screen.getByTestId('tile-heatmap')).toBeDefined()
  })

  it('renders aria-label with title', () => {
    const { container } = render(<HeatmapTile data={DATA_1D} title="Exportations DJ" />)
    const svg = container.querySelector('svg')
    expect(svg?.getAttribute('aria-label')).toContain('Exportations DJ')
  })

  it('shows values in cells when showValues=true', () => {
    render(<HeatmapTile data={DATA_1D} title="Exp" options={{ showValues: true }} />)
    // With showValues, text elements with values appear inside cells
    const heatmap = screen.getByTestId('tile-heatmap')
    expect(heatmap.querySelector('text')).toBeTruthy()
  })

  it('applies different palette for orange scheme', () => {
    render(<HeatmapTile data={DATA_1D} title="Exp" options={{ colorScheme: 'orange' }} />)
    const cells = screen.getAllByTestId(/^heatmap-cell-/)
    // All cells should have fill attribute set
    cells.forEach(cell => expect(cell.getAttribute('fill')).toBeTruthy())
  })
})
