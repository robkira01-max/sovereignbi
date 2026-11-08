import { describe, it, expect, vi, beforeAll } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ScrollySection } from '../components/ScrollySection'

// IntersectionObserver is not available in jsdom
class MockIntersectionObserver {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}
vi.stubGlobal('IntersectionObserver', MockIntersectionObserver)

// GeoJSON import — returns a minimal valid FeatureCollection for ScrollyPage tests
vi.mock('../data/dji_adm1.geojson', () => ({
  default: {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: { shapeName: 'Obock' },
        geometry: {
          type: 'Polygon',
          coordinates: [[[43.0, 12.0], [44.0, 12.0], [44.0, 11.0], [43.0, 11.0], [43.0, 12.0]]],
        },
      },
    ],
  },
}))

beforeAll(() => {
  globalThis.requestAnimationFrame = vi.fn(cb => { cb(0); return 0 })
  globalThis.cancelAnimationFrame  = vi.fn()
})

const STEPS = [
  { title: 'Étape une', body: 'Contenu de l\'étape une.' },
  { title: 'Étape deux', body: 'Contenu de l\'étape deux.' },
  { title: 'Étape trois', body: 'Contenu de l\'étape trois.' },
]

describe('ScrollySection', () => {
  it('renders without crashing', () => {
    const { container } = render(
      <ScrollySection steps={STEPS} figure={() => <div>Fig</div>} />
    )
    expect(container).toBeTruthy()
  })

  it('renders the section container testid', () => {
    render(<ScrollySection steps={STEPS} figure={() => <div>Fig</div>} />)
    expect(screen.getByTestId('scrolly-section')).toBeTruthy()
  })

  it('renders the sticky figure container', () => {
    render(<ScrollySection steps={STEPS} figure={() => <div>Fig</div>} />)
    expect(screen.getByTestId('scrolly-figure')).toBeTruthy()
  })

  it('renders correct number of step containers', () => {
    render(<ScrollySection steps={STEPS} figure={() => <div>Fig</div>} />)
    for (let i = 0; i < STEPS.length; i++) {
      expect(screen.getByTestId(`scrolly-step-${i}`)).toBeTruthy()
    }
  })

  it('assigns correct data-step-index to each step', () => {
    render(<ScrollySection steps={STEPS} figure={() => <div>Fig</div>} />)
    STEPS.forEach((_, i) => {
      const el = screen.getByTestId(`scrolly-step-${i}`)
      expect(el.getAttribute('data-step-index')).toBe(String(i))
    })
  })

  it('renders step titles', () => {
    render(<ScrollySection steps={STEPS} figure={() => <div>Fig</div>} />)
    expect(screen.getByText('Étape une')).toBeTruthy()
    expect(screen.getByText('Étape deux')).toBeTruthy()
    expect(screen.getByText('Étape trois')).toBeTruthy()
  })

  it('renders figure content via render prop', () => {
    render(
      <ScrollySection
        steps={STEPS}
        figure={i => <div data-testid={`fig-${i}`}>Figure {i}</div>}
      />
    )
    expect(screen.getByTestId('fig-0')).toBeTruthy()
  })

  it('accepts custom figureWidth prop without crashing', () => {
    const { container } = render(
      <ScrollySection steps={STEPS} figure={() => <div />} figureWidth="38%" />
    )
    expect(container).toBeTruthy()
  })
})

describe('ScrollyPage', () => {
  it('renders without crashing', async () => {
    const { ScrollyPage } = await import('../pages/ScrollyPage')
    const { container } = render(<ScrollyPage onNavigate={vi.fn()} />)
    expect(container).toBeTruthy()
  })

  it('renders the report container testid', async () => {
    const { ScrollyPage } = await import('../pages/ScrollyPage')
    render(<ScrollyPage onNavigate={vi.fn()} />)
    expect(screen.getByTestId('scrolly-report')).toBeTruthy()
  })

  it('renders back button', async () => {
    const { ScrollyPage } = await import('../pages/ScrollyPage')
    render(<ScrollyPage onNavigate={vi.fn()} />)
    expect(screen.getByTestId('scrolly-back')).toBeTruthy()
  })

  it('calls onNavigate("home") when back button clicked', async () => {
    const { ScrollyPage } = await import('../pages/ScrollyPage')
    const nav = vi.fn()
    render(<ScrollyPage onNavigate={nav} />)
    screen.getByTestId('scrolly-back').click()
    expect(nav).toHaveBeenCalledWith('home')
  })
})
