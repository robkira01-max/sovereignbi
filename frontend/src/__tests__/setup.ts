import '@testing-library/jest-dom'
import { vi } from 'vitest'

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
