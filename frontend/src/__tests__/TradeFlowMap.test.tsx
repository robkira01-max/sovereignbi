import { describe, it, expect, vi, beforeAll } from 'vitest'
import { render } from '@testing-library/react'
import { TRADE_FLOWS, MAX_TONNAGE_K, PORT_DJIBOUTI } from '../data/trade_flows'

// Mock maplibre-gl and pmtiles (require canvas/WebGL not available in jsdom)
vi.mock('maplibre-gl', () => ({
  default: {
    Map: vi.fn(() => ({
      addControl: vi.fn(),
      on: vi.fn(),
      remove: vi.fn(),
      project: vi.fn(() => ({ x: 100, y: 100 })),
      isStyleLoaded: vi.fn(() => false),
    })),
    NavigationControl: vi.fn(),
    AttributionControl: vi.fn(),
    addProtocol: vi.fn(),
  },
  Map: vi.fn(() => ({
    addControl: vi.fn(),
    on: vi.fn(),
    remove: vi.fn(),
    project: vi.fn(() => ({ x: 100, y: 100 })),
    isStyleLoaded: vi.fn(() => false),
  })),
  NavigationControl: vi.fn(),
  AttributionControl: vi.fn(),
  addProtocol: vi.fn(),
}))

vi.mock('pmtiles', () => ({
  Protocol: vi.fn(() => ({ tile: vi.fn() })),
}))

vi.mock('maplibre-gl/dist/maplibre-gl.css', () => ({}))

beforeAll(() => {
  // jsdom doesn't implement requestAnimationFrame — provide stub
  globalThis.requestAnimationFrame = vi.fn(cb => { cb(0); return 0 })
  globalThis.cancelAnimationFrame  = vi.fn()
})

describe('TRADE_FLOWS data', () => {
  it('has exactly 5 corridors', () => {
    expect(TRADE_FLOWS).toHaveLength(5)
  })

  it('all flows originate from Port de Djibouti', () => {
    for (const flow of TRADE_FLOWS) {
      expect(flow.from[0]).toBeCloseTo(PORT_DJIBOUTI[0], 2)
      expect(flow.from[1]).toBeCloseTo(PORT_DJIBOUTI[1], 2)
    }
  })

  it('tonnageK values are positive', () => {
    for (const flow of TRADE_FLOWS) {
      expect(flow.tonnageK).toBeGreaterThan(0)
    }
  })

  it('MAX_TONNAGE_K equals the largest flow', () => {
    const max = Math.max(...TRADE_FLOWS.map(f => f.tonnageK))
    expect(MAX_TONNAGE_K).toBe(max)
  })

  it('all colors are hex strings', () => {
    const hex = /^#[0-9a-fA-F]{6}$/
    for (const flow of TRADE_FLOWS) {
      expect(flow.color).toMatch(hex)
    }
  })

  it('ids are unique', () => {
    const ids = TRADE_FLOWS.map(f => f.id)
    expect(new Set(ids).size).toBe(ids.length)
  })
})

describe('TradeFlowMap component', () => {
  it('renders without crashing', async () => {
    const { TradeFlowMap } = await import('../components/TradeFlowMap')
    const { container } = render(<TradeFlowMap />)
    expect(container).toBeTruthy()
  })

  it('renders the tile testid', async () => {
    const { TradeFlowMap } = await import('../components/TradeFlowMap')
    const { getByTestId } = render(<TradeFlowMap />)
    expect(getByTestId('tile-trade-flow')).toBeTruthy()
  })
})
