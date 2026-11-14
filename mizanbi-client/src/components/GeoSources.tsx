import ATTRIBUTION from '../data/geo_attribution.json'

// geo_attribution.json est généré depuis data/geo/catalog.yaml par
// tools/sync_geo_attribution.py : ne pas l'éditer à la main.
type Attribution = Record<string, { name: string; provider: string; license: string }>
const ATTR = ATTRIBUTION as Attribution

interface Props {
  /** Ids de couches du catalogue géospatial (data/geo/catalog.yaml). */
  layerIds: string[]
  /** Ligne libre ajoutée après les sources (précisions, période, etc.). */
  note?: string
}

/** Pied de carte : attribution dérivée automatiquement du catalogue géospatial. */
export default function GeoSources({ layerIds, note }: Props) {
  const groups = new Map<string, { provider: string; license: string; names: string[] }>()
  for (const id of layerIds) {
    const a = ATTR[id]
    if (!a) continue
    const key = `${a.provider}|${a.license}`
    const g = groups.get(key) ?? { provider: a.provider, license: a.license, names: [] }
    g.names.push(a.name)
    groups.set(key, g)
  }

  return (
    <p className="muted" style={{ fontSize: 11, marginTop: 4, lineHeight: 1.6 }}>
      {[...groups.values()].map((g, i) => (
        <span key={i}>
          <strong>{g.provider}</strong> — {g.names.join(', ')} ({g.license}).{' '}
        </span>
      ))}
      {note}
    </p>
  )
}
