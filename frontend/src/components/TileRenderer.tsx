import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line,
  PieChart, Pie, Cell,
} from 'recharts'
import { useLocale } from '../hooks/useLocale'

interface TileData {
  columns: string[]
  rows: unknown[][]
}

interface Props {
  type: string
  title: string
  data: TileData
}

const CHART_COLORS = [
  'oklch(42% 0.14 220)',
  'oklch(56% 0.16 175)',
  'oklch(52% 0.16 145)',
  'oklch(68% 0.18 75)',
  'oklch(52% 0.20 25)',
  'oklch(48% 0.15 290)',
]

function toChartData(data: TileData): Record<string, unknown>[] {
  return data.rows.map(row =>
    Object.fromEntries(data.columns.map((col, i) => [col, row[i]]))
  )
}

export function TileRenderer({ type, title, data }: Props) {
  const { t } = useLocale()
  const chartData = toChartData(data)
  const [xKey, yKey] = data.columns.length >= 2
    ? [data.columns[0], data.columns[1]]
    : [data.columns[0] ?? 'x', data.columns[0] ?? 'y']

  switch (type) {
    case 'kpi': {
      const val = data.rows[0]?.[0] ?? '—'
      return (
        <div data-testid="tile-kpi" style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: '12px',
          padding: '20px',
        }}>
          <div style={{
            fontSize: '0.7rem',
            fontWeight: 500,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: 'var(--muted)',
            marginBottom: '8px',
          }}>
            {title}
          </div>
          <div style={{
            fontSize: '2rem',
            fontWeight: 700,
            fontVariantNumeric: 'tabular-nums',
            color: 'var(--brand)',
            lineHeight: 1,
          }}>
            {String(val)}
          </div>
        </div>
      )
    }
    case 'bar':
      return (
        <div data-testid="tile-bar">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData}>
              <XAxis dataKey={xKey} />
              <YAxis />
              <Tooltip />
              <Bar dataKey={yKey} fill={CHART_COLORS[0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )
    case 'line':
      return (
        <div data-testid="tile-line">
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <XAxis dataKey={xKey} />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey={yKey} stroke={CHART_COLORS[0]} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )
    case 'pie':
      return (
        <div data-testid="tile-pie">
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={chartData} dataKey={yKey} nameKey={xKey}>
                {chartData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )
    case 'table':
      return (
        <div data-testid="tile-table" style={{ overflowX: 'auto' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '0.85rem' }}>
            <thead>
              <tr>
                {data.columns.map(c => (
                  <th key={c} style={{ border: '1px solid var(--border)', padding: '6px 10px', background: 'var(--surface-alt)', color: 'var(--text)', fontWeight: 600, textAlign: 'start' }}>
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row, i) => (
                <tr key={i} style={{ background: i % 2 === 1 ? 'var(--surface-alt)' : 'var(--surface)' }}>
                  {(row as unknown[]).map((cell, j) => (
                    <td key={j} style={{ border: '1px solid var(--border)', padding: '6px 10px', color: 'var(--text)', fontVariantNumeric: 'tabular-nums' }}>
                      {String(cell ?? '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    default:
      return <div data-testid="tile-unknown">{t('tile.unknown')} {type}</div>
  }
}
