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
