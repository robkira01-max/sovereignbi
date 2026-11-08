import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend,
  PieChart, Pie, Cell,
} from 'recharts'
import { useLocale } from '../hooks/useLocale'
import { MapLibreMap } from './MapLibreMap'
import { MapAdm2 } from './MapAdm2'
import { BivariateChoropleth } from './BivariateChoropleth'
import { SparklineKpi } from './SparklineKpi'
import { TableTile } from './TableTile'
import { HeatmapTile } from './HeatmapTile'

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
  colorScheme?: 'blue' | 'green' | 'red' | 'orange' | 'classic' | 'teal-orange'
  facet_by?: string
  chart_type?: 'bar' | 'line'
  x1_label?: string
  x2_label?: string
  /** Enable sparkline + delta badge on KPI tiles */
  sparkline?: boolean
  sparkline_points?: number[]
  sparkline_delta_pct?: number | null
  sparkline_direction?: 'up' | 'down' | 'flat' | null
  sparkline_previous?: number | null
  /** Traffic-light thresholds for KPI: [{op:">=",value:30,color:"#ef4444",label:"Critique"}, ...] */
  thresholds?: Array<{ op?: string; value?: number; color?: string; label?: string }>
}

interface Props {
  type: string
  title: string
  data: TileData
  options?: TileOptions
  onRegionSelect?: (regionName: string) => void
  selectedRegion?: string | null
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

const _OPS: Record<string, (v: number, t: number) => boolean> = {
  '>':  (v, t) => v > t,
  '>=': (v, t) => v >= t,
  '<':  (v, t) => v < t,
  '<=': (v, t) => v <= t,
  '==': (v, t) => v === t,
  '!=': (v, t) => v !== t,
}

function evalThreshold(
  value: number,
  thresholds: TileOptions['thresholds'],
): string | undefined {
  if (!thresholds?.length) return undefined
  for (const t of thresholds) {
    if (t.op && t.value !== undefined) {
      const fn = _OPS[t.op]
      if (fn && fn(value, t.value)) return t.color ?? undefined
    } else {
      return t.color ?? undefined  // default fallback
    }
  }
  return undefined
}

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

export function TileRenderer({ type, title, data, options = {}, onRegionSelect, selectedRegion }: Props) {
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

      const thresholdColor = (val !== null && val !== undefined && options.thresholds?.length)
        ? evalThreshold(Number(val), options.thresholds)
        : undefined

      const hasSparkline =
        options.sparkline &&
        Array.isArray(options.sparkline_points) &&
        (options.sparkline_points as number[]).length >= 2

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
          {hasSparkline ? (
            <SparklineKpi
              points={options.sparkline_points as number[]}
              current={typeof val === 'number' ? val : Number(val ?? 0)}
              previous={options.sparkline_previous ?? null}
              deltaPct={options.sparkline_delta_pct ?? null}
              direction={options.sparkline_direction ?? null}
              label={title}
            />
          ) : (
            <div
              data-testid="tile-kpi-value"
              style={{
                fontSize: '1.9rem',
                fontWeight: 700,
                fontVariantNumeric: 'tabular-nums',
                color: thresholdColor ?? 'var(--brand)',
                lineHeight: 1.1,
              }}
            >
              {formatted}
            </div>
          )}
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

    // ── Table (sortable + filterable) ────────────────────────────────────────
    case 'table':
      return <TableTile data={data} />

    // ── Heatmap (SVG, calendrier de chaleur 1D ou 2D) ────────────────────────
    case 'heatmap':
      return (
        <HeatmapTile
          data={data}
          title={title}
          unit={unit}
          options={{
            colorScheme: options.colorScheme ?? 'blue',
            showValues:  options.showValues === true,
          }}
        />
      )

    // ── Choropleth map (Djibouti ADM1) ────────────────────────────────────────
    case 'map':
      return (
        <MapLibreMap
          data={data}
          title={title}
          unit={unit}
          colorScheme={options.colorScheme ?? 'blue'}
          onRegionSelect={onRegionSelect}
          selectedRegion={selectedRegion}
        />
      )

    // ── ADM2 + Quartiers choropleth (Djibouti districts / quartiers) ─────────
    case 'map-adm2':
      return (
        <MapAdm2
          data={data}
          title={title}
          unit={unit}
          colorScheme={options.colorScheme ?? 'blue'}
          options={{
            level: (options.level as 'adm2' | 'quartiers') ?? 'adm2',
            showLevelToggle: options.showLevelToggle !== false,
          }}
          onRegionSelect={onRegionSelect}
          selectedRegion={selectedRegion}
        />
      )

    // ── Bivariate choropleth (2 variables, 3×3 colour matrix) ────────────────
    case 'map-bivariate':
      return (
        <BivariateChoropleth
          data={data}
          title={title}
          unit={unit}
          x1_label={options.x1_label}
          x2_label={options.x2_label}
          colorScheme={
            (options.colorScheme as 'classic' | 'teal-orange' | undefined) ?? 'classic'
          }
        />
      )

    // ── Small multiples grid (one mini-chart per facet value) ─────────────────
    case 'grid': {
      const facetKey = options.facet_by ?? data.columns[0] ?? ''
      const facetIdx = data.columns.indexOf(facetKey)
      const xColKey = options.x ?? data.columns.find(c => c !== facetKey) ?? ''
      const xColIdx = data.columns.indexOf(xColKey)
      const rawYGrid = options.y
      const yColKey = !Array.isArray(rawYGrid) && rawYGrid
        ? rawYGrid
        : data.columns.find(c => c !== facetKey && c !== xColKey) ?? ''
      const yColIdx = data.columns.indexOf(yColKey)
      const subType = options.chart_type ?? 'bar'

      const facets = [...new Set(data.rows.map(r => r[facetIdx]))]

      return (
        <div
          data-testid="tile-grid"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))',
            gap: '8px',
          }}
        >
          {facets.map((facetVal, fi) => {
            const facetRows = data.rows.filter(r => r[facetIdx] === facetVal)
            const facetData = facetRows.map(r => ({
              [xColKey]: r[xColIdx],
              [yColKey]: r[yColIdx],
            }))
            const color = CHART_COLORS[fi % CHART_COLORS.length]
            return (
              <div
                key={String(facetVal)}
                style={{
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  padding: '4px 6px 2px',
                }}
              >
                <div style={{
                  fontSize: '0.6rem',
                  fontWeight: 600,
                  color: 'var(--muted)',
                  marginBottom: 2,
                  textAlign: 'center',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {shortLabel(facetVal)}
                </div>
                <ResponsiveContainer width="100%" height={70}>
                  {subType === 'line' ? (
                    <LineChart data={facetData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
                      <Line type="monotone" dataKey={yColKey} stroke={color} strokeWidth={1.5} dot={{ r: 2 }} isAnimationActive={false} />
                      <Tooltip formatter={tooltipFormatter} />
                    </LineChart>
                  ) : (
                    <BarChart data={facetData} margin={{ top: 2, right: 2, bottom: 0, left: 2 }}>
                      <Bar dataKey={yColKey} fill={color} radius={[2, 2, 0, 0]} isAnimationActive={false} />
                      <Tooltip formatter={tooltipFormatter} />
                    </BarChart>
                  )}
                </ResponsiveContainer>
              </div>
            )
          })}
        </div>
      )
    }

    default:
      return <div data-testid="tile-unknown">{t('tile.unknown')} {type}</div>
  }
}
