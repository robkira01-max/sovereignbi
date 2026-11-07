/**
 * P-017 — Tile annotation display test.
 * Verifies that a tile with a pre-existing note renders its text,
 * and that the edit button is present for each tile.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DashboardPage } from '../pages/DashboardPage'

// ── Mocks (vi.mock is hoisted — no external variables allowed inside factory) ─

vi.mock('../hooks/useLocale', () => ({
  useLocale: () => ({ t: (k: string) => k, locale: 'fr' }),
}))

vi.mock('../api/client', () => ({
  api: {
    dashboards: vi.fn().mockResolvedValue([
      { id: 'dash-annot', title: 'Emploi DJ', scope: 'personal', updated_at: '', is_favorite: false },
    ]),
    getDashboard: vi.fn().mockResolvedValue({
      id: 'dash-annot',
      title: 'Emploi DJ',
      scope: 'personal',
      tiles: [
        { id: 'kpi1', type: 'kpi', title: 'Total emplois', note: 'Source : INSTAD, Recensement 2023.', position: 0 },
        { id: 'kpi2', type: 'kpi', title: 'Taux chômage', position: 1 },
      ],
      theme: { primary_color: '#1a4a8c', font: 'sans-serif', logo_url: '' },
      created_at: '',
      updated_at: '',
    }),
    toggleFavorite: vi.fn(),
    patchLayout: vi.fn(),
    addTile: vi.fn(),
    removeTile: vi.fn(),
    setTileNote: vi.fn(),
  },
  apiFetch: vi.fn().mockResolvedValue({ columns: [], rows: [], insight: '', cached: false, age_seconds: null, stale: false }),
  getApiBase: vi.fn().mockReturnValue('http://localhost:8000/api/v1'),
  getKey: vi.fn().mockReturnValue('test-editor-key-s6'),
}))

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('Tile annotation (P-017)', () => {
  it('renders a note-edit button for each tile after opening a dashboard', async () => {
    render(<DashboardPage />)
    // Dashboard list appears first — click dashboard
    const listBtn = await screen.findByText('Emploi DJ')
    listBtn.click()

    const editBtn1 = await screen.findByTestId('note-edit-btn-kpi1')
    const editBtn2 = await screen.findByTestId('note-edit-btn-kpi2')
    expect(editBtn1).toBeTruthy()
    expect(editBtn2).toBeTruthy()
  })

  it('renders existing note text below tile content', async () => {
    render(<DashboardPage />)
    const listBtn = await screen.findByText('Emploi DJ')
    listBtn.click()

    const noteEl = await screen.findByTestId('tile-note-kpi1')
    expect(noteEl.textContent).toContain('INSTAD')
  })
})
