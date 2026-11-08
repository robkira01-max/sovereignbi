import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { GeoCatalog } from '../components/GeoCatalog'

vi.mock('../hooks/useLocale', () => ({
  useLocale: () => ({ t: (k: string) => k, locale: 'fr' }),
}))

// ── Fixtures ──────────────────────────────────────────────────────────────────

const LAYER_ADM1 = {
  id: 'dj_adm1',
  name_fr: 'Régions de Djibouti (ADM1)',
  name_en: 'Djibouti Regions (ADM1)',
  description_fr: '6 régions administratives',
  description_en: '6 administrative regions',
  format: 'geojson',
  geometry_type: 'Polygon',
  source: 'GADM v4.1',
  license: 'CC BY 4.0',
  license_url: 'https://gadm.org/license.html',
  date_acquired: '2026-10-01',
  coverage: 'Djibouti — national',
  feature_count: 6,
  status: 'validated',
  warnings: [],
  api_endpoint: '/api/v1/geo/dj/adm1',
  enabled: true,
}

const LAYER_QUARTIERS = {
  id: 'dj_quartiers',
  name_fr: 'Quartiers de Djibouti-Ville',
  name_en: 'Djibouti City Neighbourhoods',
  description_fr: '11 quartiers approximatifs',
  description_en: '11 approximate neighbourhoods',
  format: 'geojson',
  geometry_type: 'Polygon',
  source: 'OpenStreetMap',
  license: 'ODbL 1.0',
  license_url: 'https://opendatacommons.org/licenses/odbl/1-0/',
  date_acquired: '2026-10-01',
  coverage: 'Djibouti-Ville',
  feature_count: 11,
  status: 'draft',
  warnings: [
    { fr: 'Délimitations approximatives', en: 'Approximate boundaries' },
  ],
  api_endpoint: '/api/v1/geo/dj/quartiers',
  enabled: true,
}

const CATALOG_RESPONSE = {
  version: '1',
  count: 2,
  layers: [LAYER_ADM1, LAYER_QUARTIERS],
}

const mockFetch = vi.fn()

beforeEach(() => {
  mockFetch.mockReset()
  vi.stubGlobal('fetch', mockFetch)
})

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('GeoCatalog', () => {
  it('shows loading state initially', () => {
    mockFetch.mockReturnValue(new Promise(() => {})) // never resolves
    render(<GeoCatalog apiKey="test-viewer-key-s6" />)
    expect(screen.getByTestId('geo-catalog-loading')).toBeDefined()
  })

  it('renders catalog after fetch', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(CATALOG_RESPONSE),
    })
    render(<GeoCatalog apiKey="test-viewer-key-s6" />)
    await waitFor(() => expect(screen.getByTestId('geo-catalog')).toBeDefined())
  })

  it('renders a card for each layer', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(CATALOG_RESPONSE) })
    render(<GeoCatalog apiKey="test-viewer-key-s6" />)
    await waitFor(() => {
      expect(screen.getByTestId('geo-layer-card-dj_adm1')).toBeDefined()
      expect(screen.getByTestId('geo-layer-card-dj_quartiers')).toBeDefined()
    })
  })

  it('shows validated status badge for ADM1', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(CATALOG_RESPONSE) })
    render(<GeoCatalog apiKey="test-viewer-key-s6" />)
    await waitFor(() => {
      const badge = screen.getByTestId('geo-layer-status-dj_adm1')
      expect(badge.textContent).toContain('geo_catalog.status_validated')
    })
  })

  it('shows draft status badge for quartiers', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(CATALOG_RESPONSE) })
    render(<GeoCatalog apiKey="test-viewer-key-s6" />)
    await waitFor(() => {
      const badge = screen.getByTestId('geo-layer-status-dj_quartiers')
      expect(badge.textContent).toContain('geo_catalog.status_draft')
    })
  })

  it('shows quality warning for quartiers', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(CATALOG_RESPONSE) })
    render(<GeoCatalog apiKey="test-viewer-key-s6" />)
    await waitFor(() => {
      expect(screen.getByTestId('geo-layer-warning-dj_quartiers')).toBeDefined()
    })
  })

  it('no warning element for ADM1 (no warnings)', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(CATALOG_RESPONSE) })
    render(<GeoCatalog apiKey="test-viewer-key-s6" />)
    await waitFor(() => screen.getByTestId('geo-catalog'))
    expect(screen.queryByTestId('geo-layer-warning-dj_adm1')).toBeNull()
  })

  it('shows enabled badge for viewer (not editor toggle)', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(CATALOG_RESPONSE) })
    render(<GeoCatalog apiKey="test-viewer-key-s6" isEditor={false} />)
    await waitFor(() => {
      expect(screen.getByTestId('geo-layer-enabled-badge-dj_adm1')).toBeDefined()
    })
  })

  it('shows toggle button for editor', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(CATALOG_RESPONSE) })
    render(<GeoCatalog apiKey="test-editor-key-s6" isEditor={true} />)
    await waitFor(() => {
      expect(screen.getByTestId('geo-layer-toggle-dj_adm1')).toBeDefined()
    })
  })

  it('calls PUT toggle on button click (editor)', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(CATALOG_RESPONSE) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ id: 'dj_adm1', enabled: false }) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(CATALOG_RESPONSE) })
    render(<GeoCatalog apiKey="test-editor-key-s6" isEditor={true} />)
    await waitFor(() => screen.getByTestId('geo-layer-toggle-dj_adm1'))
    fireEvent.click(screen.getByTestId('geo-layer-toggle-dj_adm1'))
    await waitFor(() => {
      const calls = mockFetch.mock.calls
      const toggleCall = calls.find(c => c[0]?.includes('toggle'))
      expect(toggleCall).toBeDefined()
      expect(toggleCall![1].method).toBe('PUT')
    })
  })

  it('shows error on fetch failure', async () => {
    mockFetch.mockResolvedValue({ ok: false, status: 500 })
    render(<GeoCatalog apiKey="test-viewer-key-s6" />)
    await waitFor(() => expect(screen.getByTestId('geo-catalog-error')).toBeDefined())
  })

  it('renders enabled_only checkbox', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(CATALOG_RESPONSE) })
    render(<GeoCatalog apiKey="test-viewer-key-s6" />)
    await waitFor(() => {
      expect(screen.getByTestId('geo-catalog-enabled-toggle')).toBeDefined()
    })
  })

  it('no layers message when catalog is empty', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ version: '1', count: 0, layers: [] }),
    })
    render(<GeoCatalog apiKey="test-viewer-key-s6" />)
    await waitFor(() => {
      expect(screen.getByText('geo_catalog.no_layers')).toBeDefined()
    })
  })
})
