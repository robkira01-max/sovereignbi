import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { GeoImport } from '../components/GeoImport'

// Mock fetch globally
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Minimal valid response
const SUCCESS_RESPONSE = {
  layer: {
    id: 'import_zone_test_123456',
    name_fr: 'Zone Test',
    feature_count: 2,
    geometry_type: 'POLYGON',
    status: 'draft',
    enabled: false,
  },
}

function makeFile(name = 'zone.geojson', type = 'application/geo+json', size = 100): File {
  const content = new Uint8Array(size)
  return new File([content], name, { type })
}

beforeEach(() => {
  mockFetch.mockReset()
})

describe('GeoImport', () => {
  it('renders title and dropzone', () => {
    render(<GeoImport apiKey="test-editor-key-s6" />)
    expect(screen.getByTestId('geo-import')).toBeDefined()
    expect(screen.getByTestId('geo-import-dropzone')).toBeDefined()
  })

  it('submit button is disabled without file', () => {
    render(<GeoImport apiKey="test-editor-key-s6" />)
    const btn = screen.getByTestId('geo-import-submit') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  it('shows filename after file input change', () => {
    render(<GeoImport apiKey="test-editor-key-s6" />)
    const input = screen.getByTestId('geo-import-file-input') as HTMLInputElement
    const file = makeFile('regions.geojson')
    Object.defineProperty(input, 'files', { value: [file], configurable: true })
    fireEvent.change(input)
    expect(screen.getByTestId('geo-import-filename').textContent).toBe('regions.geojson')
  })

  it('shows error for unsupported extension', () => {
    render(<GeoImport apiKey="test-editor-key-s6" />)
    const input = screen.getByTestId('geo-import-file-input') as HTMLInputElement
    const file = makeFile('regions.shp', 'application/octet-stream')
    Object.defineProperty(input, 'files', { value: [file], configurable: true })
    fireEvent.change(input)
    expect(screen.getByTestId('geo-import-error')).toBeDefined()
  })

  it('shows error for oversized file', () => {
    render(<GeoImport apiKey="test-editor-key-s6" />)
    const input = screen.getByTestId('geo-import-file-input') as HTMLInputElement
    const big = makeFile('big.geojson', 'application/geo+json', 51 * 1024 * 1024)
    Object.defineProperty(input, 'files', { value: [big], configurable: true })
    fireEvent.change(input)
    expect(screen.getByTestId('geo-import-error')).toBeDefined()
  })

  it('submits form and shows success result', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => SUCCESS_RESPONSE,
    })

    render(<GeoImport apiKey="test-editor-key-s6" />)
    const input = screen.getByTestId('geo-import-file-input') as HTMLInputElement
    const file = makeFile('zone.geojson')
    Object.defineProperty(input, 'files', { value: [file], configurable: true })
    fireEvent.change(input)

    // Set required name_fr
    fireEvent.change(screen.getByTestId('geo-import-name-fr'), { target: { value: 'Zone Test' } })

    fireEvent.click(screen.getByTestId('geo-import-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('geo-import-success')).toBeDefined()
    })
    expect(screen.getByTestId('geo-import-result-id').textContent).toBe('import_zone_test_123456')
    expect(screen.getByTestId('geo-import-result-features').textContent).toBe('2')
  })

  it('shows server error on 500', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Internal error' }),
    })

    render(<GeoImport apiKey="test-editor-key-s6" />)
    const input = screen.getByTestId('geo-import-file-input') as HTMLInputElement
    const file = makeFile('zone.geojson')
    Object.defineProperty(input, 'files', { value: [file], configurable: true })
    fireEvent.change(input)
    fireEvent.change(screen.getByTestId('geo-import-name-fr'), { target: { value: 'Z' } })
    fireEvent.click(screen.getByTestId('geo-import-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('geo-import-error')).toBeDefined()
    })
  })

  it('shows validation error from server on 400', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Cannot read geographic file: bad format' }),
    })

    render(<GeoImport apiKey="test-editor-key-s6" />)
    const input = screen.getByTestId('geo-import-file-input') as HTMLInputElement
    const file = makeFile('bad.geojson')
    Object.defineProperty(input, 'files', { value: [file], configurable: true })
    fireEvent.change(input)
    fireEvent.change(screen.getByTestId('geo-import-name-fr'), { target: { value: 'Bad' } })
    fireEvent.click(screen.getByTestId('geo-import-submit'))

    await waitFor(() => {
      expect(screen.getByTestId('geo-import-error').textContent).toContain('Cannot read')
    })
  })

  it('calls onImported callback on success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: async () => SUCCESS_RESPONSE,
    })
    const onImported = vi.fn()
    render(<GeoImport apiKey="test-editor-key-s6" onImported={onImported} />)
    const input = screen.getByTestId('geo-import-file-input') as HTMLInputElement
    const file = makeFile('zone.geojson')
    Object.defineProperty(input, 'files', { value: [file], configurable: true })
    fireEvent.change(input)
    fireEvent.change(screen.getByTestId('geo-import-name-fr'), { target: { value: 'Zone' } })
    fireEvent.click(screen.getByTestId('geo-import-submit'))

    await waitFor(() => expect(onImported).toHaveBeenCalledOnce())
    expect(onImported.mock.calls[0][0].id).toBe('import_zone_test_123456')
  })

  it('renders all metadata input fields', () => {
    render(<GeoImport apiKey="test-editor-key-s6" />)
    expect(screen.getByTestId('geo-import-name-fr')).toBeDefined()
    expect(screen.getByTestId('geo-import-name-en')).toBeDefined()
    expect(screen.getByTestId('geo-import-desc-fr')).toBeDefined()
    expect(screen.getByTestId('geo-import-source')).toBeDefined()
    expect(screen.getByTestId('geo-import-license')).toBeDefined()
    expect(screen.getByTestId('geo-import-coverage')).toBeDefined()
  })
})
