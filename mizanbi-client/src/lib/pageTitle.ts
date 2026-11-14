export const APP_TITLE = 'MizanBI | Business Intelligence souveraine et IA'

/** Titre d'onglet unique par écran : « Écran | MizanBI » (titre par défaut sans écran). */
export function documentTitle(label?: string | null): string {
  const l = label?.trim()
  return l ? `${l} | MizanBI` : APP_TITLE
}
