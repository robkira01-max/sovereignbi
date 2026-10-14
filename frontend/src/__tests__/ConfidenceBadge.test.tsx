import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConfidenceBadge } from '../components/ConfidenceBadge'

// Rendered outside LocaleProvider → default context uses English (DEFAULT_LOCALE).
// Colors are keyed by the API's French labels ('élevée', 'moyenne', 'faible') — unchanged.

describe('ConfidenceBadge', () => {
  it('renders "élevée" with green background and English label', () => {
    render(<ConfidenceBadge confidence={{ score: 0.9, label: 'élevée', explanation: 'Top' }} />)
    const badge = screen.getByTestId('confidence-badge')
    expect(badge).toBeInTheDocument()
    expect(badge.textContent).toContain('high')
    expect(badge.textContent).toContain('90')
    expect((badge as HTMLElement).style.backgroundColor).toBe('rgb(22, 163, 74)')
  })

  it('renders "moyenne" with orange background and English label', () => {
    render(<ConfidenceBadge confidence={{ score: 0.6, label: 'moyenne', explanation: 'OK' }} />)
    const badge = screen.getByTestId('confidence-badge')
    expect(badge.textContent).toContain('medium')
    expect((badge as HTMLElement).style.backgroundColor).toBe('rgb(217, 119, 6)')
  })

  it('renders "faible" with red background and English label', () => {
    render(<ConfidenceBadge confidence={{ score: 0.3, label: 'faible', explanation: 'Low' }} />)
    const badge = screen.getByTestId('confidence-badge')
    expect(badge.textContent).toContain('low')
    expect((badge as HTMLElement).style.backgroundColor).toBe('rgb(220, 38, 38)')
  })

  it('returns nothing when confidence is null', () => {
    const { container } = render(<ConfidenceBadge confidence={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('displays score percentage', () => {
    render(<ConfidenceBadge confidence={{ score: 0.75, label: 'élevée', explanation: 'Good' }} />)
    const badge = screen.getByTestId('confidence-badge')
    expect(badge.textContent).toContain('75')
  })

  it('uses gray for unknown API labels', () => {
    render(<ConfidenceBadge confidence={{ score: 0.5, label: 'inconnue', explanation: '' }} />)
    const badge = screen.getByTestId('confidence-badge')
    expect((badge as HTMLElement).style.backgroundColor).toBe('rgb(107, 114, 128)')
  })
})
