import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SqlBlock } from '../components/SqlBlock'

describe('SqlBlock', () => {
  it('renders SQL inside a pre element', () => {
    render(<SqlBlock sql="SELECT * FROM ventes" />)
    const pre = screen.getByTestId('sql-block')
    expect(pre.tagName).toBe('PRE')
    expect(pre.textContent).toContain('SELECT * FROM ventes')
  })

  it('shows a copy button', () => {
    render(<SqlBlock sql="SELECT 1" />)
    expect(screen.getByTestId('copy-button')).toBeInTheDocument()
  })

  it('renders empty SQL without error', () => {
    render(<SqlBlock sql="" />)
    expect(screen.getByTestId('sql-block')).toBeInTheDocument()
  })
})
