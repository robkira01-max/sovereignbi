// Analytics opt-in : injecte le script uniquement si VITE_ANALYTICS_URL est défini.
// Compatible Plausible (data-domain) et Umami (data-website-id).
// Aucun appel réseau si la variable est absente — mode hors-ligne garanti.

export function initAnalytics(): void {
  const src = import.meta.env.VITE_ANALYTICS_URL as string | undefined
  if (!src) return

  const script = document.createElement('script')
  script.defer = true
  script.src = src

  const siteId = import.meta.env.VITE_ANALYTICS_SITE_ID as string | undefined
  if (siteId) {
    // Plausible attend data-domain ; Umami attend data-website-id.
    // On injecte les deux — le moteur d'analytics ignore ce qu'il ne connaît pas.
    script.setAttribute('data-domain', siteId)
    script.setAttribute('data-website-id', siteId)
  }

  document.head.appendChild(script)
}
