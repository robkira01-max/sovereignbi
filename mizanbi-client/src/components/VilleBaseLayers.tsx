import { useMemo } from 'react'
import COMMUNES_ADMIN from '../data/admin_communes.json'
import QUARTIERS_ADMIN from '../data/admin_quartiers.json'
import OSM_VOIRIE_GEO from '../data/osm_centre_voirie.json'
import {
  COMMUNE_FILL, OSM_ROAD_STYLE, LAND_FILL, LAND_PATCH, SEA_FILL, SEA_RECT, VILLE_BOUNDS, centroidOfPolygon, linePath, polygonPath, px, py, quartierLabel,
  type GeoFeature,
} from '../lib/villeGeo'

const feats = (geo: unknown) => (geo as { features: GeoFeature[] }).features
const ROAD_ORDER = ['locale', 'tertiaire', 'secondaire', 'primaire'] as const

/** Fond de carte Djibouti-ville (communes et quartiers officiels admin_pol + routes OSM) à placer dans un <svg viewBox={VILLE_VIEWBOX}>. */
export default function VilleBaseLayers({ labels = true }: { labels?: boolean }) {
  const b = VILLE_BOUNDS
  const roads = useMemo(() => ROAD_ORDER.map(cl => ({
    cl,
    d: feats(OSM_VOIRIE_GEO).filter(f => f.properties.classe === cl).map(f => linePath(f.geometry.coordinates, b)).join(''),
  })), [b])

  return (
    <g>
      <rect {...SEA_RECT} fill={SEA_FILL} />
      <rect {...LAND_PATCH} fill={LAND_FILL} />
      {feats(COMMUNES_ADMIN).map((f, i) => (
        <path key={`comm-${i}`} d={polygonPath(f.geometry.coordinates, b)}
          fill={COMMUNE_FILL[String(f.properties.nom)] ?? 'oklch(20% 0.03 265)'} stroke="oklch(45% 0.08 265)" strokeWidth={0.8} />
      ))}
      {feats(QUARTIERS_ADMIN).map((f, i) => (
        <path key={`q-${i}`} d={polygonPath(f.geometry.coordinates, b)}
          fill="oklch(28% 0.04 265 / .35)" stroke="oklch(55% 0.07 265)" strokeWidth={0.4} strokeLinejoin="round" />
      ))}
      {roads.map(({ cl, d }) => (
        <path key={cl} d={d} fill="none" stroke={OSM_ROAD_STYLE[cl].color}
          strokeWidth={OSM_ROAD_STYLE[cl].w} strokeLinecap="round" strokeLinejoin="round" />
      ))}
      {labels && feats(QUARTIERS_ADMIN).map((f, i) => {
        const txt = quartierLabel(String(f.properties.nom), Number(f.properties.superficie_ha))
        if (!txt) return null
        const [clon, clat] = centroidOfPolygon(f.geometry.coordinates)
        return (
          <text key={`ql-${i}`} x={px(clon, b).toFixed(1)} y={py(clat, b).toFixed(1)}
            textAnchor="middle" dominantBaseline="middle" fontSize={5.5} fontStyle="italic"
            fill="oklch(82% 0.06 200)" stroke="oklch(12% 0.03 265)" strokeWidth={1.4} paintOrder="stroke"
            style={{ pointerEvents: 'none', userSelect: 'none' }}>
            {txt}
          </text>
        )
      })}
    </g>
  )
}
