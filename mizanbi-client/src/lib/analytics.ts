// Analytics opt-in ET soumis au consentement : le script n'est injecté que si
//   1. l'opérateur a défini VITE_ANALYTICS_URL (désactivé par défaut), ET
//   2. l'utilisateur a accepté (startAnalytics n'est appelé qu'après consentement).
// Aucun appel réseau sinon — mode hors ligne garanti.
// Compatible Plausible (data-domain) et Umami (data-website-id) : outils sans cookie.

const SCRIPT_ID = 'mizan-analytics'

export function isAnalyticsConfigured(): boolean {
  return Boolean(import.meta.env.VITE_ANALYTICS_URL as string | undefined)
}

export function isAnalyticsRunning(): boolean {
  return typeof document !== 'undefined' && document.getElementById(SCRIPT_ID) !== null
}

/** Charge le script de mesure d'audience. À n'appeler qu'après consentement. */
export function startAnalytics(): boolean {
  const src = import.meta.env.VITE_ANALYTICS_URL as string | undefined
  if (!src || typeof document === 'undefined' || isAnalyticsRunning()) return false

  const script = document.createElement('script')
  script.id = SCRIPT_ID
  script.defer = true
  script.src = src

  const siteId = import.meta.env.VITE_ANALYTICS_SITE_ID as string | undefined
  if (siteId) {
    // Plausible attend data-domain ; Umami attend data-website-id.
    script.setAttribute('data-domain', siteId)
    script.setAttribute('data-website-id', siteId)
  }

  document.head.appendChild(script)
  return true
}

/**
 * Retire le script (retrait du consentement). Un script déjà exécuté ne se « décharge » pas :
 * renvoie true si un rechargement de la page est nécessaire pour l'arrêter réellement.
 */
export function stopAnalytics(): boolean {
  if (typeof document === 'undefined') return false
  const el = document.getElementById(SCRIPT_ID)
  if (!el) return false
  el.remove()
  return true
}
