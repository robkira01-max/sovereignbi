export type Adm2Level = 'adm2' | 'quartiers'

interface LevelConfig {
  /** Dernier segment de /api/v1/geo/dj/{endpoint}. */
  endpoint: string
  /** Propriété GeoJSON utilisée pour joindre les données de la tuile. */
  nameKey: string
  center: [number, number]
  zoom: number
  labelSize: number
  /** Mention de source affichée sous la carte (null = aucune). */
  note: string | null
}

export const ADM2_LEVELS: Record<Adm2Level, LevelConfig> = {
  adm2: {
    endpoint: 'adm2', nameKey: 'name', center: [42.65, 11.85], zoom: 7.2, labelSize: 11, note: null,
  },
  quartiers: {
    endpoint: 'admin_quartiers', nameKey: 'nom', center: [43.12, 11.585], zoom: 11, labelSize: 9,
    note: 'Source : CERD admin_pol (2014) · 91 quartiers officiels',
  },
}

/** Clé de jointure tolérante : minuscules, sans accents, apostrophes ni espaces multiples. */
export function normName(s: string): string {
  return s
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[’']/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

export function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

/** Ligne HTML complémentaire du popup selon le niveau (les valeurs viennent du GeoJSON servi par l'API). */
export function popupExtra(level: Adm2Level, p: Record<string, unknown>): string {
  if (level === 'quartiers') {
    const parts: string[] = []
    if (p.commune) parts.push(`Commune : ${escapeHtml(String(p.commune))}`)
    if (p.superficie_ha) parts.push(`${Number(p.superficie_ha).toLocaleString('fr-FR')} ha`)
    return parts.length ? `<br/>${parts.join(' · ')}` : ''
  }
  return p.population_est ? `<br/>Pop. : ${Number(p.population_est).toLocaleString('fr-FR')}` : ''
}
