import { useCallback, useEffect, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import 'maplibre-gl/dist/maplibre-gl.css'
import { TRADE_FLOWS, MAX_TONNAGE_K, type TradeFlow } from '../data/trade_flows'

interface ArcInfo {
  flow: TradeFlow
  d: string
  destX: number
  destY: number
  width: number
}

const BASEMAP: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    carto: {
      type: 'raster',
      tiles: ['https://basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://carto.com/attributions">CARTO</a>',
    },
  },
  layers: [{ id: 'basemap', type: 'raster', source: 'carto' }],
}

function arcPath(p1: { x: number; y: number }, p2: { x: number; y: number }): string {
  const mx = (p1.x + p2.x) / 2
  const my = (p1.y + p2.y) / 2
  const dx = p2.x - p1.x
  const dy = p2.y - p1.y
  const cpx = mx - dy * 0.42
  const cpy = my + dx * 0.42
  return `M ${p1.x.toFixed(1)} ${p1.y.toFixed(1)} Q ${cpx.toFixed(1)} ${cpy.toFixed(1)} ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`
}

let _pmtilsRegisteredFlow = false

export function TradeFlowMap() {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef       = useRef<maplibregl.Map | null>(null)
  const svgRef       = useRef<SVGSVGElement | null>(null)
  const rafRef       = useRef<number>(0)
  const startRef     = useRef<number>(0)
  const arcEls       = useRef<(SVGPathElement | null)[]>([])

  const [arcs, setArcs]       = useState<ArcInfo[]>([])
  const [hovered, setHovered] = useState<TradeFlow | null>(null)
  const [mapReady, setMapReady] = useState(false)

  const updateArcs = useCallback(() => {
    const map = mapRef.current
    if (!map) return
    const infos: ArcInfo[] = TRADE_FLOWS.map(flow => {
      const p1 = map.project(flow.from as [number, number])
      const p2 = map.project(flow.to as [number, number])
      return {
        flow,
        d: arcPath(p1, p2),
        destX: p2.x,
        destY: p2.y,
        width: 1.5 + (flow.tonnageK / MAX_TONNAGE_K) * 4.5,
      }
    })
    setArcs(infos)
  }, [])

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    if (!_pmtilsRegisteredFlow) {
      const proto = new Protocol()
      maplibregl.addProtocol('pmtiles', proto.tile)
      _pmtilsRegisteredFlow = true
    }
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASEMAP,
      center: [41.0, 10.5], zoom: 4.8, minZoom: 3, maxZoom: 10,
      attributionControl: false,
    })
    mapRef.current = map
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')
    map.on('load',   () => { setMapReady(true); updateArcs() })
    map.on('move',   updateArcs)
    map.on('zoom',   updateArcs)
    map.on('resize', updateArcs)
    return () => { cancelAnimationFrame(rafRef.current); map.remove(); mapRef.current = null }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!mapReady) return
    const animate = (time: number) => {
      if (!startRef.current) startRef.current = time
      const elapsed = time - startRef.current
      TRADE_FLOWS.forEach((flow, i) => {
        const el = arcEls.current[i]
        if (!el) return
        const duration = 2200 + i * 500
        const phase    = (elapsed % duration) / duration
        el.setAttribute('stroke-dashoffset', (300 - phase * 600).toFixed(1))
      })
      rafRef.current = requestAnimationFrame(animate)
    }
    rafRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafRef.current)
  }, [mapReady])

  const svgW = containerRef.current?.clientWidth  ?? 600
  const svgH = containerRef.current?.clientHeight ?? 340

  return (
    <div data-testid="tile-trade-flow" style={{ width: '100%', position: 'relative' }}>
      <div ref={containerRef} style={{ width: '100%', height: 340, borderRadius: 8, overflow: 'hidden' }} />

      {mapReady && (
        <svg
          ref={svgRef}
          viewBox={`0 0 ${svgW} ${svgH}`}
          style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: 340, pointerEvents: 'none', overflow: 'visible' }}
        >
          {arcs.map((arc, i) => (
            <g key={arc.flow.id}>
              <path d={arc.d} fill="none" stroke={arc.flow.color} strokeWidth={arc.width} strokeOpacity={0.22} strokeLinecap="round" />
              <path
                ref={el => { arcEls.current[i] = el }}
                d={arc.d} fill="none" stroke={arc.flow.color}
                strokeWidth={arc.width + 1} strokeOpacity={0.92} strokeLinecap="round"
                strokeDasharray="20 300" strokeDashoffset="300"
              />
              <text x={arc.destX + 7} y={arc.destY + 4} fontSize="11" fontFamily="'Instrument Sans', sans-serif" fill="#e2e8f0" style={{ pointerEvents: 'none' }}>
                {arc.flow.destination}
              </text>
              <circle cx={arc.destX} cy={arc.destY} r={3} fill={arc.flow.color} fillOpacity={0.9} />
            </g>
          ))}
          {arcs.length > 0 && (() => {
            const map = mapRef.current
            if (!map) return null
            const p = map.project(TRADE_FLOWS[0].from as [number, number])
            return (
              <g>
                <circle cx={p.x} cy={p.y} r={8} fill="#f8fafc" fillOpacity={0.15} stroke="#f8fafc" strokeWidth={1.5} />
                <circle cx={p.x} cy={p.y} r={4} fill="#f8fafc" />
                <text x={p.x + 12} y={p.y + 4} fontSize="11" fontFamily="'Instrument Sans', sans-serif" fill="#f8fafc" fontWeight="600">
                  Port de Djibouti
                </text>
              </g>
            )
          })()}
        </svg>
      )}

      <div style={{
        position: 'absolute', top: 10, left: 10,
        background: 'oklch(10% 0.025 265 / 0.78)',
        backdropFilter: 'blur(8px)',
        borderRadius: 10, padding: '8px 12px',
        display: 'flex', flexDirection: 'column', gap: 5,
        pointerEvents: 'auto',
      }}>
        <div style={{ fontSize: 10, color: 'oklch(72% 0.03 265)', marginBottom: 2, fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
          Flux 2024 (k tonnes/an)
        </div>
        {TRADE_FLOWS.map(flow => (
          <div
            key={flow.id}
            onMouseEnter={() => setHovered(flow)}
            onMouseLeave={() => setHovered(null)}
            style={{
              display: 'flex', alignItems: 'center', gap: 7, cursor: 'default',
              opacity: hovered && hovered.id !== flow.id ? 0.45 : 1,
              transition: 'opacity 0.15s',
            }}
          >
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: flow.color, flexShrink: 0 }} />
            <span style={{ fontSize: 11, color: '#e2e8f0', flex: 1 }}>{flow.commodity}</span>
            <span style={{ fontSize: 11, color: 'oklch(72% 0.03 265)', fontFamily: "'JetBrains Mono', monospace" }}>
              {flow.tonnageK.toLocaleString('fr-FR')}
            </span>
          </div>
        ))}
      </div>

      <div style={{ position: 'absolute', bottom: 22, left: 10, fontSize: 10, color: 'oklch(55% 0.03 265)', pointerEvents: 'none' }}>
        * Données synthétiques — modèle illustratif
      </div>
    </div>
  )
}
