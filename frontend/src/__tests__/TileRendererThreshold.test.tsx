import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TileRenderer } from '../components/TileRenderer'

const kpiData = { columns: ['valeur'], rows: [[25]] }

describe('TileRenderer — traffic-light thresholds', () => {
  const thresholds = [
    { op: '>=', value: 30, color: '#ef4444', label: 'Critique' },
    { op: '>=', value: 20, color: '#f59e0b', label: 'Élevé' },
    { color: '#22c55e', label: 'Normal' },
  ]

  it('applies threshold color to KPI value', () => {
    render(
      <TileRenderer
        type="kpi"
        title="Chômage"
        data={kpiData}
        options={{ thresholds }}
      />
    )
    const el = screen.getByTestId('tile-kpi-value')
    // 25 → Élevé → #f59e0b; jsdom normalises hex to rgb
    expect(el.style.color).toMatch(/f59e0b|245.*158.*11/i)
  })

  it('uses brand color when no thresholds', () => {
    render(
      <TileRenderer type="kpi" title="Chômage" data={kpiData} />
    )
    const el = screen.getByTestId('tile-kpi-value')
    expect(el.style.color).toBe('var(--brand)')
  })

  it('applies first-match rule (>= 30 → Critique)', () => {
    render(
      <TileRenderer
        type="kpi"
        title="Test"
        data={{ columns: ['v'], rows: [[35]] }}
        options={{ thresholds }}
      />
    )
    const el = screen.getByTestId('tile-kpi-value')
    expect(el.style.color).toMatch(/ef4444|239.*68.*68/i)
  })

  it('falls back to default rule when no op matches', () => {
    render(
      <TileRenderer
        type="kpi"
        title="Test"
        data={{ columns: ['v'], rows: [[5]] }}
        options={{ thresholds }}
      />
    )
    const el = screen.getByTestId('tile-kpi-value')
    // 5 is below both >=30 and >=20 → default Normal → #22c55e
    expect(el.style.color).toMatch(/22c55e|34.*197.*94/i)
  })
})
