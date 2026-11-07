import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MapAdm2 } from '../components/MapAdm2'

// maplibre-gl, pmtiles, echarts are mocked globally in setup.ts

vi.mock('maplibre-gl/dist/maplibre-gl.css', () => ({}))

vi.mock('../hooks/useLocale', () => ({
  useLocale: () => ({ t: (k: string) => k, locale: 'fr' }),
}))

// ── Fixtures ──────────────────────────────────────────────────────────────────

const MOCK_DATA = {
  columns: ['district', 'population'],
  rows: [
    ['Djibouti', 591000],
    ['Ali Sabieh', 108000],
  ],
}

const MOCK_FC = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      properties: { name: 'Djibouti', population_est: 591000 },
      geometry: { type: 'Polygon', coordinates: [[[43.1,11.5],[43.2,11.5],[43.2,11.6],[43.1,11.6],[43.1,11.5]]] },
    },
    {
      type: 'Feature',
      properties: { name: 'Ali Sabieh', population_est: 108000 },
      geometry: { type: 'Polygon', coordinates: [[[43.0,11.0],[43.1,11.0],[43.1,11.1],[43.0,11.1],[43.0,11.0]]] },
    },
  ],
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('MapAdm2', () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(MOCK_FC),
    })
  })

  it('renders map container', () => {
    render(<MapAdm2 data={MOCK_DATA} title="Population" />)
    expect(screen.getByTestId('tile-map-adm2')).toBeDefined()
  })

  it('shows ADM2 and quartiers toggle buttons by default', () => {
    render(<MapAdm2 data={MOCK_DATA} title="Pop" />)
    expect(screen.getByTestId('map-level-btn-adm2')).toBeDefined()
    expect(screen.getByTestId('map-level-btn-quartiers')).toBeDefined()
  })

  it('hides toggle when showLevelToggle=false', () => {
    render(<MapAdm2 data={MOCK_DATA} title="Pop" options={{ showLevelToggle: false }} />)
    expect(screen.queryByTestId('map-level-btn-adm2')).toBeNull()
  })

  it('switches to quartiers level on button click', () => {
    render(<MapAdm2 data={MOCK_DATA} title="Pop" />)
    const btn = screen.getByTestId('map-level-btn-quartiers')
    fireEvent.click(btn)
    expect(global.fetch).toHaveBeenCalledWith(expect.stringContaining('quartiers'))
  })

  it('fetches adm2 geo on mount', () => {
    render(<MapAdm2 data={MOCK_DATA} title="Pop" />)
    expect(global.fetch).toHaveBeenCalledWith('/api/v1/geo/dj/adm2')
  })

  it('shows error message when fetch fails', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('network error'))
    render(<MapAdm2 data={MOCK_DATA} title="Pop" />)
    await new Promise(r => setTimeout(r, 10))
    expect(screen.getByTestId('map-geo-error')).toBeDefined()
  })
})
