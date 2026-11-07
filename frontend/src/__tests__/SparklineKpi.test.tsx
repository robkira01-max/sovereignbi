import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SparklineKpi } from '../components/SparklineKpi'

describe('SparklineKpi', () => {
  it('renders current value', () => {
    render(<SparklineKpi points={[10, 12, 15]} current={15} />)
    expect(screen.getByTestId('sparkline-current')).toBeTruthy()
    expect(screen.getByTestId('sparkline-current').textContent).toContain('15')
  })

  it('renders up badge with positive deltaPct', () => {
    render(
      <SparklineKpi
        points={[10, 12, 15]}
        current={15}
        previous={12}
        deltaPct={25.0}
        direction="up"
      />
    )
    const badge = screen.getByTestId('sparkline-badge')
    expect(badge.textContent).toContain('↑')
    expect(badge.textContent).toContain('+25.0%')
  })

  it('renders down badge with negative deltaPct', () => {
    render(
      <SparklineKpi
        points={[20, 15, 10]}
        current={10}
        previous={15}
        deltaPct={-33.33}
        direction="down"
      />
    )
    const badge = screen.getByTestId('sparkline-badge')
    expect(badge.textContent).toContain('↓')
    expect(badge.textContent).toContain('-33.3%')
  })

  it('renders SVG sparkline with 2+ points', () => {
    render(<SparklineKpi points={[5, 10, 8, 12]} current={12} />)
    const svg = screen.getByTestId('sparkline-svg')
    expect(svg).toBeTruthy()
    expect(svg.querySelector('path')).toBeTruthy()
    expect(screen.getByTestId('sparkline-dot')).toBeTruthy()
  })

  it('does not render SVG with single point', () => {
    render(<SparklineKpi points={[42]} current={42} />)
    expect(screen.queryByTestId('sparkline-svg')).toBeNull()
  })

  it('renders previous value label when provided', () => {
    render(
      <SparklineKpi
        points={[10, 15]}
        current={15}
        previous={10}
        deltaPct={50}
        direction="up"
      />
    )
    expect(screen.getByTestId('sparkline-previous')).toBeTruthy()
    expect(screen.getByTestId('sparkline-previous').textContent).toContain('10')
  })

  it('renders flat direction with →', () => {
    render(
      <SparklineKpi
        points={[5, 5, 5]}
        current={5}
        previous={5}
        deltaPct={0}
        direction="flat"
      />
    )
    const badge = screen.getByTestId('sparkline-badge')
    expect(badge.textContent).toContain('→')
  })

  it('SVG title attribute contains label', () => {
    render(
      <SparklineKpi
        points={[1, 2, 3]}
        current={3}
        label="Chômage (%)"
      />
    )
    const title = screen.getByTestId('sparkline-svg').querySelector('title')
    expect(title?.textContent).toContain('Chômage (%)')
  })
})
