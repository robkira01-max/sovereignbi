import { useMemo } from 'react'
import COMMUNES_GEO from '../data/cerd_communes.json'
import SECTEURS_GEO from '../data/cerd_secteurs.json'
import OSM_VOIRIE_GEO from '../data/osm_centre_voirie.json'
import OSM_LIEUX_GEO from '../data/osm_centre_lieux.json'
import { OSM_ROAD_STYLE, VILLE_BOUNDS, linePath, polygonPath, px, py, type Coord, type GeoFeature } from '../lib/villeGeo'

const feats = (geo: unknown) => (geo as { features: GeoFeature[] }).features
const ROAD_ORDER = ['locale', 'tertiaire', 'secondaire', 'primaire'] as const

/** Fond de carte Djibouti-ville (CERD Balbala + OSM centre) à placer dans un <svg viewBox={VILLE_VIEWBOX}>. */
export default function VilleBaseLayers({ labels = true }: { labels?: boolean }) {
  const b = VILLE_BOUNDS
  const roads = useMemo(() => ROAD_ORDER.map(cl => ({
    cl,
    d: feats(OSM_VOIRIE_GEO).filter(f => f.properties.classe === cl).map(f => linePath(f.geometry.coordinates, b)).join(''),
  })), [b])

  return (
    <g>
      {feats(COMMUNES_GEO).map((f, i) => (
        <path key={`comm-${i}`} d={polygonPath(f.geometry.coordinates, b)}
          fill="oklch(18% 0.03 265)" stroke="oklch(45% 0.08 265)" strokeWidth={0.8} />
      ))}
      {feats(SECTEURS_GEO).map((f, i) => (
        <path key={`sect-${i}`} d={polygonPath(f.geometry.coordinates, b)}
          fill="oklch(24% 0.04 265 / .4)" stroke="oklch(55% 0.08 265)" strokeWidth={0.5} strokeDasharray="3 2" />
      ))}
      {roads.map(({ cl, d }) => (
        <path key={cl} d={d} fill="none" stroke={OSM_ROAD_STYLE[cl].color}
          strokeWidth={OSM_ROAD_STYLE[cl].w} strokeLinecap="round" strokeLinejoin="round" />
      ))}
      {labels && feats(OSM_LIEUX_GEO).map((f, i) => {
        const c = f.geometry.coordinates as Coord
        return (
          <text key={`lieu-${i}`} x={px(c[0], b).toFixed(1)} y={py(c[1], b).toFixed(1)}
            textAnchor="middle" dominantBaseline="middle" fontSize={6.5} fontStyle="italic"
            fill="oklch(82% 0.06 200)" stroke="oklch(12% 0.03 265)" strokeWidth={1.6} paintOrder="stroke"
            style={{ pointerEvents: 'none', userSelect: 'none' }}>
            {String(f.properties.nom)}
          </text>
        )
      })}
    </g>
  )
}
