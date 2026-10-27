import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  LineChart, Line,
  PieChart, Pie, Cell, Legend,
} from 'recharts'

interface Props {
  columns: string[]
  rows: unknown[][]
}

const COLORS = [
  'oklch(42% 0.14 220)',
  'oklch(56% 0.16 175)',
  'oklch(52% 0.16 145)',
  'oklch(68% 0.18 75)',
  'oklch(52% 0.20 25)',
  'oklch(48% 0.15 290)',
]

function isNumeric(v: unknown): boolean {
  return typeof v === 'number' || (typeof v === 'string' && v.trim() !== '' && !isNaN(Number(v)))
}

function isYearLike(col: string): boolean {
  return /^(ann[eé]e|year|date|mois|month|periode|period|trimestre|quarter)/i.test(col)
}

function fmt(v: unknown): string {
  if (typeof v === 'number') {
    return v >= 1000 ? v.toLocaleString('fr-FR', { maximumFractionDigits: 1 }) : String(+v.toFixed(2))
  }
  return String(v ?? '')
}

type ChartType = 'kpi' | 'bar' | 'line' | 'pie' | 'multibar' | 'none'

function detectType(columns: string[], rows: unknown[][]): ChartType {
  if (rows.length === 0 || columns.length === 0) return 'none'

  // Single value → KPI
  if (rows.length === 1 && columns.length === 1) return 'kpi'

  // Single numeric column, multiple rows → bar
  if (columns.length === 1 && rows.every(r => isNumeric(r[0]))) return 'bar'

  const numCols = columns.slice(1).filter((_, i) => rows.every(r => isNumeric(r[i + 1])))

  // 2 columns: label + value
  if (columns.length === 2 && numCols.length === 1) {
    if (rows.length <= 6) return 'pie'
    if (isYearLike(columns[0])) return 'line'
    return 'bar'
  }

  // Time series with multiple numeric columns
  if (isYearLike(columns[0]) && numCols.length >= 1) return 'line'

  // Multiple numeric columns → multibar
  if (numCols.length >= 2 && rows.length <= 30) return 'multibar'

  // Single numeric col, many rows
  if (numCols.length >= 1 && rows.length <= 30) return 'bar'

  return 'none'
}

function toChartData(columns: string[], rows: unknown[][]): Record<string, unknown>[] {
  return rows.map(row =>
    Object.fromEntries(columns.map((col, i) => [col, isNumeric(row[i]) ? Number(row[i]) : row[i]]))
  )
}

const tooltipStyle = {
  background: 'var(--surface)',
  border: '1px solid var(--border)',
  borderRadius: '8px',
  fontSize: '0.8rem',
  fontFamily: 'Figtree, system-ui, sans-serif',
}

export function ChartBlock({ columns, rows }: Props) {
  if (rows.length === 0) return null

  const type = detectType(columns, rows)
  if (type === 'none') return null

  const data = toChartData(columns, rows)
  const xKey = columns[0]
  const numericCols = columns.slice(1).filter((_, i) => rows.every(r => isNumeric(r[i + 1])))
  const yKey = numericCols[0] ?? columns[1] ?? columns[0]

  if (type === 'kpi') {
    const val = rows[0][0]
    return (
      <div style={{
        display: 'inline-block',
        background: 'oklch(96% 0.018 220)',
        border: '1px solid oklch(88% 0.03 220)',
        borderRadius: '12px',
        padding: '16px 24px',
        marginTop: '10px',
      }}>
        <div style={{ fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted)', marginBottom: '4px' }}>
          {columns[0]}
        </div>
        <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--brand)', fontVariantNumeric: 'tabular-nums' }}>
          {fmt(val)}
        </div>
      </div>
    )
  }

  if (type === 'pie') {
    return (
      <div style={{ marginTop: '10px' }}>
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie data={data} dataKey={yKey} nameKey={xKey} cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
              {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} formatter={(v: unknown) => fmt(v)} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    )
  }

  if (type === 'line') {
    return (
      <div style={{ marginTop: '10px' }}>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={fmt} width={60} />
            <Tooltip contentStyle={tooltipStyle} formatter={(v: unknown) => fmt(v)} />
            {(type === 'line' ? numericCols.slice(0, 4) : [yKey]).map((col, i) => (
              <Line key={col} type="monotone" dataKey={col} stroke={COLORS[i % COLORS.length]} strokeWidth={2} dot={rows.length <= 15} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    )
  }

  // bar / multibar
  const barCols = type === 'multibar' ? numericCols.slice(0, 4) : [yKey]
  return (
    <div style={{ marginTop: '10px' }}>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} tickFormatter={fmt} width={60} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v: unknown) => fmt(v)} />
          {barCols.length > 1 && <Legend />}
          {barCols.map((col, i) => (
            <Bar key={col} dataKey={col} fill={COLORS[i % COLORS.length]} radius={[4, 4, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
