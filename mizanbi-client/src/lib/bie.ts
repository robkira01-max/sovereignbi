// P-030 — BIE, Ministère des Finances de Djibouti.
// Données RÉELLES extraites des Bulletins d'information économique (BIE) et
// des Notes de conjoncture trimestrielles, téléchargés le 2026-11-08 depuis
// https://www.ministere-finances.dj/BIE.html (snapshot local, aucune requête
// réseau). Ne JAMAIS mélanger ces chiffres aux chiffres démo de Djibouti
// (1 030 000 hab. / 23,5 %) ni aux données StatCan Canada : séries, page et
// provenances séparées. Méthode : dernière vintage disponible par année
// (quand deux bulletins diffèrent, la valeur du bulletin le plus récent est
// retenue et l'écart est signalé dans la source).
import series from '../data/bie/bie_series.json'
import sources from '../data/bie/bie_sources.json'

export interface BieSource { document: string; url: string; page: string; note?: string }
export interface BieValue { year: number; value: number; status: string; source?: BieSource }
export interface BieIndicator {
  id: string; label_fr: string; unit: string
  values: BieValue[]; missing?: number[]; missing_note?: string
}
export interface BieForecastValue { year: number; central: number; low: number; high: number }
export interface BieForecast {
  indicator: string; label_fr: string; unit: string; method: string
  horizon: string; residual_sd: number; values: BieForecastValue[]; warning: string
}

export const BIE = series as unknown as {
  downloaded: string; source_page: string; method: string
  indicators: BieIndicator[]
  ministry_forecasts_2008: { label: string; source: BieSource; croissance_pib_reel: { year: number; value: number }[]; pib_nominal_mfd: { year: number; value: number }[]; inflation_fin_periode: { year: number; value: number }[] }
  forecasts_model: BieForecast[]
  no_forecast: { indicator: string; reason: string }[]
  coverage: { year: number; status: string; detail: string }[]
}
export const BIE_SOURCES = sources as unknown as {
  downloaded: string; source_page: string
  documents: { year: number; quarter: string; file: string | null; url: string | null; pages: number | null; status: string; detail?: string }[]
}

export function bieIndicator(id: string): BieIndicator | undefined {
  return BIE.indicators.find((i) => i.id === id)
}
export function bieForecast(indicator: string): BieForecast | undefined {
  return BIE.forecasts_model.find((f) => f.indicator === indicator)
}
/** Variation d'année en année en %, null si l'année précédente manque. */
export function yoy(values: BieValue[], year: number): number | null {
  const cur = values.find((v) => v.year === year)
  const prev = values.find((v) => v.year === year - 1)
  if (!cur || !prev || prev.value === 0) return null
  return ((cur.value - prev.value) / Math.abs(prev.value)) * 100
}
export function bieAttribution(source?: BieSource): string {
  if (!source) return 'Source : Ministère des Finances de Djibouti, BIE'
  return `Source : Ministère des Finances de Djibouti, ${source.document}, ${source.page}${source.note ? ` — ${source.note}` : ''}`
}
export const BIE_SNAPSHOT_DATE = '8 novembre 2026'
