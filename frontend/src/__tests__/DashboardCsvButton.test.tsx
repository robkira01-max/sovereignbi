import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DashboardPage } from '../pages/DashboardPage'

// Mock API so the component doesn't make real network calls
vi.mock('../api/client', () => ({
  api: {
    dashboards: vi.fn().mockResolvedValue([
      { id: 'dash1', title: 'Test Dashboard', scope: 'personal' },
    ]),
    getDashboard: vi.fn().mockResolvedValue({
      id: 'dash1', title: 'Test Dashboard', scope: 'personal',
      tiles: [{ id: 'kpi1', type: 'kpi', title: 'Chômage', position: 0 }],
      theme: { primary_color: '#1a4a8c', font: 'sans-serif', logo_url: '' },
    }),
    patchLayout: vi.fn().mockResolvedValue(undefined),
    addTile: vi.fn().mockResolvedValue(undefined),
    removeTile: vi.fn().mockResolvedValue(undefined),
  },
  apiFetch: vi.fn().mockResolvedValue({ columns: ['valeur'], rows: [[25]] }),
  getApiBase: vi.fn().mockReturnValue('http://localhost:8000/api/v1'),
  getKey: vi.fn().mockReturnValue('test-key'),
}))

describe('DashboardPage — CSV export button', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders CSV export button after selecting a dashboard', async () => {
    render(<DashboardPage />)
    // Click the first dashboard in the list
    const dashBtn = await screen.findByText('Test Dashboard')
    dashBtn.click()
    // CSV button should appear for the tile
    const csvBtn = await screen.findByTestId('export-csv-kpi1')
    expect(csvBtn).toBeTruthy()
    expect(csvBtn.textContent).toContain('CSV')
  })
})
