import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { SpatialAnalysis } from '../components/SpatialAnalysis'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

const TYPES_RESPONSE = {
  analyses: [
    { id: 'buffer', description: 'Features within radius_km of a reference point.' },
    { id: 'intersection', description: 'Feature pairs that intersect between two layers.' },
    { id: 'density', description: 'Value-per-area density for each polygon feature.' },
  ],
}

const LAYERS_RESPONSE = {
  layers: [
    { id: 'dj_adm2', name_fr: 'Districts de Djibouti (ADM2)', name_en: 'Djibouti Districts', enabled: true },
    { id: 'dj_quartiers', name_fr: 'Quartiers de Djibouti-Ville', name_en: 'Djibouti City Neighbourhoods', enabled: true },
  ],
}

const BUFFER_RESULT = {
  layer_id: 'dj_adm2',
  analysis: 'buffer',
  row_count: 2,
  results: [
    { name: 'Djibouti', dist_m: 0 },
    { name: 'Arta', dist_m: 42000 },
  ],
}

const INTERSECTION_RESULT = {
  layer_id: 'dj_adm2',
  analysis: 'intersection',
  layer_id_b: 'dj_quartiers',
  row_count: 11,
  results: Array.from({ length: 11 }, (_, i) => ({
    feature_a: 'Djibouti',
    feature_b: `Quartier ${i + 1}`,
    overlap_km2: 1.5,
  })),
}

beforeEach(() => {
  mockFetch.mockReset()
  // Default: types + layers
  mockFetch.mockImplementation((url: string) => {
    if (url.includes('/types')) {
      return Promise.resolve({ ok: true, json: async () => TYPES_RESPONSE })
    }
    if (url.includes('/catalog')) {
      return Promise.resolve({ ok: true, json: async () => LAYERS_RESPONSE })
    }
    return Promise.resolve({ ok: false, status: 500, json: async () => ({ detail: 'err' }) })
  })
})

describe('SpatialAnalysis', () => {
  it('renders without crash', async () => {
    render(<SpatialAnalysis apiKey="test-viewer-key-s6" />)
    await waitFor(() => {
      expect(screen.getByTestId('spatial-analysis')).toBeDefined()
    })
  })

  it('shows analysis type selector', async () => {
    render(<SpatialAnalysis apiKey="test-viewer-key-s6" />)
    await waitFor(() => {
      expect(screen.getByTestId('spatial-analysis-type')).toBeDefined()
    })
  })

  it('shows layer selector populated from catalog', async () => {
    render(<SpatialAnalysis apiKey="test-viewer-key-s6" />)
    await waitFor(() => {
      const sel = screen.getByTestId('spatial-analysis-layer-a') as HTMLSelectElement
      expect(sel.options.length).toBeGreaterThan(1)
    })
  })

  it('shows buffer params (lon/lat/radius) when buffer selected', async () => {
    render(<SpatialAnalysis apiKey="test-viewer-key-s6" />)
    await waitFor(() => expect(screen.getByTestId('spatial-analysis-type')).toBeDefined())
    fireEvent.change(screen.getByTestId('spatial-analysis-type'), { target: { value: 'buffer' } })
    expect(screen.getByTestId('spatial-analysis-lon')).toBeDefined()
    expect(screen.getByTestId('spatial-analysis-lat')).toBeDefined()
    expect(screen.getByTestId('spatial-analysis-radius')).toBeDefined()
  })

  it('shows layer B selector when intersection selected', async () => {
    render(<SpatialAnalysis apiKey="test-viewer-key-s6" />)
    await waitFor(() => expect(screen.getByTestId('spatial-analysis-type')).toBeDefined())
    fireEvent.change(screen.getByTestId('spatial-analysis-type'), { target: { value: 'intersection' } })
    expect(screen.getByTestId('spatial-analysis-layer-b')).toBeDefined()
  })

  it('shows value_col input when density selected', async () => {
    render(<SpatialAnalysis apiKey="test-viewer-key-s6" />)
    await waitFor(() => expect(screen.getByTestId('spatial-analysis-type')).toBeDefined())
    fireEvent.change(screen.getByTestId('spatial-analysis-type'), { target: { value: 'density' } })
    expect(screen.getByTestId('spatial-analysis-value-col')).toBeDefined()
  })

  it('shows error when run without layer A', async () => {
    render(<SpatialAnalysis apiKey="test-viewer-key-s6" />)
    await waitFor(() => expect(screen.getByTestId('spatial-analysis-run')).toBeDefined())
    fireEvent.click(screen.getByTestId('spatial-analysis-run'))
    expect(screen.getByTestId('spatial-analysis-error')).toBeDefined()
  })

  it('shows buffer results after successful run', async () => {
    mockFetch.mockImplementation((url: string, opts?: RequestInit) => {
      if (url.includes('/types')) return Promise.resolve({ ok: true, json: async () => TYPES_RESPONSE })
      if (url.includes('/catalog')) return Promise.resolve({ ok: true, json: async () => LAYERS_RESPONSE })
      if (url.includes('/analyze') && (opts?.method === 'POST')) {
        return Promise.resolve({ ok: true, json: async () => BUFFER_RESULT })
      }
      return Promise.resolve({ ok: false, status: 500, json: async () => ({}) })
    })

    render(<SpatialAnalysis apiKey="test-viewer-key-s6" />)
    await waitFor(() => expect(screen.getByTestId('spatial-analysis-layer-a')).toBeDefined())

    fireEvent.change(screen.getByTestId('spatial-analysis-layer-a'), { target: { value: 'dj_adm2' } })
    fireEvent.click(screen.getByTestId('spatial-analysis-run'))

    await waitFor(() => {
      expect(screen.getByTestId('spatial-analysis-results')).toBeDefined()
    })
  })

  it('shows intersection results after successful run', async () => {
    mockFetch.mockImplementation((url: string, opts?: RequestInit) => {
      if (url.includes('/types')) return Promise.resolve({ ok: true, json: async () => TYPES_RESPONSE })
      if (url.includes('/catalog')) return Promise.resolve({ ok: true, json: async () => LAYERS_RESPONSE })
      if (url.includes('/analyze') && opts?.method === 'POST') {
        return Promise.resolve({ ok: true, json: async () => INTERSECTION_RESULT })
      }
      return Promise.resolve({ ok: false, status: 500, json: async () => ({}) })
    })

    render(<SpatialAnalysis apiKey="test-viewer-key-s6" />)
    await waitFor(() => expect(screen.getByTestId('spatial-analysis-type')).toBeDefined())

    fireEvent.change(screen.getByTestId('spatial-analysis-type'), { target: { value: 'intersection' } })
    await waitFor(() => expect(screen.getByTestId('spatial-analysis-layer-b')).toBeDefined())

    fireEvent.change(screen.getByTestId('spatial-analysis-layer-a'), { target: { value: 'dj_adm2' } })
    fireEvent.change(screen.getByTestId('spatial-analysis-layer-b'), { target: { value: 'dj_quartiers' } })
    fireEvent.click(screen.getByTestId('spatial-analysis-run'))

    await waitFor(() => {
      expect(screen.getByTestId('spatial-analysis-results')).toBeDefined()
    })
  })

  it('shows error on intersection without layer B', async () => {
    render(<SpatialAnalysis apiKey="test-viewer-key-s6" />)
    await waitFor(() => expect(screen.getByTestId('spatial-analysis-type')).toBeDefined())

    fireEvent.change(screen.getByTestId('spatial-analysis-type'), { target: { value: 'intersection' } })
    await waitFor(() => expect(screen.getByTestId('spatial-analysis-layer-b')).toBeDefined())

    fireEvent.change(screen.getByTestId('spatial-analysis-layer-a'), { target: { value: 'dj_adm2' } })
    // Do NOT set layer B
    fireEvent.click(screen.getByTestId('spatial-analysis-run'))

    expect(screen.getByTestId('spatial-analysis-error')).toBeDefined()
  })

  it('shows server error on failed analysis', async () => {
    mockFetch.mockImplementation((url: string, opts?: RequestInit) => {
      if (url.includes('/types')) return Promise.resolve({ ok: true, json: async () => TYPES_RESPONSE })
      if (url.includes('/catalog')) return Promise.resolve({ ok: true, json: async () => LAYERS_RESPONSE })
      if (url.includes('/analyze') && opts?.method === 'POST') {
        return Promise.resolve({ ok: false, status: 400, json: async () => ({ detail: 'Unknown layer' }) })
      }
      return Promise.resolve({ ok: false, json: async () => ({}) })
    })

    render(<SpatialAnalysis apiKey="test-viewer-key-s6" />)
    await waitFor(() => expect(screen.getByTestId('spatial-analysis-layer-a')).toBeDefined())

    fireEvent.change(screen.getByTestId('spatial-analysis-layer-a'), { target: { value: 'dj_adm2' } })
    fireEvent.click(screen.getByTestId('spatial-analysis-run'))

    await waitFor(() => {
      expect(screen.getByTestId('spatial-analysis-error')).toBeDefined()
    })
  })
})
