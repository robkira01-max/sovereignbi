// Pastille « jeu de données certifié » (P-069). Logique pure, testable sans DOM.
// Ce que la pastille atteste : un administrateur a enregistré qu'une institution a validé la table,
// et les données n'ont pas changé depuis. Le serveur ne vérifie pas l'institution.
import { apiJson, isApiConfigured } from './api'

export type CertStatus = 'certified' | 'stale' | 'expired' | 'revoked' | 'tampered' | 'none'

export interface CertInfo {
  table: string
  certification_id?: string
  status: CertStatus
  certifier?: string
  reference?: string
  certified_at?: string
  valid_until?: string | null
  detail?: string
  revoked_reason?: string
}

export interface CertResponse {
  disclaimer?: string
  tables: CertInfo[]
}

const KNOWN: CertStatus[] = ['certified', 'stale', 'expired', 'revoked', 'tampered', 'none']

/** Réponse serveur → table par nom. Statut inconnu ou forme inattendue = pas de pastille (jamais un « certifié » par défaut). */
export function indexByTable(resp: unknown): Record<string, CertInfo> {
  const out: Record<string, CertInfo> = {}
  const tables = (resp as CertResponse | null)?.tables
  if (!Array.isArray(tables)) return out
  for (const c of tables) {
    if (c && typeof c.table === 'string' && KNOWN.includes(c.status)) out[c.table] = c
  }
  return out
}

export type Tone = 'ok' | 'warn' | 'bad'

export interface CertLabels {
  certCertified: string; certStale: string; certExpired: string; certRevoked: string; certTampered: string
  certBy: string; certRef: string; certOn: string; certNotVerified: string; certStaleHint: string
}

export interface Badge { tone: Tone; icon: string; label: string; title: string }

const day = (iso?: string): string => (iso ? iso.slice(0, 10) : '')

/** null = pas de pastille (table non certifiée). */
export function badgeFor(c: CertInfo | undefined, t: CertLabels): Badge | null {
  if (!c || c.status === 'none') return null
  const who = c.certifier ? `${t.certBy} ${c.certifier}` : ''
  const lines = [
    who,
    c.reference ? `${t.certRef} : ${c.reference}` : '',
    c.certified_at ? `${t.certOn} ${day(c.certified_at)}` : '',
    c.status === 'stale' ? t.certStaleHint : '',
    c.status === 'revoked' && c.revoked_reason ? c.revoked_reason : '',
    t.certNotVerified,
  ].filter(Boolean)
  const title = lines.join('\n')
  switch (c.status) {
    case 'certified': return { tone: 'ok', icon: '✔', label: who ? `${t.certCertified} — ${c.certifier}` : t.certCertified, title }
    case 'stale': return { tone: 'warn', icon: '⚠', label: t.certStale, title }
    case 'expired': return { tone: 'warn', icon: '⚠', label: t.certExpired, title }
    case 'revoked': return { tone: 'bad', icon: '✖', label: t.certRevoked, title }
    case 'tampered': return { tone: 'bad', icon: '✖', label: t.certTampered, title }
  }
  return null
}

export async function fetchCertifications(): Promise<Record<string, CertInfo>> {
  if (!isApiConfigured()) return {}
  return indexByTable(await apiJson<CertResponse>('/certification'))
}

// ── Administration (admin) : enregistrer / révoquer une validation ──────────

export interface CertifyInput { table: string; certifier: string; reference: string; validUntil: string }

/** « 2027-03-31 » → fin de journée UTC ; vide → null ; format inattendu → undefined (à refuser). */
export function toValidUntil(day: string): string | null | undefined {
  const d = day.trim()
  if (!d) return null
  return /^\d{4}-\d{2}-\d{2}$/.test(d) && !Number.isNaN(Date.parse(d)) ? `${d}T23:59:59+00:00` : undefined
}

/** Corps de la requête, ou null si un champ obligatoire manque ou si la date est invalide. */
export function buildCertifyBody(i: CertifyInput): { table: string; certifier: string; reference: string; valid_until: string | null } | null {
  const certifier = i.certifier.trim()
  const reference = i.reference.trim()
  const until = toValidUntil(i.validUntil)
  if (!i.table || !certifier || !reference || until === undefined) return null
  return { table: i.table, certifier, reference, valid_until: until }
}

const jsonInit = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export async function certifyTable(i: CertifyInput): Promise<void> {
  const body = buildCertifyBody(i)
  if (!body) throw new Error('invalid')
  await apiJson('/certification', jsonInit(body))
}

export async function revokeCertification(id: string, reason: string): Promise<void> {
  const r = reason.trim()
  if (!r) throw new Error('invalid')
  await apiJson(`/certification/${encodeURIComponent(id)}/revoke`, jsonInit({ reason: r }))
}
