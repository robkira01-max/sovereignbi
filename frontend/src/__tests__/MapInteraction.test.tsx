/**
 * Tests for P-026 — Map ↔ Dashboard filter interaction.
 * Verifies: region badge, clear button, fetch URL with ?region=, map tiles excluded.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'

// ── Mocks (hoisted — no module-level variable references) ─────────────────────

vi.mock('../components/MapLibreMap', () => ({
  MapLibreMap: (props: {
    onRegionSelect?: (name: string) => void
    selectedRegion?: string | null
  }) => (
    <div
      data-testid="mock-map"
      data-selected={props.selectedRegion ?? ''}
      onClick={() => props.onRegionSelect?.('Djibouti-ville')}
    />
  ),
}))

vi.mock('../components/MapAdm2', () => ({
  MapAdm2: (props: {
    onRegionSelect?: (name: string) => void
    selectedRegion?: string | null
  }) => (
    <div
      data-testid="mock-map-adm2"
      data-selected={props.selectedRegion ?? ''}
      onClick={() => props.onRegionSelect?.('Ali Sabieh')}
    />
  ),
}))

vi.mock('../components/BivariateChoropleth', () => ({
  BivariateChoropleth: () => <div data-testid="mock-bivariate" />,
}))

vi.mock('../components/TradeFlowMap', () => ({
  TradeFlowMap: () => <div data-testid="mock-trade-flow" />,
}))

// ── Fixtures ──────────────────────────────────────────────────────────────────

const SUMMARY = {
  id: 'test_dash',
  title: 'Test Dashboard',
  scope: 'viewer',
  updated_at: '2026-01-01',
  tags: [],
}

const FULL_DASHBOARD = {
  id: 'test_dash',
  title: 'Test Dashboard',
  scope: 'viewer',
  tiles: [
    { id: 'kpi_tile', title: 'Total', type: 'kpi', sql_pinned: 'SELECT 42', position: 0 },
    { id: 'map_tile', title: 'Map', type: 'map', sql_pinned: 'SELECT region, v FROM t', position: 1 },
  ],
}

const KPI_DATA  = { columns: ['total'], rows: [[42]],                           error: null }
const MAP_DATA  = { columns: ['region', 'v'], rows: [['Djibouti-ville', 10]], error: null }

function setupFetch() {
  const fetchMock = vi.fn((url: string | Request) => {
    const u = String(typeof url === 'string' ? url : (url as Request).url)

    if (/\/dashboards$/.test(u)) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ dashboards: [SUMMARY] }) })
    }
    if (/\/dashboards\/test_dash$/.test(u)) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(FULL_DASHBOARD) })
    }
    if (u.includes('freshness')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ age_seconds: 10, stale: false }) })
    }
    if (u.includes('insight')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ insight: '', tile_id: '', cached: true }) })
    }
    if (u.includes('map_tile/data')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(MAP_DATA) })
    }
    if (u.includes('kpi_tile/data')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(KPI_DATA) })
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      getItem: (k: string) => (k === 'mizan_api_key' ? 'test-key' : null),
      setItem: () => {},
      removeItem: () => {},
    },
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

// ── Helper ────────────────────────────────────────────────────────────────────

import { DashboardPage } from '../pages/DashboardPage'

async function renderAndOpen() {
  const fetchMock = setupFetch()
  render(<DashboardPage />)
  const btn = await screen.findByText('Test Dashboard', {}, { timeout: 3000 })
  fireEvent.click(btn)
  await screen.findByTestId('mock-map', {}, { timeout: 3000 })
  return fetchMock
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('Map ↔ Dashboard region filter (P-026)', () => {

  it('region filter badge is not shown before any region click', async () => {
    setupFetch()
    render(<DashboardPage />)
    // Initial render + dashboard list load — badge must not be there
    await waitFor(() => expect(screen.queryByText('Test Dashboard')).not.toBeNull())
    expect(screen.queryByTestId('region-filter-badge')).toBeNull()
  })

  it('badge appears with region name after clicking a map tile region', async () => {
    await renderAndOpen()

    act(() => { fireEvent.click(screen.getByTestId('mock-map')) })

    const badge = await screen.findByTestId('region-filter-badge', {}, { timeout: 3000 })
    expect(badge.textContent).toContain('Djibouti-ville')
  })

  it('clear button in badge removes the region filter', async () => {
    await renderAndOpen()

    act(() => { fireEvent.click(screen.getByTestId('mock-map')) })
    await screen.findByTestId('region-filter-badge', {}, { timeout: 3000 })

    act(() => { fireEvent.click(screen.getByTestId('region-filter-clear')) })

    await waitFor(() => expect(screen.queryByTestId('region-filter-badge')).toBeNull())
  })

  it('clicking the same region a second time deselects it (toggle off)', async () => {
    await renderAndOpen()

    const mockMap = screen.getByTestId('mock-map')
    act(() => { fireEvent.click(mockMap) })
    await screen.findByTestId('region-filter-badge', {}, { timeout: 3000 })

    act(() => { fireEvent.click(mockMap) })
    await waitFor(() => expect(screen.queryByTestId('region-filter-badge')).toBeNull())
  })

  it('non-map tile fetch URL includes ?region= when a region is selected', async () => {
    const fetchMock = await renderAndOpen()

    act(() => { fireEvent.click(screen.getByTestId('mock-map')) })
    await screen.findByTestId('region-filter-badge', {}, { timeout: 3000 })

    await waitFor(
      () => {
        const urls = fetchMock.mock.calls.map(([u]) => String(u))
        expect(urls.some(u => u.includes('kpi_tile') && u.includes('region='))).toBe(true)
      },
      { timeout: 3000 },
    )
  })

  it('map tile fetch URL does NOT include ?region= (maps are excluded from filtering)', async () => {
    const fetchMock = await renderAndOpen()

    act(() => { fireEvent.click(screen.getByTestId('mock-map')) })
    await screen.findByTestId('region-filter-badge', {}, { timeout: 3000 })

    await waitFor(
      () => {
        const urls = fetchMock.mock.calls.map(([u]) => String(u))
        // At least one kpi call with region= must exist before we check the map
        expect(urls.some(u => u.includes('kpi_tile') && u.includes('region='))).toBe(true)
      },
      { timeout: 3000 },
    )

    const urls = fetchMock.mock.calls.map(([u]) => String(u))
    expect(urls.filter(u => u.includes('map_tile') && u.includes('region=')).length).toBe(0)
  })

  it('selectedRegion is passed down to the map tile component as data-selected', async () => {
    await renderAndOpen()

    act(() => { fireEvent.click(screen.getByTestId('mock-map')) })

    await waitFor(() => {
      expect(screen.getByTestId('mock-map').getAttribute('data-selected')).toBe('Djibouti-ville')
    })
  })

  it('going back and re-opening a dashboard clears the previous region selection', async () => {
    setupFetch()
    render(<DashboardPage />)
    const btn = await screen.findByText('Test Dashboard', {}, { timeout: 3000 })

    // Open dashboard, select region
    fireEvent.click(btn)
    await screen.findByTestId('mock-map', {}, { timeout: 3000 })
    act(() => { fireEvent.click(screen.getByTestId('mock-map')) })
    await screen.findByTestId('region-filter-badge', {}, { timeout: 3000 })

    // Navigate back to list
    const backBtn = screen.getByText('← Retour')
    act(() => { fireEvent.click(backBtn) })

    // Re-open — region must be cleared by openDashboard's setSelectedRegion(null)
    const btn2 = await screen.findByText('Test Dashboard', {}, { timeout: 3000 })
    act(() => { fireEvent.click(btn2) })
    await screen.findByTestId('mock-map', {}, { timeout: 3000 })

    expect(screen.queryByTestId('region-filter-badge')).toBeNull()
  })
})
