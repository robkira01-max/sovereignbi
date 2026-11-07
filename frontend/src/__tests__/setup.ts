import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Recharts ResponsiveContainer uses ResizeObserver — not available in jsdom
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
;(globalThis as any).ResizeObserver = ResizeObserverMock

// ECharts requires a real canvas/SVG environment — mock it for jsdom tests
vi.mock('echarts', () => ({
  default: {
    init: vi.fn(() => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() })),
    registerMap: vi.fn(),
    getMap: vi.fn(() => null),
  },
  init: vi.fn(() => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() })),
  registerMap: vi.fn(),
  getMap: vi.fn(() => null),
}))

// MapLibre GL uses WebGL/workers — mock for jsdom
vi.mock('maplibre-gl', () => {
  const mockMap = {
    on: vi.fn(),
    once: vi.fn(),
    addControl: vi.fn(),
    addSource: vi.fn(),
    addLayer: vi.fn(),
    removeLayer: vi.fn(),
    removeSource: vi.fn(),
    getSource: vi.fn(() => null),
    getLayer: vi.fn(() => null),
    getCanvas: vi.fn(() => ({ style: {} })),
    isStyleLoaded: vi.fn(() => false),
    setPaintProperty: vi.fn(),
    flyTo: vi.fn(),
    remove: vi.fn(),
  }
  return {
    default: {
      Map: vi.fn(() => mockMap),
      NavigationControl: vi.fn(),
      AttributionControl: vi.fn(),
      Popup: vi.fn(() => ({ setLngLat: vi.fn().mockReturnThis(), setHTML: vi.fn().mockReturnThis(), addTo: vi.fn(), remove: vi.fn() })),
      addProtocol: vi.fn(),
    },
    Map: vi.fn(() => mockMap),
    NavigationControl: vi.fn(),
    AttributionControl: vi.fn(),
    Popup: vi.fn(() => ({ setLngLat: vi.fn().mockReturnThis(), setHTML: vi.fn().mockReturnThis(), addTo: vi.fn(), remove: vi.fn() })),
    addProtocol: vi.fn(),
  }
})

// PMTiles Protocol — mock for jsdom
vi.mock('pmtiles', () => ({
  Protocol: vi.fn(() => ({ tile: vi.fn() })),
}))
