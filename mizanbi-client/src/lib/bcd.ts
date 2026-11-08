// P-033 — BCD 2024 + INSTAD RGPH-3.
// Données RÉELLES, snapshot local du 8 nov. 2026, séparées des chiffres démo
// de Djibouti (1 030 000 hab. / 23,5 %) et du BIE (2001-2012).
// BCD : valeurs extraites de la Synthèse du Rapport Annuel 2024 (p. 2-3).
// INSTAD : RGPH-3, résultats provisoires août 2024, définitifs juin 2025.
// Aucune carte dans la page BCD : l'utilisateur a demandé de retirer la
// cartographie des images, elle ne ressemblait pas à Djibouti.
import bcd from '../data/bcd/bcd_2024.json'
import rgph from '../data/instad/rgph3.json'

export interface BcdKpi { id: string; label_fr: string; unit: string; value_2023?: number; value_2024?: number; variation_pct?: number; note?: string }
export const BCD = bcd as unknown as { downloaded: string; source: string; source_url: string; method: string; kpis: BcdKpi[] }
export const RGPH3 = rgph as unknown as {
  population_2024: number; population_2009: number; croissance_annuelle_moyenne_pct: number
  ville_djibouti: { habitants: number; part_pct: number; part_provisoire_pct: number; note: string }
  age_moyen: number; age_median: number; menages: number; taille_moyenne_menage: number
  urbain_pct: number; population_femmes: number; population_hommes: number
  date_reference: string; source: string
}
export function bcdKpi(id: string): BcdKpi | undefined { return BCD.kpis.find((k) => k.id === id) }
export const BCD_ATTRIBUTION = 'Source : Banque Centrale de Djibouti, Rapport Annuel 2024 (Synthèse, p. 2-3)'
export const RGPH3_ATTRIBUTION = 'Source : INSTAD, RGPH-3, résultats provisoires août 2024, définitifs juin 2025'
export const BCD_SNAPSHOT_DATE = '8 novembre 2026'
