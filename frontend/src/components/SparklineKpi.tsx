/**
 * SparklineKpi — mini SVG sparkline + delta badge for KPI tiles.
 *
 * Usage:
 *   <SparklineKpi
 *     points={[12, 15, 14, 18, 20]}
 *     current={20}
 *     previous={18}
 *     deltaPct={11.11}
 *     direction="up"
 *     label="Chômage (%)"
 *   />
 */
import React from 'react'

export interface SparklineKpiProps {
  points: number[]
  current: number
  previous?: number | null
  deltaPct?: number | null
  direction?: 'up' | 'down' | 'flat' | null
  label?: string
  width?: number
  height?: number
  color?: string
}

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

const ARROW: Record<string, string> = {
  up: '↑',
  down: '↓',
  flat: '→',
}

export function SparklineKpi({
  points,
  current,
  previous,
  deltaPct,
  direction,
  label = '',
  width = 80,
  height = 32,
  color,
}: SparklineKpiProps) {
  const autoColor =
    color ??
    (direction === 'up'
      ? 'oklch(0.55 0.18 145)'
      : direction === 'down'
      ? 'oklch(0.55 0.21 25)'
      : 'oklch(0.55 0.08 250)')

  const path = buildPath(points, width, height)
  const arrow = direction ? ARROW[direction] : ''
  const badge =
    deltaPct !== null && deltaPct !== undefined
      ? `${arrow} ${deltaPct > 0 ? '+' : ''}${deltaPct.toFixed(1)}%`
      : arrow || null

  return (
    <div
      data-testid="sparkline-kpi"
      style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.75rem' }}>
        <span
          data-testid="sparkline-current"
          style={{ fontSize: '1.5rem', fontWeight: 700, lineHeight: 1 }}
        >
          {current.toLocaleString()}
        </span>
        {badge && (
          <span
            data-testid="sparkline-badge"
            style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: autoColor,
              lineHeight: 1,
              paddingBottom: '0.15rem',
            }}
          >
            {badge}
          </span>
        )}
      </div>

      {points.length >= 2 && (
        <svg
          data-testid="sparkline-svg"
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          aria-label={`Sparkline pour ${label}`}
          role="img"
          style={{ display: 'block' }}
        >
          <title>{`Sparkline — ${label}`}</title>
          <path
            d={path}
            fill="none"
            stroke={autoColor}
            strokeWidth={1.5}
            vectorEffect="non-scaling-stroke"
          />
          {/* last point dot */}
          {points.length > 0 && (() => {
            const min = Math.min(...points)
            const max = Math.max(...points)
            const range = max === min ? 1 : max - min
            const step = width / (points.length - 1)
            const lx = (points.length - 1) * step
            const ly = height - ((points[points.length - 1] - min) / range) * (height - 4) - 2
            return (
              <circle
                data-testid="sparkline-dot"
                cx={lx}
                cy={ly}
                r={2.5}
                fill={autoColor}
              />
            )
          })()}
        </svg>
      )}

      {previous !== null && previous !== undefined && (
        <span
          data-testid="sparkline-previous"
          style={{ fontSize: '0.65rem', color: 'oklch(0.55 0 0)', opacity: 0.7 }}
        >
          vs {previous.toLocaleString()}
        </span>
      )}
    </div>
  )
}
