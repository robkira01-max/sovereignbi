/**
 * TableTile — sortable, filterable data table for dashboard tiles.
 * Sort: click any column header to cycle asc → desc → none.
 * Filter: text input performs case-insensitive substring match across all cells.
 */
import { useState, useMemo } from 'react'
import type { LiveTileData } from './LiveTileRenderer'

type SortDir = 'asc' | 'desc' | null

function compareValues(a: unknown, b: unknown, dir: 'asc' | 'desc'): number {
  const na = Number(a)
  const nb = Number(b)
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

export function TableTile({ data }: { data: LiveTileData }) {
  const [sortCol, setSortCol] = useState<number | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>(null)
  const [filter, setFilter] = useState('')

  const handleHeaderClick = (colIdx: number) => {
    if (sortCol !== colIdx) {
      setSortCol(colIdx)
      setSortDir('asc')
    } else if (sortDir === 'asc') {
      setSortDir('desc')
    } else if (sortDir === 'desc') {
      setSortCol(null)
      setSortDir(null)
    }
  }

  const sortIcon = (colIdx: number) => {
    if (sortCol !== colIdx) return ' ↕'
    return sortDir === 'asc' ? ' ↑' : ' ↓'
  }

  const rows = useMemo(() => {
    let result = [...data.rows]
    if (filter.trim()) {
      const q = filter.trim().toLowerCase()
      result = result.filter(row =>
        (row as unknown[]).some(cell => String(cell ?? '').toLowerCase().includes(q))
      )
    }
    if (sortCol !== null && sortDir !== null) {
      result.sort((a, b) =>
        compareValues((a as unknown[])[sortCol], (b as unknown[])[sortCol], sortDir)
      )
    }
    return result
  }, [data.rows, filter, sortCol, sortDir])

  return (
    <div data-testid="tile-table-advanced" style={{ overflowX: 'auto' }}>
      <input
        data-testid="table-filter-input"
        type="text"
        value={filter}
        onChange={e => setFilter(e.target.value)}
        placeholder="Filtrer…"
        style={{
          width: '100%',
          marginBottom: '6px',
          padding: '4px 8px',
          fontSize: '0.78rem',
          border: '1px solid var(--border)',
          borderRadius: '4px',
          boxSizing: 'border-box',
          background: 'var(--surface)',
          color: 'var(--text)',
        }}
      />
      <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.82rem' }}>
        <thead>
          <tr>
            {data.columns.map((c, colIdx) => (
              <th
                key={c}
                data-testid={`table-col-header-${c}`}
                onClick={() => handleHeaderClick(colIdx)}
                style={{
                  border: '1px solid var(--border)',
                  padding: '7px 11px',
                  background: 'var(--surface-solid)',
                  color: 'var(--text)',
                  fontWeight: 600,
                  textAlign: 'start',
                  whiteSpace: 'nowrap',
                  cursor: 'pointer',
                  userSelect: 'none',
                }}
              >
                {c.replace(/_/g, ' ')}{sortIcon(colIdx)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ background: i % 2 === 1 ? 'var(--surface-solid)' : 'var(--surface)' }}>
              {(row as unknown[]).map((cell, j) => (
                <td
                  key={j}
                  style={{
                    border: '1px solid var(--border)',
                    padding: '6px 11px',
                    color: 'var(--text)',
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {cell === null || cell === undefined ? '—' : String(cell)}
                </td>
              ))}
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td
                colSpan={data.columns.length || 1}
                style={{ padding: '12px', textAlign: 'center', color: 'var(--muted)', fontSize: '0.78rem' }}
              >
                —
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
