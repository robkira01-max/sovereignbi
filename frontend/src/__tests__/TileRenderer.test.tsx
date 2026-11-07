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
    // fr-FR locale formats 42000 as "42 000" (narrow non-breaking space)
    expect(screen.getByTestId('tile-kpi').textContent).toMatch(/42[^\d]*000/)
  })

  it('renders table tile with column headers', () => {
    render(<TileRenderer type="table" title="CA par région" data={tableData} />)
    expect(screen.getByTestId('tile-table')).toBeInTheDocument()
    // Headers now include a sort icon — match by testid
    expect(screen.getByTestId('table-col-header-région')).toBeInTheDocument()
    expect(screen.getByTestId('table-col-header-ca')).toBeInTheDocument()
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

  it('renders grid tile (small multiples) with one cell per facet', () => {
    const gridData = {
      columns: ['region', 'annee', 'taux_chomage_pct'],
      rows: [
        ['Djibouti-ville', 2009, 45.0],
        ['Djibouti-ville', 2016, 40.3],
        ['Djibouti-ville', 2024, 35.1],
        ['Ali Sabieh', 2009, 40.0],
        ['Ali Sabieh', 2016, 36.5],
        ['Ali Sabieh', 2024, 32.2],
        ['Arta', 2009, 38.5],
        ['Arta', 2016, 34.1],
        ['Arta', 2024, 29.8],
      ],
    }
    render(
      <TileRenderer
        type="grid"
        title="Chômage régional — 2009–2024"
        data={gridData}
        options={{ facet_by: 'region', x: 'annee', y: 'taux_chomage_pct', chart_type: 'line', unit: '%' }}
      />
    )
    expect(screen.getByTestId('tile-grid')).toBeInTheDocument()
    // Should show one cell per unique region value
    expect(screen.getByText(/Djibouti-ville/)).toBeInTheDocument()
    expect(screen.getByText(/Ali Sabieh/)).toBeInTheDocument()
    expect(screen.getByText(/Arta/)).toBeInTheDocument()
  })

  it('renders grid tile with bar sub-type', () => {
    const gridData = {
      columns: ['region', 'annee', 'valeur'],
      rows: [
        ['Nord', 2020, 10],
        ['Nord', 2021, 12],
        ['Sud', 2020, 8],
        ['Sud', 2021, 9],
      ],
    }
    render(
      <TileRenderer
        type="grid"
        title="Indicateur par région"
        data={gridData}
        options={{ facet_by: 'region', x: 'annee', y: 'valeur', chart_type: 'bar' }}
      />
    )
    expect(screen.getByTestId('tile-grid')).toBeInTheDocument()
    expect(screen.getByText('Nord')).toBeInTheDocument()
    expect(screen.getByText('Sud')).toBeInTheDocument()
  })

  it('renders map tile (choropleth) with data-testid', () => {
    const mapData = {
      columns: ['region', 'taux_chomage_pct'],
      rows: [
        ['Djibouti-ville', 25.3],
        ['Ali Sabieh', 31.1],
        ['Arta', 28.0],
        ['Dikhil', 33.4],
        ['Tadjourah', 29.5],
        ['Obock', 27.8],
      ],
    }
    render(<TileRenderer type="map" title="Chômage par région" data={mapData} options={{ unit: '%', colorScheme: 'red' }} />)
    expect(screen.getByTestId('tile-map')).toBeInTheDocument()
  })

  it('renders map-bivariate tile with data-testid', () => {
    const bivData = {
      columns: ['region', 'taux_pauvrete_pct', 'taux_chomage_pct'],
      rows: [
        ['Djibouti-ville', 18.2, 25.3],
        ['Ali Sabieh',     42.1, 31.1],
        ['Arta',           35.0, 28.0],
        ['Dikhil',         48.5, 33.4],
        ['Tadjourah',      38.2, 29.5],
        ['Obock',          40.1, 27.8],
      ],
    }
    render(
      <TileRenderer
        type="map-bivariate"
        title="Pauvreté × Chômage"
        data={bivData}
        options={{ unit: '%', x1_label: 'Pauvreté', x2_label: 'Chômage', colorScheme: 'classic' }}
      />
    )
    expect(screen.getByTestId('tile-map-bivariate')).toBeInTheDocument()
  })

  it('renders map-bivariate with teal-orange palette', () => {
    const bivData = {
      columns: ['region', 'var1', 'var2'],
      rows: [
        ['Djibouti-ville', 10, 20],
        ['Ali Sabieh', 30, 40],
        ['Arta', 50, 60],
        ['Dikhil', 70, 80],
        ['Tadjourah', 90, 10],
        ['Obock', 20, 50],
      ],
    }
    render(
      <TileRenderer type="map-bivariate" title="Test bivariée" data={bivData}
        options={{ colorScheme: 'teal-orange' }} />
    )
    expect(screen.getByTestId('tile-map-bivariate')).toBeInTheDocument()
  })
})
