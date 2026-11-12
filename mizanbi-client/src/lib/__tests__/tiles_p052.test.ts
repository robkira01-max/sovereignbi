/**
 * Tests for P-052: advanced tile component helpers (DOM-free pure logic).
 */
import { describe, it, expect } from 'vitest'

// ── HeatmapTile: intensityColor helper ────────────────────────────────────────

const PALETTE_BLUE = ['#1e293b', '#c7d2fe', '#818cf8', '#4f46e5', '#312e81']

function intensityColor(norm: number, palette: string[]): string {
  if (norm <= 0) return palette[0]
  if (norm < 0.25) return palette[1]
  if (norm < 0.5)  return palette[2]
  if (norm < 0.75) return palette[3]
  return palette[4]
}

describe('HeatmapTile intensityColor', () => {
  it('returns palette[0] for norm <= 0', () => {
    expect(intensityColor(0, PALETTE_BLUE)).toBe('#1e293b')
    expect(intensityColor(-1, PALETTE_BLUE)).toBe('#1e293b')
  })
  it('returns palette[1] for 0 < norm < 0.25', () => {
    expect(intensityColor(0.1, PALETTE_BLUE)).toBe('#c7d2fe')
  })
  it('returns palette[2] for 0.25 <= norm < 0.5', () => {
    expect(intensityColor(0.3, PALETTE_BLUE)).toBe('#818cf8')
  })
  it('returns palette[3] for 0.5 <= norm < 0.75', () => {
    expect(intensityColor(0.6, PALETTE_BLUE)).toBe('#4f46e5')
  })
  it('returns palette[4] for norm >= 0.75', () => {
    expect(intensityColor(0.9, PALETTE_BLUE)).toBe('#312e81')
    expect(intensityColor(1.0, PALETTE_BLUE)).toBe('#312e81')
  })
})

// ── SparklineKpi: buildPath helper ────────────────────────────────────────────

function buildPath(pts: number[], W: number, H: number): string {
  if (pts.length < 2) return ''
  const min = Math.min(...pts)
  const max = Math.max(...pts)
  const range = max === min ? 1 : max - min
  const step = W / (pts.length - 1)
  const coords = pts.map((v, i) => {
    const x = i * step
    const y = H - ((v - min) / range) * (H - 4) - 2
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return 'M ' + coords.join(' L ')
}

describe('SparklineKpi buildPath', () => {
  it('returns empty string for < 2 points', () => {
    expect(buildPath([], 80, 32)).toBe('')
    expect(buildPath([10], 80, 32)).toBe('')
  })

  it('starts with M for 2+ points', () => {
    const path = buildPath([10, 20], 80, 32)
    expect(path).toMatch(/^M /)
  })

  it('contains L connectors for 3+ points', () => {
    const path = buildPath([10, 20, 15], 80, 32)
    expect(path).toContain(' L ')
  })

  it('first x coordinate is 0.0 for first point', () => {
    const path = buildPath([10, 20], 80, 32)
    expect(path).toMatch(/^M 0\.0,/)
  })

  it('last x coordinate equals W for last point (2 pts)', () => {
    const path = buildPath([10, 20], 80, 32)
    expect(path).toContain('80.0,')
  })

  it('handles equal min/max values without NaN', () => {
    const path = buildPath([5, 5, 5], 80, 32)
    expect(path).not.toContain('NaN')
    expect(path).toMatch(/^M /)
  })
})

// ── TableTile: compareValues helper ───────────────────────────────────────────

type SortDir = 'asc' | 'desc'

function compareValues(a: unknown, b: unknown, dir: SortDir): number {
  const na = Number(a); const nb = Number(b)
  const numA = isNaN(na) ? null : na
  const numB = isNaN(nb) ? null : nb
  let cmp: number
  if (numA !== null && numB !== null) {
    cmp = numA - numB
  } else {
    cmp = String(a ?? '').localeCompare(String(b ?? ''), undefined, { numeric: true, sensitivity: 'base' })
  }
  return dir === 'asc' ? cmp : -cmp
}

describe('TableTile compareValues', () => {
  it('sorts numbers ascending', () => {
    expect(compareValues(3, 10, 'asc')).toBeLessThan(0)
    expect(compareValues(10, 3, 'asc')).toBeGreaterThan(0)
    expect(compareValues(5, 5, 'asc')).toBe(0)
  })
  it('reverses for desc', () => {
    expect(compareValues(3, 10, 'desc')).toBeGreaterThan(0)
  })
  it('sorts strings lexicographically', () => {
    expect(compareValues('Ali Sabieh', 'Obock', 'asc')).toBeLessThan(0)
  })
  it('handles null/undefined as empty string', () => {
    expect(() => compareValues(null, 'x', 'asc')).not.toThrow()
  })
})

// ── BivariateChoropleth: tercileClass helper ──────────────────────────────────

function tercileClass(values: number[]): number[] {
  const sorted = [...values].sort((a, b) => a - b)
  const n = sorted.length
  const t1 = sorted[Math.floor(n / 3)]
  const t2 = sorted[Math.floor((2 * n) / 3)]
  return values.map(v => (v <= t1 ? 0 : v <= t2 ? 1 : 2))
}

describe('BivariateChoropleth tercileClass', () => {
  it('assigns class 0,0,1 to 3 sorted values (boundary values fall in lower class)', () => {
    // t1=sorted[1]=20, t2=sorted[2]=30 → 10≤20→0, 20≤20→0, 30≤30→1
    expect(tercileClass([10, 20, 30])).toEqual([0, 0, 1])
  })
  it('assigns class 0 to all equal values', () => {
    expect(tercileClass([5, 5, 5])).toEqual([0, 0, 0])
  })
  it('output length equals input length', () => {
    const vals = [1, 2, 3, 4, 5, 6]
    expect(tercileClass(vals)).toHaveLength(6)
  })
  it('all values are 0, 1, or 2', () => {
    const vals = [15, 3, 8, 22, 1, 10]
    const classes = tercileClass(vals)
    expect(classes.every(c => c >= 0 && c <= 2)).toBe(true)
  })
  it('lowest third gets class 0, highest third gets class 2', () => {
    const vals = [1, 2, 3, 7, 8, 9]
    const classes = tercileClass(vals)
    expect(classes[0]).toBe(0)
    expect(classes[5]).toBe(2)
  })
})

// ── LiveTileData: type contract ───────────────────────────────────────────────

import type { LiveTileData } from '../../components/LiveTileRenderer'

describe('LiveTileData type', () => {
  it('accepts valid tile data', () => {
    const d: LiveTileData = {
      columns: ['date', 'valeur'],
      rows: [['2024-01', 42], ['2024-02', 55]],
    }
    expect(d.columns).toHaveLength(2)
    expect(d.rows).toHaveLength(2)
  })

  it('handles empty rows', () => {
    const d: LiveTileData = { columns: ['x', 'y'], rows: [] }
    expect(d.rows).toHaveLength(0)
  })
})
