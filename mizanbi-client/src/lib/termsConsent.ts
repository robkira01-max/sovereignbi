import { LEGAL } from './legalConfig'
import { apiFetch, isApiConfigured } from './api'

// Acceptation des CGU et de la politique de confidentialité.
// Mémorisée localement par compte (email → version) pour ne pas redemander à chaque
// connexion ; quand une API est configurée, l'acceptation est aussi enregistrée côté
// serveur (POST /compliance/consent/self : date, compte et version, sans adresse IP).
export const TERMS_KEY = 'mizan_terms_accepted'

type Store = Record<string, string>

function read(): Store {
  try {
    const raw = localStorage.getItem(TERMS_KEY)
    const v = raw ? JSON.parse(raw) : {}
    return v && typeof v === 'object' ? (v as Store) : {}
  } catch {
    return {}
  }
}

export function hasAcceptedTerms(email: string, version: string = LEGAL.version): boolean {
  return read()[email.trim().toLowerCase()] === version
}

export function markTermsAccepted(email: string, version: string = LEGAL.version): void {
  const store = read()
  store[email.trim().toLowerCase()] = version
  localStorage.setItem(TERMS_KEY, JSON.stringify(store))
}

async function postConsent(purpose: string): Promise<void> {
  await apiFetch('/compliance/consent/self', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ purpose, granted: true }),
  })
}

/** Enregistre l'acceptation. Lève une erreur si le serveur la refuse : on ne continue pas sans trace. */
export async function acceptTerms(email: string, token: string | null, version: string = LEGAL.version): Promise<void> {
  if (isApiConfigured() && token && token !== 'demo') {
    await postConsent(`cgu:${version}`)
    await postConsent(`privacy:${version}`)
  }
  markTermsAccepted(email, version)
}
