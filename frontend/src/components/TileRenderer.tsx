import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line,
  PieChart, Pie, Cell,
} from 'recharts'

interface TileData {
  columns: string[]
  rows: unknown[][]
}

interface Props {
  type: string
  title: string
  data: TileData
}

const COLORS = ['#2563eb', '#16a34a', '#d97706', '#dc2626', '#7c3aed', '#0891b2']

function toChartData(data: TileData): Record<string, unknown>[] {
  return data.rows.map(row =>
    Object.fromEntries(data.columns.map((col, i) => [col, row[i]]))
  )
}

export function TileRenderer({ type, title, data }: Props) {
  const chartData = toChartData(data)
  const [xKey, yKey] = data.columns.length >= 2
    ? [data.columns[0], data.columns[1]]
    : [data.columns[0] ?? 'x', data.columns[0] ?? 'y']

  switch (type) {
    case 'kpi': {
      const val = data.rows[0]?.[0] ?? '—'
      return (
        <div data-testid="tile-kpi" style={{ textAlign: 'center', padding: '16px' }}>
          <div style={{ fontSize: '2rem', fontWeight: 700 }}>{String(val)}</div>
          <div style={{ fontSize: '0.85rem', color: '#6b7280' }}>{title}</div>
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
              <Bar dataKey={yKey} fill={COLORS[0]} />
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
              <Line type="monotone" dataKey={yKey} stroke={COLORS[0]} />
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
                {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
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
                  <th key={c} style={{ border: '1px solid #e5e7eb', padding: '4px 8px', background: '#f9fafb' }}>
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row, i) => (
                <tr key={i}>
                  {(row as unknown[]).map((cell, j) => (
                    <td key={j} style={{ border: '1px solid #e5e7eb', padding: '4px 8px' }}>
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
      return <div data-testid="tile-unknown">Type de tuile inconnu : {type}</div>
  }
}
