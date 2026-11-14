import { useEffect, useRef } from 'react'
import { VILLE_BOUNDS, VILLE_PAD, VILLE_W, px, py, type Coord, type GeoFeature } from '../lib/villeGeo'

// 98k empreintes de bâtiments : un <canvas> (un seul fill/stroke) là où 98k
// nœuds SVG figeraient le navigateur. Superposé à la carte, non interactif.
export default function BuildingsCanvas({ features }: { features: GeoFeature[] }) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const cv = ref.current
    if (!cv || !cv.parentElement) return
    const parent = cv.parentElement

    const draw = () => {
      const viewW = VILLE_W + VILLE_PAD * 2
      const viewH = VILLE_BOUNDS.H + VILLE_PAD * 2
      const wCss = parent.clientWidth
      const hCss = (wCss * viewH) / viewW
      const dpr = window.devicePixelRatio || 1
      cv.width = Math.round(wCss * dpr)
      cv.height = Math.round(hCss * dpr)
      cv.style.width = `${wCss}px`
      cv.style.height = `${hCss}px`
      const ctx = cv.getContext('2d')
      if (!ctx) return
      const s = (wCss * dpr) / viewW
      ctx.setTransform(s, 0, 0, s, VILLE_PAD * s, VILLE_PAD * s)
      ctx.clearRect(-VILLE_PAD, -VILLE_PAD, viewW, viewH)
      ctx.lineWidth = 0.25
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.55)'
      ctx.fillStyle = 'rgba(148, 163, 184, 0.12)'
      const b = VILLE_BOUNDS
      const ring = (r: Coord[]) => {
        ctx.moveTo(px(r[0][0], b), py(r[0][1], b))
        for (let i = 1; i < r.length; i++) ctx.lineTo(px(r[i][0], b), py(r[i][1], b))
        ctx.closePath()
      }
      ctx.beginPath()
      for (const f of features) {
        const g = f.geometry
        if (g.type === 'Polygon') (g.coordinates as Coord[][]).forEach(ring)
        else if (g.type === 'MultiPolygon') (g.coordinates as Coord[][][]).forEach(pg => pg.forEach(ring))
      }
      ctx.fill('evenodd')
      ctx.stroke()
    }

    draw()
    const ro = new ResizeObserver(draw)
    ro.observe(parent)
    return () => ro.disconnect()
  }, [features])

  return <canvas ref={ref} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }} aria-hidden="true" />
}
