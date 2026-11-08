import { useMemo } from 'react'
import { buildDjiboutiMap } from '../lib/geo'
import { REGIONS } from '../data/demo'
import { colorForValue, currentTheme, scaleFor, textOnFill, type ChoroplethScale, type IndicatorId } from '../lib/theme'

interface Props {
  selected?: string | null
  onSelect?: (name: string) => void
  height?: number
  /** Indicateur affiché sur la carte (par défaut : chômage). */
  indicator?: IndicatorId
  /** Valeurs par région ; par défaut, celles de l'indicateur choisi dans demo.ts. */
  values?: Record<string, number>
  unit?: string
}

function valueFor(region: (typeof REGIONS)[number], indicator: IndicatorId): number {
  if (indicator === 'poverty') return region.poverty ?? 0
  if (indicator === 'population') return region.population
  return region.unemployment
}

// P-028 : la couleur de chaque région vient de sa valeur via colorForValue(),
// sur une échelle calculée sur les valeurs affichées (min/max réels + quartiles).
// La légende affiche les bornes réelles, la médiane et le seuil d'alerte (25 %).
export default function DjiboutiMap({ selected, onSelect, height, indicator = 'unemployment', values, unit = '%' }: Props) {
  const geo = useMemo(() => buildDjiboutiMap(), [])
  const scale: ChoroplethScale = useMemo(() => {
    const vals = REGIONS.map((r) => values?.[r.name] ?? valueFor(r, indicator))
    return scaleFor(vals, currentTheme(), unit, indicator === 'unemployment'
      ? { reference: 25, referenceLabel: 'Seuil d’alerte chômage : 25 % (démo, 2024)' }
      : { reference: null, referenceLabel: '' })
  }, [indicator, values, unit])
  const valOf = (name: string) => {
    const r = REGIONS.find((x) => x.name === name)
    if (!r) return null
    return values?.[name] ?? valueFor(r, indicator)
  }
  return (
    <div dir="ltr" style={{ width: '100%' }}>
      <div style={{ position: 'relative', width: '100%', maxWidth: 340, margin: '0 auto', aspectRatio: geo.ratio }}>
        <svg viewBox={geo.view} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} role="img" aria-label="Carte de Djibouti par région">
          {geo.shapes.map((g) => {
            const v = valOf(g.name)
            return (
              <path
                key={g.key}
                d={g.d}
                fill={v === null ? 'oklch(30% 0.04 265)' : colorForValue(v, scale)}
                stroke={selected === g.name ? '#f0f0fa' : 'oklch(85% 0.03 265)'}
                strokeWidth={selected === g.name ? 2 : 0.8}
                strokeLinejoin="round"
                style={{ cursor: onSelect ? 'pointer' : 'default' }}
                onClick={() => onSelect?.(g.name)}
              >
                <title>{`${g.name} — ${v ?? '—'} ${unit}`}</title>
              </path>
            )
          })}
        </svg>
        {geo.shapes.map((g) => {
          const v = valOf(g.name)
          const fg = v === null ? '#fff' : textOnFill(v, scale)
          return (
            <div
              key={g.key + '-label'}
              style={{
                position: 'absolute', left: `${((g.x + 6) / geo.w) * 100}%`, top: `${((g.y + 6) / geo.h) * 100}%`,
                transform: 'translate(-50%,-50%)', pointerEvents: 'none', textAlign: 'center',
                fontSize: 11, lineHeight: 1.15, fontWeight: 600,
                color: fg,
                textShadow: fg === '#070711' ? '0 1px 2px rgba(255,255,255,.55)' : '0 1px 3px oklch(10% 0.04 265), 0 0 6px oklch(10% 0.04 265)',
              }}
            >
              {g.name}
              <br />
              <b style={{ fontSize: 13 }}>{v !== null ? `${String(v).replace('.', ',')} ${unit}` : ''}</b>
            </div>
          )
        })}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--muted)', marginTop: 8 }}>
        <span>{String(scale.min).replace('.', ',')} {unit}</span>
        <span className="legend-bar" />
        <span>{String(scale.max).replace('.', ',')} {unit}</span>
      </div>
      <div className="muted" style={{ marginTop: 6 }}>
        Médiane : {String(scale.median).replace('.', ',')} {unit} · Quartiles : {String(scale.q1).replace('.', ',')} / {String(scale.q3).replace('.', ',')} {unit}
        {scale.reference !== null ? ` · ${scale.referenceLabel}` : ''}
        <br />
        Source : geoBoundaries ADM1 (licence ouverte), contours réels. Données : Démo.
        {selected ? ` Région sélectionnée : ${selected} — ${REGIONS.find((r) => r.name === selected)?.population.toLocaleString('fr-FR')} hab.` : ''}
      </div>
      {height ? null : null}
    </div>
  )
}
