import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConfidenceBadge } from '../components/ConfidenceBadge'

// Rendered outside LocaleProvider → DEFAULT_LOCALE='fr', labels are in French.
// Colors are keyed by the API's French labels ('élevée', 'moyenne', 'faible').

describe('ConfidenceBadge', () => {
  it('renders "élevée" with green background and French label', () => {
    render(<ConfidenceBadge confidence={{ score: 0.9, label: 'élevée', explanation: 'Top' }} />)
    const badge = screen.getByTestId('confidence-badge')
    expect(badge).toBeInTheDocument()
    expect(badge.textContent).toContain('élevée')
    expect(badge.textContent).toContain('90')
    expect((badge as HTMLElement).style.backgroundColor).toContain('oklch')
  })

  it('renders "moyenne" with orange background and French label', () => {
    render(<ConfidenceBadge confidence={{ score: 0.6, label: 'moyenne', explanation: 'OK' }} />)
    const badge = screen.getByTestId('confidence-badge')
    expect(badge.textContent).toContain('moyenne')
    expect((badge as HTMLElement).style.backgroundColor).toContain('oklch')
  })

  it('renders "faible" with red background and French label', () => {
    render(<ConfidenceBadge confidence={{ score: 0.3, label: 'faible', explanation: 'Low' }} />)
    const badge = screen.getByTestId('confidence-badge')
    expect(badge.textContent).toContain('faible')
    expect((badge as HTMLElement).style.backgroundColor).toContain('oklch')
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

  it('uses a background color for unknown API labels', () => {
    render(<ConfidenceBadge confidence={{ score: 0.5, label: 'inconnue', explanation: '' }} />)
    const badge = screen.getByTestId('confidence-badge')
    expect((badge as HTMLElement).style.backgroundColor).toBeTruthy()
  })
})
