/**
 * Tests for P-051: DashboardsPage and LiveTileRenderer
 * DOM-free: test types, helper logic, i18n key coverage.
 * Full render tests require jsdom (not configured in this vitest setup).
 */
import { describe, it, expect } from 'vitest'
import { I18N } from '../i18n'

const fr = I18N.fr
const en = I18N.en

// ── i18n key coverage ─────────────────────────────────────────────────────────

const REQUIRED_DASHBOARD_KEYS = [
  'title', 'tagsFilterPlaceholder', 'noDashboards',
  'unfavorite', 'favorite', 'saving', 'exportBulletin',
  'clone', 'exportPptx', 'addTile', 'tagsPlaceholder',
  'save', 'cancel', 'tagsLabel', 'idLabel', 'tileIdPlaceholder',
  'titleLabel', 'tileTitlePlaceholder', 'typeLabel',
  'dragHint', 'freshnessUnknown', 'freshnessStale',
  'exportCsv', 'deleteTile', 'tileNotePlaceholder',
  'tileNote', 'tileNoteEdit', 'sourceLabel', 'noTiles',
  'regionFilter', 'regionFilterClear',
] as const

describe('i18n dashboard keys', () => {
  for (const key of REQUIRED_DASHBOARD_KEYS) {
    it(`fr.dashboard.${key} is a non-empty string`, () => {
      const val = (fr.dashboard as Record<string, string>)[key]
      expect(typeof val).toBe('string')
      expect(val.length).toBeGreaterThan(0)
    })

    it(`en.dashboard.${key} is a non-empty string`, () => {
      const val = (en.dashboard as Record<string, string>)[key]
      expect(typeof val).toBe('string')
      expect(val.length).toBeGreaterThan(0)
    })

  }

  it('regionFilter contains {region} placeholder', () => {
    expect(fr.dashboard.regionFilter).toContain('{region}')
    expect(en.dashboard.regionFilter).toContain('{region}')
  })

  it('regionFilter interpolation works with replace', () => {
    const result = fr.dashboard.regionFilter.replace('{region}', 'Ali Sabieh')
    expect(result).toContain('Ali Sabieh')
    expect(result).not.toContain('{region}')
  })
})

// ── Freshness logic ───────────────────────────────────────────────────────────

type FreshnessState = { age_seconds: number | null; stale: boolean }

function freshnessColor(f: FreshnessState | undefined): string {
  if (!f) return 'var(--muted)'
  if (f.stale) return 'var(--danger)'
  if ((f.age_seconds ?? 9999) < 300) return 'oklch(68% 0.18 155)'
  return 'oklch(72% 0.19 55)'
}

describe('freshnessColor', () => {
  it('returns muted when no freshness data', () => {
    expect(freshnessColor(undefined)).toBe('var(--muted)')
  })
  it('returns danger when stale', () => {
    expect(freshnessColor({ age_seconds: 1000, stale: true })).toBe('var(--danger)')
  })
  it('returns green for age < 300s', () => {
    expect(freshnessColor({ age_seconds: 60, stale: false })).toBe('oklch(68% 0.18 155)')
  })
  it('returns amber for age >= 300s', () => {
    expect(freshnessColor({ age_seconds: 600, stale: false })).toBe('oklch(72% 0.19 55)')
  })
  it('treats null age_seconds as old', () => {
    expect(freshnessColor({ age_seconds: null, stale: false })).toBe('oklch(72% 0.19 55)')
  })
})

// ── API types ─────────────────────────────────────────────────────────────────

import type { DashboardSummary, Dashboard, Tile, TileData } from '../api'

describe('API types', () => {
  it('DashboardSummary has expected shape', () => {
    const d: DashboardSummary = {
      id: 'dash-1', title: 'Test', scope: 'global', updated_at: '2026-01-01T00:00:00Z',
      is_favorite: false, tags: ['emploi'],
    }
    expect(d.id).toBe('dash-1')
    expect(d.tags).toHaveLength(1)
  })

  it('Dashboard has tiles array', () => {
    const d: Dashboard = { id: 'x', title: 'X', scope: 'dj', tiles: [] }
    expect(Array.isArray(d.tiles)).toBe(true)
  })

  it('Tile has optional note and source', () => {
    const tile: Tile = { id: 't1', type: 'kpi', title: 'Chômage' }
    expect(tile.note).toBeUndefined()
    expect(tile.source).toBeUndefined()
  })

  it('TileData has columns and rows', () => {
    const td: TileData = { columns: ['region', 'value'], rows: [['Ali Sabieh', 25.3]] }
    expect(td.columns).toHaveLength(2)
    expect(td.rows[0][1]).toBe(25.3)
  })
})

// ── Tile sort by position ─────────────────────────────────────────────────────

function byPosition(a: Tile, b: Tile) { return (a.position ?? 999) - (b.position ?? 999) }

describe('byPosition sort', () => {
  it('sorts tiles in position order', () => {
    const tiles: Tile[] = [
      { id: 'c', type: 'kpi', title: 'C', position: 2 },
      { id: 'a', type: 'kpi', title: 'A', position: 0 },
      { id: 'b', type: 'kpi', title: 'B', position: 1 },
    ]
    const sorted = [...tiles].sort(byPosition)
    expect(sorted.map(t => t.id)).toEqual(['a', 'b', 'c'])
  })

  it('puts tiles without position last (999)', () => {
    const tiles: Tile[] = [
      { id: 'x', type: 'kpi', title: 'X' },
      { id: 'a', type: 'kpi', title: 'A', position: 0 },
    ]
    const sorted = [...tiles].sort(byPosition)
    expect(sorted[0].id).toBe('a')
    expect(sorted[1].id).toBe('x')
  })
})

// ── Tag filtering ─────────────────────────────────────────────────────────────

describe('tag filter logic', () => {
  const summaries: DashboardSummary[] = [
    { id: '1', title: 'A', scope: 'dj', updated_at: '', tags: ['emploi', 'instad'] },
    { id: '2', title: 'B', scope: 'dj', updated_at: '', tags: ['canada'] },
    { id: '3', title: 'C', scope: 'dj', updated_at: '', tags: [] },
  ]

  function filter(tag: string) {
    return tag ? summaries.filter(d => (d.tags ?? []).includes(tag.trim())) : summaries
  }

  it('empty tag returns all', () => {
    expect(filter('')).toHaveLength(3)
  })
  it('filters by exact tag', () => {
    expect(filter('emploi')).toHaveLength(1)
    expect(filter('emploi')[0].id).toBe('1')
  })
  it('trims whitespace from tag filter', () => {
    expect(filter('  canada  ')).toHaveLength(1)
  })
  it('returns empty for unknown tag', () => {
    expect(filter('xyz')).toHaveLength(0)
  })
})

// ── LiveTileRenderer toChartData ──────────────────────────────────────────────

function toChartData(data: TileData): Record<string, unknown>[] {
  return data.rows.map(row =>
    Object.fromEntries(data.columns.map((col, i) => [col, row[i]]))
  )
}

describe('toChartData', () => {
  it('converts rows to column-keyed objects', () => {
    const data: TileData = {
      columns: ['region', 'value'],
      rows: [['Ali Sabieh', 25.3], ['Djibouti', 23.5]],
    }
    const chart = toChartData(data)
    expect(chart).toHaveLength(2)
    expect(chart[0]).toEqual({ region: 'Ali Sabieh', value: 25.3 })
    expect(chart[1]).toEqual({ region: 'Djibouti', value: 23.5 })
  })

  it('handles empty rows', () => {
    expect(toChartData({ columns: ['x'], rows: [] })).toEqual([])
  })
})

// ── drag-and-drop reorder logic ───────────────────────────────────────────────

function reorder(tiles: Tile[], from: number, to: number): Tile[] {
  const next = [...tiles]
  const [moved] = next.splice(from, 1)
  next.splice(to, 0, moved)
  return next.map((tile, idx) => ({ ...tile, position: idx }))
}

describe('drag reorder', () => {
  const tiles: Tile[] = [
    { id: 'a', type: 'kpi', title: 'A', position: 0 },
    { id: 'b', type: 'kpi', title: 'B', position: 1 },
    { id: 'c', type: 'kpi', title: 'C', position: 2 },
  ]

  it('moves tile from index 0 to index 2', () => {
    const result = reorder(tiles, 0, 2)
    expect(result.map(t => t.id)).toEqual(['b', 'c', 'a'])
    expect(result.map(t => t.position)).toEqual([0, 1, 2])
  })

  it('no-op when from === to', () => {
    // No-op guard is in the component, here we test the pure reorder function
    const result = reorder(tiles, 1, 1)
    expect(result.map(t => t.id)).toEqual(['a', 'b', 'c'])
  })

  it('positions are always re-indexed from 0', () => {
    const result = reorder(tiles, 2, 0)
    expect(result.map(t => t.position)).toEqual([0, 1, 2])
  })
})
