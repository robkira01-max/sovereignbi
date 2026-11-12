/**
 * Live-data tile renderer for the full DashboardPage (P-051 / P-052).
 * Takes structured data from the backend (/tiles/{id}/data) and renders it.
 */
import {
  Bar, BarChart, CartesianGrid, Cell, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend,
} from 'recharts'
import { HeatmapTile } from './HeatmapTile'
import { TableTile } from './TableTile'
import { SparklineKpi } from './SparklineKpi'
import { MapLibreMap } from './MapLibreMap'
import { MapAdm2 } from './MapAdm2'
import { BivariateChoropleth } from './BivariateChoropleth'
import { TradeFlowMap } from './TradeFlowMap'

export interface LiveTileData {
  columns: string[]
  rows: unknown[][]
}

export interface LiveTileOptions {
  unit?: string
  decimals?: number
  x?: string
  y?: string | string[]
  name?: string
  value?: string
  colorScheme?: string
  showValues?: boolean
  chart_type?: 'bar' | 'line'
  facet_by?: string
}

interface Props {
  type: string
  title: string
  data: LiveTileData
  options?: Record<string, unknown>
  onRegionSelect?: (name: string) => void
  selectedRegion?: string | null
}

// 12-color professional BI palette — Tableau Classic 10 adapted for OKLCH dark theme
const COLORS = [
  '#60a5fa',  // cornflower blue   (primary)
  '#fb923c',  // amber-orange      (Tableau orange)
  '#34d399',  // emerald           (Tableau green)
  '#f87171',  // rose-red          (Tableau red softened)
  '#818cf8',  // indigo            (Tableau purple adapted)
  '#2dd4bf',  // teal              (Tableau teal)
  '#facc15',  // golden yellow     (Tableau yellow)
  '#c084fc',  // soft purple       (secondary)
  '#4ade80',  // lime green        (tertiary green)
  '#f9a8d4',  // dusty pink        (Tableau pink)
  '#5eead4',  // cyan-teal         (extra)
  '#94a3b8',  // slate             (neutral)
]

function fmt(v: unknown, decimals = 1): string {
  if (v === null || v === undefined) return '—'
  const n = Number(v)
  if (isNaN(n)) return String(v)
  return n.toLocaleString('fr-FR', { maximumFractionDigits: decimals })
}

function shortLabel(v: unknown): string {
  const s = String(v ?? '')
  return s.length > 14 ? s.slice(0, 13) + '…' : s
}

function toChartData(data: LiveTileData): Record<string, unknown>[] {
  return data.rows.map(row =>
    Object.fromEntries(data.columns.map((col, i) => [col, row[i]]))
  )
}

export function LiveTileRenderer({ type, title, data, options = {}, onRegionSelect, selectedRegion }: Props) {
  const opts = options as LiveTileOptions
  const decimals = opts.decimals ?? 1
  const unit = opts.unit ?? ''

  const xKey = opts.x ?? data.columns[0] ?? 'x'
  const rawY = opts.y
  const yKeys: string[] = Array.isArray(rawY)
    ? rawY as string[]
    : rawY
      ? [rawY as string]
      : data.columns.slice(1).length > 0
        ? data.columns.slice(1)
        : [data.columns[0] ?? 'y']

  const chartData = toChartData(data)
  const tooltipFmt = (value: unknown) =>
    [`${fmt(value, decimals)}${unit ? ' ' + unit : ''}`, '']

  switch (type) {

    case 'kpi': {
      const val = data.rows[0]?.[0]
      const formatted = val === null || val === undefined
        ? '—'
        : unit ? `${fmt(val, opts.decimals ?? 0)} ${unit}` : fmt(val, opts.decimals ?? 0)
      return (
        <div data-testid="tile-kpi" style={{ textAlign: 'center', padding: '8px 0' }}>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--accent-soft)', letterSpacing: '-.02em' }}>
            {formatted}
          </div>
          {unit && <div style={{ color: 'var(--muted)', fontSize: 12 }}>{unit}</div>}
        </div>
      )
    }

    case 'bar':
      return (
        <div data-testid="tile-bar">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 20, left: 4 }}>
              <CartesianGrid stroke="oklch(25% 0.04 265)" strokeDasharray="3 3" />
              <XAxis dataKey={xKey} tickFormatter={shortLabel} tick={{ fontSize: 10, fill: 'var(--muted)' }} angle={-25} textAnchor="end" interval={0} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--muted)' }} width={40} />
              <Tooltip formatter={tooltipFmt} contentStyle={{ background: 'var(--surface-solid)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text)' }} />
              {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '0.7rem' }} />}
              {yKeys.map((k, i) => (
                <Bar key={k} dataKey={k} fill={COLORS[i % COLORS.length]} radius={[4, 4, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )

    case 'line':
      return (
        <div data-testid="tile-line">
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 4 }}>
              <CartesianGrid stroke="oklch(25% 0.04 265)" strokeDasharray="3 3" />
              <XAxis dataKey={xKey} tick={{ fontSize: 10, fill: 'var(--muted)' }} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--muted)' }} width={40} />
              <Tooltip formatter={tooltipFmt} contentStyle={{ background: 'var(--surface-solid)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text)' }} />
              {yKeys.length > 1 && <Legend wrapperStyle={{ fontSize: '0.7rem' }} />}
              {yKeys.map((k, i) => (
                <Line key={k} type="monotone" dataKey={k} stroke={COLORS[i % COLORS.length]} strokeWidth={2.5} dot={{ r: 2 }} activeDot={{ r: 4 }} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )

    case 'pie': {
      const nameKey = (opts.name ?? xKey)
      const valueKey = (opts.value ?? yKeys[0])
      return (
        <div data-testid="tile-pie">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={chartData} dataKey={valueKey} nameKey={nameKey} cx="50%" cy="50%" innerRadius={45} outerRadius={80} paddingAngle={2}
                label={({ name, percent }: { name: string; percent: number }) => `${shortLabel(name)} ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v: unknown) => fmt(v, decimals)} contentStyle={{ background: 'var(--surface-solid)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text)' }} />
              <Legend wrapperStyle={{ fontSize: '0.7rem' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )
    }

    case 'table':
      return <TableTile data={data} />

    case 'grid': {
      const facetKey = (opts.facet_by ?? data.columns[0] ?? '')
      const facetIdx = data.columns.indexOf(facetKey)
      const xColKey = opts.x ?? data.columns.find(c => c !== facetKey) ?? ''
      const xColIdx = data.columns.indexOf(xColKey)
      const rawYGrid = opts.y
      const yColKey = !Array.isArray(rawYGrid) && rawYGrid
        ? rawYGrid as string
        : data.columns.find(c => c !== facetKey && c !== xColKey) ?? ''
      const yColIdx = data.columns.indexOf(yColKey)
      const subType = opts.chart_type ?? 'bar'
      const facets = [...new Set(data.rows.map(r => r[facetIdx]))]
      return (
        <div data-testid="tile-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 8 }}>
          {facets.map((facetVal, fi) => {
            const facetData = data.rows
              .filter(r => r[facetIdx] === facetVal)
              .map(r => ({ [xColKey]: r[xColIdx], [yColKey]: r[yColIdx] }))
            const color = COLORS[fi % COLORS.length]
            return (
              <div key={String(facetVal)} style={{ background: 'var(--surface-solid)', border: '1px solid var(--border)', borderRadius: 8, padding: '4px 6px' }}>
                <div style={{ fontSize: '0.6rem', fontWeight: 600, color: 'var(--muted)', textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginBottom: 2 }}>
                  {shortLabel(facetVal)}
                </div>
                <ResponsiveContainer width="100%" height={64}>
                  {subType === 'line' ? (
                    <LineChart data={facetData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
                      <Line type="monotone" dataKey={yColKey} stroke={color} strokeWidth={1.5} dot={{ r: 1 }} isAnimationActive={false} />
                      <Tooltip formatter={tooltipFmt} contentStyle={{ background: 'var(--surface-solid)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text)', fontSize: 10 }} />
                    </LineChart>
                  ) : (
                    <BarChart data={facetData} margin={{ top: 2, right: 2, bottom: 0, left: 2 }}>
                      <Bar dataKey={yColKey} fill={color} radius={[2, 2, 0, 0]} isAnimationActive={false} />
                      <Tooltip formatter={tooltipFmt} contentStyle={{ background: 'var(--surface-solid)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text)', fontSize: 10 }} />
                    </BarChart>
                  )}
                </ResponsiveContainer>
              </div>
            )
          })}
        </div>
      )
    }

    case 'heatmap':
      return (
        <HeatmapTile
          data={data}
          title={title}
          unit={opts.unit}
          options={{
            colorScheme: (opts.colorScheme as 'blue' | 'green' | 'red' | 'orange') ?? 'blue',
            showValues: opts.showValues,
          }}
        />
      )

    case 'sparkline-kpi': {
      const pts = data.rows.map(r => Number(r[1] ?? 0))
      const cur = pts[pts.length - 1] ?? 0
      const prev = pts.length > 1 ? pts[pts.length - 2] : null
      const delta = prev !== null && prev !== 0 ? ((cur - prev) / Math.abs(prev)) * 100 : null
      const dir: 'up' | 'down' | 'flat' | null =
        delta === null ? null : delta > 0.5 ? 'up' : delta < -0.5 ? 'down' : 'flat'
      return (
        <SparklineKpi
          points={pts}
          current={cur}
          previous={prev}
          deltaPct={delta !== null ? Math.round(delta * 10) / 10 : null}
          direction={dir}
          label={title}
        />
      )
    }

    case 'map':
      return (
        <MapLibreMap
          data={data}
          title={title}
          unit={unit}
          colorScheme={(opts.colorScheme as 'blue' | 'green' | 'red' | 'orange') ?? 'blue'}
          onRegionSelect={onRegionSelect}
          selectedRegion={selectedRegion}
        />
      )

    case 'map-adm2':
      return (
        <MapAdm2
          data={data}
          title={title}
          unit={unit}
          colorScheme={(opts.colorScheme as 'blue' | 'green' | 'red' | 'orange') ?? 'blue'}
          onRegionSelect={onRegionSelect}
          selectedRegion={selectedRegion}
        />
      )

    case 'map-bivariate':
      return (
        <BivariateChoropleth
          data={data}
          title={title}
          unit={unit}
          colorScheme={(opts.colorScheme as 'classic' | 'teal-orange') ?? 'classic'}
          x1_label={data.columns[1]?.replace(/_/g, ' ')}
          x2_label={data.columns[2]?.replace(/_/g, ' ')}
        />
      )

    case 'trade-flow-map':
      return <TradeFlowMap />

    default:
      return (
        <div data-testid="tile-placeholder" style={{ padding: '16px 8px', textAlign: 'center', color: 'var(--muted)', fontSize: 12, border: '1px dashed var(--border)', borderRadius: 8 }}>
          {type}
        </div>
      )
  }
}
