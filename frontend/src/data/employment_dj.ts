export const UNEMPLOY: Record<string, number> = {
  Obock:        33.2,
  Dikhil:       31.5,
  Tadjourah:    29.0,
  Arta:         27.4,
  Djibouti:     24.1,
  'Ali Sabieh': 22.3,
}

export const TREND_YEARS = [2009, 2012, 2015, 2017, 2019, 2021, 2024]
export const TREND_VALS  = [60.2, 54.8, 48.3, 40.1, 35.7, 29.6, 25.8]

export function regionColor(val: number): string {
  const t = (val - 22) / 11
  const l = 32 + t * 30
  const c = 0.12 + t * 0.08
  return `oklch(${l}% ${c} 265)`
}

export function buildTrendPoints(vals: number[], W = 300, H = 120): string {
  const mn = Math.min(...vals) - 2
  const mx = Math.max(...vals) + 2
  return vals.map((v, i) => {
    const x = (i / (vals.length - 1)) * W
    const y = H - ((v - mn) / (mx - mn)) * H
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}

export function buildAreaPoints(vals: number[], W = 300, H = 120): string {
  const mn = Math.min(...vals) - 2
  const mx = Math.max(...vals) + 2
  const pts = vals.map((v, i) => {
    const x = (i / (vals.length - 1)) * W
    const y = H - ((v - mn) / (mx - mn)) * H
    return `${x.toFixed(1)},${y.toFixed(1)}`
  })
  return `0,${H} ${pts.join(' ')} ${W},${H}`
}

export function buildMap(features: GeoJSON.Feature[]) {
  const W = 300
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity
  features.forEach(f => {
    const coords = (f.geometry as GeoJSON.Polygon).coordinates[0]
    coords.forEach(([x, y]) => {
      if (x < x0) x0 = x; if (x > x1) x1 = x
      if (y < y0) y0 = y; if (y > y1) y1 = y
    })
  })
  const midLat = (y0 + y1) / 2
  const k = Math.cos(midLat * Math.PI / 180)
  const sc = W / ((x1 - x0) * k)
  const H = (y1 - y0) * sc
  const px = (x: number) => (x - x0) * k * sc
  const py = (y: number) => (y1 - y) * sc
  const viewBox = `-6 -6 ${W + 12} ${H + 12}`
  const ratio = (W + 12) / (H + 12)

  const shapes = features.map(f => {
    const name = (f.properties as { shapeName: string }).shapeName
    const coords = (f.geometry as GeoJSON.Polygon).coordinates[0]
    const d = coords.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${px(x).toFixed(1)},${py(y).toFixed(1)}`).join(' ') + 'Z'
    const cx = coords.reduce((s, [x]) => s + x, 0) / coords.length
    const cy = coords.reduce((s, [, y]) => s + y, 0) / coords.length
    const lx = `${(px(cx) / (W + 12) * 100).toFixed(1)}%`
    const ly = `${(py(cy) / (H + 12) * 100).toFixed(1)}%`
    const val = UNEMPLOY[name] ?? 25
    return { name, d, lx, ly, val, fill: regionColor(val) }
  })

  return { viewBox, ratio, shapes }
}
