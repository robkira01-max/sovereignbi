// Informations propres à l'éditeur, utilisées par les pages juridiques (confidentialité,
// CGU, cookies, mentions légales). UN SEUL endroit à compléter avant publication.
//
// Une valeur « [À COMPLÉTER : …] » est un placeholder : elle s'affiche surlignée dans les
// pages. Tant que `draft` est true, les pages portent un bandeau « version de travail ».
// Quand toutes les valeurs sont renseignées et le texte validé par un juriste, passer
// `draft` à false : un test échoue s'il reste un placeholder alors que draft est false.

export const PLACEHOLDER_RE = /\[À COMPLÉTER[^\]]*\]/g

const todo = (label: string) => `[À COMPLÉTER : ${label}]`

export interface LegalConfig {
  /** true = version de travail (bandeau d'avertissement, placeholders tolérés). */
  draft: boolean
  /** Version des CGU / de la politique : AAAA-MM. Un changement redemande l'acceptation. */
  version: string
  /** Date de dernière mise à jour affichée (texte libre). */
  updated: { fr: string; en: string }
  company: string
  address: string
  phone: string
  registration: string
  publisher: string
  contactEmail: string
  privacyEmail: string
  privacyOfficer: string
  host: string
  hostRegion: string
  /** Fournisseur d'IA externe éventuel et pays de traitement ; « aucun » si IA locale uniquement. */
  aiProvider: string
  aiCountry: string
  /** Droit applicable et juridiction compétente. */
  law: string
  /** Autorité de contrôle / de plainte en protection des données. */
  authority: string
  retentionAccounts: string
  retentionLogs: string
  retentionData: string
}

export const LEGAL: LegalConfig = {
  draft: true,
  version: '2026-11',
  updated: { fr: '14 novembre 2026', en: '14 November 2026' },
  company: todo("nom de l'entreprise"),
  address: todo('adresse professionnelle'),
  phone: todo('téléphone'),
  registration: todo("numéro d'enregistrement de l'entreprise, si applicable"),
  publisher: todo('nom ou fonction du responsable de publication'),
  contactEmail: todo('courriel de contact'),
  privacyEmail: todo('courriel de confidentialité'),
  privacyOfficer: todo('nom ou fonction du responsable de la protection des renseignements personnels'),
  host: todo("hébergeur et adresse de l'hébergement"),
  hostRegion: todo("région du serveur d'hébergement"),
  aiProvider: todo("fournisseur d'IA externe, ou « aucun » si l'IA reste locale"),
  aiCountry: todo('pays de traitement du fournisseur'),
  law: todo('droit applicable et juridiction'),
  authority: todo('autorité de protection des données compétente'),
  retentionAccounts: todo('durée de conservation des comptes'),
  retentionLogs: todo('durée de conservation des journaux techniques'),
  retentionData: todo('durée de conservation des données importées'),
}

/** Valeurs de configuration encore à compléter (clés). */
export function unresolvedConfig(cfg: LegalConfig = LEGAL): string[] {
  return (Object.entries(cfg) as [string, unknown][])
    .filter(([, v]) => typeof v === 'string' && new RegExp(PLACEHOLDER_RE.source).test(v))
    .map(([k]) => k)
}
