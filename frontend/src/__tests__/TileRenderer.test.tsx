import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TileRenderer } from '../components/TileRenderer'

const kpiData = { columns: ['valeur'], rows: [[42000]] }
const tableData = { columns: ['région', 'ca'], rows: [['Ontario', 10000], ['Québec', 8000]] }
const emptyData = { columns: [], rows: [] }

describe('TileRenderer', () => {
  it('renders KPI tile with value', () => {
    render(<TileRenderer type="kpi" title="CA total" data={kpiData} />)
    expect(screen.getByTestId('tile-kpi')).toBeInTheDocument()
    expect(screen.getByTestId('tile-kpi').textContent).toContain('42000')
  })

  it('renders table tile with column headers', () => {
    render(<TileRenderer type="table" title="CA par région" data={tableData} />)
    expect(screen.getByTestId('tile-table')).toBeInTheDocument()
    expect(screen.getByText('région')).toBeInTheDocument()
    expect(screen.getByText('ca')).toBeInTheDocument()
  })

  it('renders table data rows', () => {
    render(<TileRenderer type="table" title="Données" data={tableData} />)
    expect(screen.getByText('Ontario')).toBeInTheDocument()
    expect(screen.getByText('Québec')).toBeInTheDocument()
  })

  it('renders unknown type message', () => {
    render(<TileRenderer type="unknown_xyz" title="Test" data={emptyData} />)
    expect(screen.getByTestId('tile-unknown')).toBeInTheDocument()
    expect(screen.getByTestId('tile-unknown').textContent).toContain('unknown_xyz')
  })

  it('renders KPI with dash when no data', () => {
    render(<TileRenderer type="kpi" title="Vide" data={emptyData} />)
    expect(screen.getByTestId('tile-kpi').textContent).toContain('—')
  })
})
