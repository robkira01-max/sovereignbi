import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConfidenceBadge } from '../components/ConfidenceBadge'

describe('ConfidenceBadge', () => {
  it('renders "élevée" with green background', () => {
    render(<ConfidenceBadge confidence={{ score: 0.9, label: 'élevée', explanation: 'Top' }} />)
    const badge = screen.getByTestId('confidence-badge')
    expect(badge).toBeInTheDocument()
    expect(badge.textContent).toContain('élevée')
    expect((badge as HTMLElement).style.backgroundColor).toBe('rgb(22, 163, 74)')
  })

  it('renders "moyenne" with orange background', () => {
    render(<ConfidenceBadge confidence={{ score: 0.6, label: 'moyenne', explanation: 'OK' }} />)
    const badge = screen.getByTestId('confidence-badge')
    expect((badge as HTMLElement).style.backgroundColor).toBe('rgb(217, 119, 6)')
  })

  it('renders "faible" with red background', () => {
    render(<ConfidenceBadge confidence={{ score: 0.3, label: 'faible', explanation: 'Low' }} />)
    const badge = screen.getByTestId('confidence-badge')
    expect((badge as HTMLElement).style.backgroundColor).toBe('rgb(220, 38, 38)')
  })

  it('returns nothing when confidence is null', () => {
    const { container } = render(<ConfidenceBadge confidence={null} />)
    expect(container.firstChild).toBeNull()
  })
})
