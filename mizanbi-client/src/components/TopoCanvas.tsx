import { useEffect, useMemo, useRef } from 'react'
import { VILLE_BOUNDS, VILLE_PAD, VILLE_W, px, py, type Coord, type GeoFeature } from '../lib/villeGeo'
import { groupByStyle, type TopoLayerDef, type TopoStyle } from '../lib/topoLayers'

// Plusieurs dizaines de milliers d'entités : un <canvas> (un tracé par groupe de style) là où
// des milliers de nœuds SVG figeraient le navigateur. Superposé à la carte, non interactif.
const BATCH = 1500

export default function TopoCanvas({ def, features }: { def: TopoLayerDef; features: GeoFeature[] }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const groups = useMemo(() => groupByStyle(features, def.style), [features, def])

  useEffect(() => {
    const cv = ref.current
    if (!cv || !cv.parentElement) return
    const parent = cv.parentElement
    const b = VILLE_BOUNDS

    let cancelled = false
    let timer = 0
    const draw = () => {
      cancelled = true // annule un tracé en cours (redimensionnement)
      window.clearTimeout(timer)
      cancelled = false
      const viewW = VILLE_W + VILLE_PAD * 2
      const viewH = b.H + VILLE_PAD * 2
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
      ctx.lineJoin = 'round'
      const path = (pts: Coord[], close: boolean) => {
        ctx.moveTo(px(pts[0][0], b), py(pts[0][1], b))
        for (let i = 1; i < pts.length; i++) ctx.lineTo(px(pts[i][0], b), py(pts[i][1], b))
        if (close) ctx.closePath()
      }
      // Un seul chemin de 80 000 sous-chemins est très lent en rendu logiciel : on trace par lots
      // et on rend la main au navigateur entre deux lots (interface réactive, annulable).
      const jobs: { style: TopoStyle; batch: GeoFeature[] }[] = []
      for (const { style, features: fs } of groups.values()) {
        for (let i = 0; i < fs.length; i += BATCH) jobs.push({ style, batch: fs.slice(i, i + BATCH) })
      }
      let k = 0
      const step = () => {
        if (cancelled) return
        const t0 = performance.now()
        while (k < jobs.length && performance.now() - t0 < 12) {
          const { style, batch } = jobs[k++]
          ctx.beginPath()
          for (const f of batch) {
            const g = f.geometry
            const c = g.coordinates
            if (g.type === 'Polygon') (c as Coord[][]).forEach(r => path(r, true))
            else if (g.type === 'MultiPolygon') (c as Coord[][][]).forEach(pg => pg.forEach(r => path(r, true)))
            else if (g.type === 'LineString') path(c as Coord[], false)
            else if (g.type === 'MultiLineString') (c as Coord[][]).forEach(l => path(l, false))
          }
          if (style.fill) { ctx.fillStyle = style.fill; ctx.fill('evenodd') }
          if (style.stroke) {
            ctx.strokeStyle = style.stroke
            ctx.lineWidth = style.width ?? 0.3
            ctx.setLineDash(style.dash ?? [])
            ctx.stroke()
          }
        }
        if (k < jobs.length) timer = window.setTimeout(step, 0)
        else ctx.setLineDash([])
      }
      step()
    }

    draw()
    const ro = new ResizeObserver(draw)
    ro.observe(parent)
    return () => { cancelled = true; window.clearTimeout(timer); ro.disconnect() }
  }, [groups])

  return <canvas ref={ref} data-testid={`topo-${def.id}`} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }} aria-hidden="true" />
}
