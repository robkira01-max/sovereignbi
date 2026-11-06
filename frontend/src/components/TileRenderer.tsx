import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend,
  PieChart, Pie, Cell,
} from 'recharts'
import { useLocale } from '../hooks/useLocale'
import { ChoroplethMap } from './ChoroplethMap'

interface TileData {
  columns: string[]
  rows: unknown[][]
}

interface TileOptions {
  unit?: string
  decimals?: number
  x?: string
  y?: string | string[]
  name?: string
  value?: string
  colorScheme?: 'blue' | 'green' | 'red' | 'orange'
}

interface Props {
  type: string
  title: string
  data: TileData
  options?: TileOptions
}

// OKLCH palette — readable on both dark and light backgrounds
const CHART_COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
  '#06b6d4', // cyan
  '#f97316', // orange
  '#84cc16', // lime
]

function toChartData(data: TileData): Record<string, unknown>[] {
  return data.rows.map(row =>
    Object.fromEntries(data.columns.map((col, i) => [col, row[i]]))
  )
}

function labelFormatter(val: unknown, decimals = 1): string {
  if (val === null || val === undefined) return '—'
  const n = Number(val)
  return isNaN(n) ? String(val) : n.toLocaleString('fr-FR', { maximumFractionDigits: decimals })
}

// Compact axis label: trim long strings
function shortLabel(val: unknown): string {
  const s = String(val ?? '')
  return s.length > 14 ? s.slice(0, 13) + '…' : s
}

export function TileRenderer({ type, title, data, options = {} }: Props) {
  const { t } = useLocale()
  const chartData = toChartData(data)

  // Resolve x/y keys from options or fall back to column positions
  const xKey = options.x ?? data.columns[0] ?? 'x'
  const rawY = options.y
  const yKeys: string[] = Array.isArray(rawY)
    ? rawY
    : rawY
      ? [rawY]
      : data.columns.slice(1).length > 0
        ? data.columns.slice(1)
        : [data.columns[0] ?? 'y']

  const unit = options.unit ?? ''
  const decimals = options.decimals ?? 1

  const tooltipFormatter = (value: unknown) =>
    [`${labelFormatter(value, decimals)}${unit ? ' ' + unit : ''}`, '']

  switch (type) {

    // ── KPI card ─────────────────────────────────────────────────────────────
    case 'kpi': {
      const val = data.rows[0]?.[0]
      const formatted = val === null || val === undefined
        ? '—'
        : unit
          ? `${labelFormatter(val, decimals ?? 0)} ${unit}`
          : labelFormatter(val, decimals ?? 0)
      return (
        <div data-testid="tile-kpi" style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 12,
          padding: '20px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          minHeight: 90,
        }}>
          <div style={{
            fontSize: '0.68rem',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.07em',
            color: 'var(--muted)',
          }}>
            {title}
          </div>
          <div style={{
            fontSize: '1.9rem',
            fontWeight: 700,
            fontVariantNumeric: 'tabular-nums',
            color: 'var(--brand)',
            lineHeight: 1.1,
          }}>
            {formatted}
          </div>
        </div>
      )
    }

    // ── Bar chart (single or multi-series) ───────────────────────────────────
    case 'bar':
      return (
        <div data-testid="tile-bar">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 24, left: 4 }}>
              <XAxis
                dataKey={xKey}
                tickFormatter={shortLabel}
                tick={{ fontSize: 10, fill: 'var(--muted)' }}
                angle={-30}
                textAnchor="end"
                interval={0}
              />
              <YAxis tick={{ fontSize: 10, fill: 'var(--muted)' }} width={40} />
              <Tooltip formatter={tooltipFormatter} />
              {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '0.7rem' }} />}
              {yKeys.map((k, i) => (
                <Bar key={k} dataKey={k} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[3, 3, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )

    // ── Line chart (single or multi-series) ──────────────────────────────────
    case 'line':
      return (
        <div data-testid="tile-line">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 4 }}>
              <XAxis dataKey={xKey} tick={{ fontSize: 10, fill: 'var(--muted)' }} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--muted)' }} width={40} />
              <Tooltip formatter={tooltipFormatter} />
              {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '0.7rem' }} />}
              {yKeys.map((k, i) => (
                <Line
                  key={k}
                  type="monotone"
                  dataKey={k}
                  stroke={CHART_COLORS[i % CHART_COLORS.length]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )

    // ── Pie / donut chart ─────────────────────────────────────────────────────
    case 'pie': {
      const nameKey = options.name ?? xKey
      const valueKey = options.value ?? yKeys[0]
      return (
        <div data-testid="tile-pie">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie
                data={chartData}
                dataKey={valueKey}
                nameKey={nameKey}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={90}
                paddingAngle={2}
                label={({ name, percent }: { name: string; percent: number }) =>
                  `${shortLabel(name)} ${(percent * 100).toFixed(0)}%`
                }
                labelLine={false}
              >
                {chartData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v: unknown) => labelFormatter(v, decimals)} />
              <Legend wrapperStyle={{ fontSize: '0.7rem' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )
    }

    // ── Table ─────────────────────────────────────────────────────────────────
    case 'table':
      return (
        <div data-testid="tile-table" style={{ overflowX: 'auto' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.82rem' }}>
            <thead>
              <tr>
                {data.columns.map(c => (
                  <th key={c} style={{
                    border: '1px solid var(--border)',
                    padding: '7px 11px',
                    background: 'var(--surface-alt)',
                    color: 'var(--text)',
                    fontWeight: 600,
                    textAlign: 'start',
                    whiteSpace: 'nowrap',
                  }}>
                    {c.replace(/_/g, ' ')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row, i) => (
                <tr key={i} style={{ background: i % 2 === 1 ? 'var(--surface-alt)' : 'var(--surface)' }}>
                  {(row as unknown[]).map((cell, j) => (
                    <td key={j} style={{
                      border: '1px solid var(--border)',
                      padding: '6px 11px',
                      color: 'var(--text)',
                      fontVariantNumeric: 'tabular-nums',
                    }}>
                      {cell === null || cell === undefined ? '—' : String(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )

    // ── Choropleth map (Djibouti ADM1) ────────────────────────────────────────
    case 'map':
      return (
        <ChoroplethMap
          data={data}
          title={title}
          unit={unit}
          colorScheme={options.colorScheme ?? 'blue'}
        />
      )

    default:
      return <div data-testid="tile-unknown">{t('tile.unknown')} {type}</div>
  }
}
