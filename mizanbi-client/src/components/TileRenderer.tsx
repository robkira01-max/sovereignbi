import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { DashboardTile } from '../data/demo'
import { fmt } from '../data/demo'
import { colorForValue, currentTheme, scaleFor, textOnFill } from '../lib/theme'

const COLORS = ['#7c6cf0', '#34d399', '#f59e0b', '#f87171', '#38bdf8', '#c084fc']

type ChartRow = Record<string, string | number> & { fill?: string }

function rowsToObjects(tile: DashboardTile): ChartRow[] {
  const [c0, c1] = tile.data.columns
  return tile.data.rows.map((r) => ({ [c0]: r[0], [c1]: Number(r[1]) }))
}

export default function TileRenderer({ tile }: { tile: DashboardTile }) {
  const th = currentTheme()
  const tickMuted = th.vars['--muted-2']
  const tickText = th.vars['--text']
  if (tile.type === 'kpi') {
    const v = tile.data.rows[0]?.[tile.data.rows[0].length - 1]
    return (
      <div style={{ textAlign: 'center', padding: '12px 0' }}>
        <div className="kpi-value">{fmt(v as number)}</div>
        <div style={{ color: 'oklch(68% 0.03 265)' }}>{tile.unit}</div>
        {tile.delta !== undefined && (
          <div style={{ marginTop: 6, fontWeight: 600, color: tile.delta < 0 ? 'oklch(72% 0.17 155)' : 'oklch(72% 0.19 55)' }}>
            {tile.delta < 0 ? '▼' : '▲'} {Math.abs(tile.delta)} %
          </div>
        )}
      </div>
    )
  }
  if (tile.type === 'bar') {
    const data = rowsToObjects(tile)
    return (
      <div dir="ltr" style={{ height: 190 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid stroke="oklch(25% 0.04 265)" strokeDasharray="3 3" />
            <XAxis dataKey={tile.data.columns[0]} tick={{ fill: tickMuted, fontSize: 11 }} />
            <YAxis tick={{ fill: tickMuted, fontSize: 11 }} />
            <Tooltip contentStyle={{ background: th.vars['--surface-solid'], border: '1px solid var(--border)', borderRadius: 10, color: th.vars['--text'] }} />
            <Bar dataKey={tile.data.columns[1]} fill="#7c6cf0" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }
  if (tile.type === 'line') {
    const data = rowsToObjects(tile)
    return (
      <div dir="ltr" style={{ height: 190 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid stroke="oklch(25% 0.04 265)" strokeDasharray="3 3" />
            <XAxis dataKey={tile.data.columns[0]} tick={{ fill: tickMuted, fontSize: 11 }} />
            <YAxis tick={{ fill: tickMuted, fontSize: 11 }} />
            <Tooltip contentStyle={{ background: th.vars['--surface-solid'], border: '1px solid var(--border)', borderRadius: 10, color: th.vars['--text'] }} />
            <Line type="monotone" dataKey={tile.data.columns[1]} stroke="#34d399" strokeWidth={2.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    )
  }
  if (tile.type === 'pie') {
    const data: ChartRow[] = rowsToObjects(tile).map((d, i) => ({ ...d, fill: COLORS[i % COLORS.length] }))
    return (
      <div dir="ltr" style={{ height: 190, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 20, flexWrap: 'wrap' }}>
        <ResponsiveContainer width={170} height={170}>
          <PieChart>
            <Pie data={data} dataKey={tile.data.columns[1]} nameKey={tile.data.columns[0]} innerRadius={42} outerRadius={75} paddingAngle={2}>
              {data.map((d, i) => (
                <Cell key={i} fill={d.fill} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ background: th.vars['--surface-solid'], border: '1px solid var(--border)', borderRadius: 10, color: th.vars['--text'] }} />
          </PieChart>
        </ResponsiveContainer>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 5, fontSize: 12 }}>
          {data.map((d) => (
            <span key={String(d[tile.data.columns[0]])} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ width: 10, height: 10, borderRadius: 3, background: d.fill }} />
              {String(d[tile.data.columns[0]])} <b>{Number(d[tile.data.columns[1]])} %</b>
            </span>
          ))}
        </div>
      </div>
    )
  }
  if (tile.type === 'choropleth') {
    const data = rowsToObjects(tile)
    const vals = data.map((d) => Number(d[tile.data.columns[1]]))
    // P-028 : couleurs calculées sur les valeurs affichées, thème Djibouti.
    const scale = scaleFor(vals, currentTheme(), '%')
    return (
      <div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 6 }}>
          {data.map((d) => {
            const v = Number(d[tile.data.columns[1]])
            return (
              <div key={String(d[tile.data.columns[0]])} style={{ borderRadius: 10, padding: '12px 8px', textAlign: 'center', background: colorForValue(v, scale), color: textOnFill(v, scale) }}>
                <div style={{ fontSize: 11, opacity: 0.9 }}>{String(d[tile.data.columns[0]])}</div>
                <div style={{ fontWeight: 700, fontSize: 16 }}>{fmt(v)} %</div>
              </div>
            )
          })}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--muted)', marginTop: 8 }}>
          <span>{fmt(scale.min)} %</span>
          <span className="legend-bar" />
          <span>{fmt(scale.max)} %</span>
          <span style={{ marginInlineStart: 8 }}>Médiane : {fmt(scale.median)} %</span>
        </div>
      </div>
    )
  }
  if (tile.type === 'grid') {
    const grouped = new Map<string, number[]>()
    tile.data.rows.forEach((r) => {
      const k = String(r[0])
      if (!grouped.has(k)) grouped.set(k, [])
      grouped.get(k)!.push(Number(r[2]))
    })
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: 10 }}>
        {[...grouped.entries()].map(([label, values]) => {
          const mn = Math.min(...values)
          const rg = Math.max(...values) - mn || 1
          const pts = values.map((v, i) => `${values.length > 1 ? (i / (values.length - 1)) * 100 : 50},${36 - ((v - mn) / rg) * 32}`).join(' ')
          return (
            <div key={label} style={{ background: 'var(--surface)', borderRadius: 10, padding: 8 }}>
              <div style={{ fontSize: 11, color: 'var(--muted)' }}>{label}</div>
              <svg viewBox="0 0 100 40" style={{ width: '100%', height: 44 }} preserveAspectRatio="none">
                <polyline points={pts} fill="none" stroke="oklch(65% 0.22 265)" strokeWidth="2" vectorEffect="non-scaling-stroke" />
              </svg>
            </div>
          )
        })}
      </div>
    )
  }
  // table
  return (
    <div className="table-wrap" style={{ maxHeight: 260 }}>
      <table className="data">
        <thead>
          <tr>{tile.data.columns.map((c) => <th key={c}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {tile.data.rows.slice(0, 100).map((r, i) => (
            <tr key={i}>{r.map((c, j) => <td key={j}>{fmt(c as number | string)}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
