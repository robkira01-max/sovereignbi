/**
 * HeatmapTile — calendrier de chaleur SVG pur (style "contribution graph").
 *
 * columns[0] = champ date/période  (ex: "2024-01", "lundi", "jan")
 * columns[1] = champ valeur numérique
 * columns[2] = champ ligne (optionnel — axe Y ; ex: heure du jour "08h", région)
 *
 * Sans columns[2] : heatmap 1D. Avec columns[2] : grille 2D.
 *
 * options:
 *   colorScheme : 'blue' | 'green' | 'red' | 'orange' (défaut : 'blue')
 *   showValues  : boolean — afficher la valeur dans chaque cellule
 */
import type { LiveTileData } from './LiveTileRenderer'

interface Props {
  data: LiveTileData
  title: string
  unit?: string
  options?: {
    colorScheme?: 'blue' | 'green' | 'red' | 'orange'
    showValues?: boolean
  }
}

const PALETTES: Record<string, [string, string, string, string, string]> = {
  blue:   ['#1e293b', '#c7d2fe', '#818cf8', '#4f46e5', '#312e81'],
  green:  ['#1e293b', '#d1fae5', '#34d399', '#059669', '#065f46'],
  red:    ['#1e293b', '#fee2e2', '#f87171', '#dc2626', '#7f1d1d'],
  orange: ['#1e293b', '#ffedd5', '#fb923c', '#ea580c', '#7c2d12'],
}

function intensityColor(norm: number, palette: string[]): string {
  if (norm <= 0) return palette[0]
  if (norm < 0.25) return palette[1]
  if (norm < 0.5)  return palette[2]
  if (norm < 0.75) return palette[3]
  return palette[4]
}

export function HeatmapTile({ data, title, unit = '', options = {} }: Props) {
  const { colorScheme = 'blue', showValues = false } = options
  const palette = PALETTES[colorScheme] ?? PALETTES.blue

  const colX = data.columns[0] ?? ''
  const colV = data.columns[1] ?? ''
  const colY = data.columns[2] ?? ''

  const valueMap = new Map<string, number>()
  const xSet = new Set<string>()
  const ySet = new Set<string>()

  for (const row of data.rows) {
    const x = String(row[0] ?? '')
    const v = Number(row[1] ?? 0)
    const y = colY ? String(row[2] ?? '') : '__single__'
    xSet.add(x)
    ySet.add(y)
    valueMap.set(`${x}|${y}`, v)
  }

  const xLabels = [...xSet]
  const yLabels = [...ySet]
  const is1D    = yLabels.length === 1 && yLabels[0] === '__single__'

  const allValues = [...valueMap.values()].filter(v => !isNaN(v))
  const minVal = allValues.length ? Math.min(...allValues) : 0
  const maxVal = allValues.length ? Math.max(...allValues) : 1

  const CELL = 28
  const GAP  = 3
  const Y_LABEL_W = is1D ? 0 : 72
  const X_LABEL_H = 24
  const LEGEND_H  = 28

  const totalW = Y_LABEL_W + xLabels.length * (CELL + GAP) + 16
  const totalH = X_LABEL_H + yLabels.length * (CELL + GAP) + LEGEND_H + 8

  return (
    <div data-testid="tile-heatmap" style={{ width: '100%', overflowX: 'auto' }}>
      <svg
        width={totalW}
        height={totalH}
        style={{ display: 'block', fontFamily: 'inherit' }}
        aria-label={`${title} — heatmap`}
      >
        {xLabels.map((x, xi) => (
          <text
            key={`xl-${xi}`}
            x={Y_LABEL_W + xi * (CELL + GAP) + CELL / 2}
            y={X_LABEL_H - 6}
            textAnchor="middle"
            fontSize={9}
            fill="#94a3b8"
          >
            {x.length > 6 ? x.slice(0, 5) + '…' : x}
          </text>
        ))}

        {yLabels.map((y, yi) => (
          <g key={`row-${yi}`}>
            {!is1D && (
              <text
                x={Y_LABEL_W - 6}
                y={X_LABEL_H + yi * (CELL + GAP) + CELL / 2 + 4}
                textAnchor="end"
                fontSize={10}
                fill="#94a3b8"
              >
                {y.length > 10 ? y.slice(0, 9) + '…' : y}
              </text>
            )}
            {xLabels.map((x, xi) => {
              const rawVal = valueMap.get(`${x}|${y}`) ?? null
              const norm   = rawVal !== null && maxVal > minVal
                ? (rawVal - minVal) / (maxVal - minVal)
                : rawVal !== null ? 1 : -1
              const fill   = rawVal !== null ? intensityColor(norm, palette) : '#0f172a'
              const cx     = Y_LABEL_W + xi * (CELL + GAP)
              const cy     = X_LABEL_H + yi * (CELL + GAP)
              const valFmt = rawVal !== null
                ? (rawVal >= 1000 ? `${(rawVal / 1000).toFixed(1)}k` : String(Math.round(rawVal)))
                : ''
              return (
                <g key={`cell-${xi}-${yi}`}>
                  <rect
                    data-testid={`heatmap-cell-${xi}-${yi}`}
                    x={cx} y={cy}
                    width={CELL} height={CELL}
                    rx={4} ry={4}
                    fill={fill}
                    stroke="#1e293b"
                    strokeWidth={1}
                  >
                    <title>{`${x}${!is1D ? ` · ${y}` : ''} : ${rawVal !== null ? rawVal : '—'} ${unit}`}</title>
                  </rect>
                  {showValues && rawVal !== null && (
                    <text
                      x={cx + CELL / 2} y={cy + CELL / 2 + 4}
                      textAnchor="middle"
                      fontSize={8}
                      fill={norm > 0.5 ? '#f1f5f9' : '#475569'}
                      style={{ pointerEvents: 'none' }}
                    >
                      {valFmt}
                    </text>
                  )}
                </g>
              )
            })}
          </g>
        ))}

        {(() => {
          const ly = X_LABEL_H + yLabels.length * (CELL + GAP) + 10
          const steps = [0, 0.25, 0.5, 0.75, 1]
          return (
            <g data-testid="heatmap-legend">
              <text x={Y_LABEL_W} y={ly + 11} fontSize={9} fill="#64748b">
                {colV} {unit ? `(${unit})` : ''}
              </text>
              {steps.map((s, i) => (
                <rect
                  key={i}
                  x={Y_LABEL_W + 80 + i * (CELL / 2 + 2)}
                  y={ly}
                  width={CELL / 2} height={CELL / 2}
                  rx={2} ry={2}
                  fill={intensityColor(s, palette)}
                />
              ))}
              <text x={Y_LABEL_W + 80} y={ly + CELL / 2 + 11} fontSize={8} fill="#64748b">bas</text>
              <text
                x={Y_LABEL_W + 80 + steps.length * (CELL / 2 + 2) + 2}
                y={ly + CELL / 2 + 11}
                fontSize={8} fill="#64748b"
              >élevé</text>
            </g>
          )
        })()}
      </svg>
      <div style={{ fontSize: '0.68rem', color: '#475569', marginTop: 4 }}>
        {colX} → {colV}{colY ? ` × ${colY}` : ''}
      </div>
    </div>
  )
}
