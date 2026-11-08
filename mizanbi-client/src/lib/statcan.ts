// P-027 — Connecteur Statistique Canada (Web Data Service, WDS).
// Licence ouverte de Statistique Canada : usage commercial permis, sans frais,
// avec attribution obligatoire. Aucune clé API, aucun token, aucun mot de passe
// en dur ici, et aucune requête réseau en mode démo : l'app lit uniquement le
// snapshot local embarqué dans src/data/statcan/ (téléchargé le 2026-11-07).
// Les chiffres canadiens ne sont JAMAIS mélangés aux chiffres démo de Djibouti
// (population 1 030 000 / chômage 23,5 %) : séries, pages et provenances séparées.
import chomage from '../data/statcan/statcan_chomage.json'
import population from '../data/statcan/statcan_population.json'
import ipc from '../data/statcan/statcan_ipc.json'
import emploi from '../data/statcan/statcan_emploi.json'
import sources from '../data/statcan/statcan_sources.json'

export interface ProvinceValue { province: string; value: number }
export interface TrendPoint { date: string; value: number }

export interface StatCanTable {
  table: string
  title_en: string
  title_fr: string
  series: string
  unit: string
  latest: string
  previous_year: string
  canada_latest: number
  canada_previous_year: number
  by_province_latest: ProvinceValue[]
  by_province_previous_year: ProvinceValue[]
  trend_canada: TrendPoint[]
}

export const STATCAN_CHOMAGE = chomage as unknown as StatCanTable
export const STATCAN_POPULATION = population as unknown as StatCanTable
export const STATCAN_IPC = ipc as unknown as StatCanTable & { yoy_pct: number }

// P-031 — Emploi vérifié (table 14-10-0287-01, snapshot du 8 nov. 2026) :
// variation de l'emploi sept. → oct. 2026 par province, en emplois, et
// répartition par tranche d'âge. Voir src/data/statcan/statcan_emploi.json.
export interface StatCanEmploiProvince {
  province: string
  employment_sep_2026: number
  employment_oct_2026: number
  change_jobs: number
  change_thousands: number
  unemployment_sep_2026: number
  unemployment_oct_2026: number
  unemployment_change_pt: number
  vector_employment: string
}
export interface StatCanEmploi {
  table: string
  title_fr: string
  downloaded: string
  reference: string
  previous: string
  canada: { employment_sep_2026: number; employment_oct_2026: number; change_jobs: number; unemployment_sep_2026: number; unemployment_oct_2026: number; unemployment_change_pt: number }
  by_province: StatCanEmploiProvince[]
  by_age_oct_2026: { age: string; label_fr: string; employment: number; share_pct: number; unemployment_rate: number; vector_employment: string }[]
  by_age_sep_2026: { age: string; employment: number; unemployment_rate: number }[]
}
export const STATCAN_EMPLOI = emploi as unknown as StatCanEmploi
export const STATCAN_SOURCES = sources as {
  downloaded: string
  licence: string
  attribution: string
  wds_base: string
  tables: { product_id: string; table: string; title_en: string; title_fr: string; reference_date: string; release: string; wds_url: string; csv_url: string }[]
}

export const STATCAN_SNAPSHOT_DATE = STATCAN_SOURCES.downloaded // '2026-11-07'

// Noms français des provinces (les snapshots WDS sont en anglais).
export const PROVINCE_FR: Record<string, string> = {
  'Newfoundland and Labrador': 'Terre-Neuve-et-Labrador',
  'Prince Edward Island': 'Île-du-Prince-Édouard',
  'Nova Scotia': 'Nouvelle-Écosse',
  'New Brunswick': 'Nouveau-Brunswick',
  'Quebec': 'Québec',
  'Ontario': 'Ontario',
  'Manitoba': 'Manitoba',
  'Saskatchewan': 'Saskatchewan',
  'Alberta': 'Alberta',
  'British Columbia': 'Colombie-Britannique',
}

export function provinceFr(name: string): string {
  return PROVINCE_FR[name] ?? name
}

/** Attribution exacte exigée par la Licence ouverte, en français. */
export function statcanAttribution(titleFr: string, referenceDate: string): string {
  return `Source : Statistique Canada, ${titleFr}, ${referenceDate}`
}

/** Lecture du snapshot local uniquement. Aucun réseau. */
export function getStatCanSnapshot(): { chomage: StatCanTable; population: StatCanTable; ipc: StatCanTable & { yoy_pct: number }; sources: typeof STATCAN_SOURCES } {
  return { chomage: STATCAN_CHOMAGE, population: STATCAN_POPULATION, ipc: STATCAN_IPC, sources: STATCAN_SOURCES }
}

// --- Accès live optionnel, désactivé par défaut ---
// N'est JAMAIS appelé au chargement de l'app, ni en mode démo.
// À utiliser uniquement depuis un outil d'ingestion (ex. tools/ingest_statcan.py)
// ou un refresh explicite, avec VITE_STATCAN_LIVE=1.
// Le WDS ne demande aucune clé : c'est un service public en accès libre.
export async function fetchStatCanTable(productId: string): Promise<{ downloadUrl: string }> {
  const live = (import.meta.env.VITE_STATCAN_LIVE as string | undefined) === '1'
  if (!live) {
    throw new Error('StatCan live désactivé : snapshot local utilisé. Mettre VITE_STATCAN_LIVE=1 pour autoriser un appel WDS.')
  }
  const res = await fetch(`https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/${productId}/fr`)
  if (!res.ok) throw new Error(`WDS HTTP ${res.status}`)
  const j = (await res.json()) as { status?: string; object?: string }
  if (j.status !== 'SUCCESS' || !j.object) throw new Error('WDS : table introuvable ou réponse inattendue')
  return { downloadUrl: j.object }
}
