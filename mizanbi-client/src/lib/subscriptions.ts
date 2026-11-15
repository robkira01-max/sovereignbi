// Abonnements courriel aux bulletins (P-067). Validation alignée sur le serveur ; le serveur reste l'autorité.
import { apiFetch, apiJson } from './api'

export type Frequency = 'daily' | 'weekly' | 'monthly'
export const FREQUENCIES: Frequency[] = ['daily', 'weekly', 'monthly']

export interface Subscription {
  id: string
  dashboard_id: string
  email: string
  frequency: Frequency
  hour_utc: number
  weekday: number
  day_of_month: number
  created_at: string
  last_sent_at: string | null
  last_error: string | null
  active: boolean
}

export interface MailStatus { smtp_configured: boolean; mode: string }

export interface SubInput {
  email: string
  frequency: string
  hourUtc: number
  weekday: number
  dayOfMonth: number
  consent: boolean
}

export type SubIssue = 'email' | 'frequency' | 'hour' | 'weekday' | 'day' | 'consent'

// Même gabarit que le serveur (app/subscriptions/store.py)
const EMAIL_RE = /^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,190}\.[A-Za-z]{2,24}$/

export function subIssues(i: SubInput): SubIssue[] {
  const out: SubIssue[] = []
  const email = i.email.trim()
  if (!EMAIL_RE.test(email) || email.includes('..')) out.push('email')
  if (!(FREQUENCIES as string[]).includes(i.frequency)) out.push('frequency')
  if (!Number.isInteger(i.hourUtc) || i.hourUtc < 0 || i.hourUtc > 23) out.push('hour')
  if (i.frequency === 'weekly' && (!Number.isInteger(i.weekday) || i.weekday < 0 || i.weekday > 6)) out.push('weekday')
  if (i.frequency === 'monthly' && (!Number.isInteger(i.dayOfMonth) || i.dayOfMonth < 1 || i.dayOfMonth > 28)) out.push('day')
  if (!i.consent) out.push('consent')
  return out
}

/** Corps de la requête, ou null si invalide. Le jour non pertinent pour la fréquence prend la valeur neutre du serveur. */
export function buildSubBody(dashboardId: string, i: SubInput) {
  if (subIssues(i).length) return null
  return {
    dashboard_id: dashboardId,
    email: i.email.trim().toLowerCase(),
    frequency: i.frequency,
    hour_utc: i.hourUtc,
    weekday: i.frequency === 'weekly' ? i.weekday : 0,
    day_of_month: i.frequency === 'monthly' ? i.dayOfMonth : 1,
  }
}

export interface ScheduleLabels {
  subDaily: string; subWeekly: string; subMonthly: string
  subDays: string              // sept jours séparés par des virgules, du lundi au dimanche
  subAt: string                // « à » / « at »
}

const pad = (n: number) => String(n).padStart(2, '0')

/** Ex. « Chaque lundi à 07:00 UTC ». */
export const daysOf = (t: Pick<ScheduleLabels, 'subDays'>): string[] => t.subDays.split(',')

export function describeSchedule(s: Pick<Subscription, 'frequency' | 'hour_utc' | 'weekday' | 'day_of_month'>, t: ScheduleLabels): string {
  const time = `${t.subAt} ${pad(s.hour_utc)}:00 UTC`
  if (s.frequency === 'daily') return `${t.subDaily} ${time}`
  if (s.frequency === 'weekly') return `${t.subWeekly.replace('{day}', daysOf(t)[s.weekday] ?? '?')} ${time}`
  return `${t.subMonthly.replace('{day}', String(s.day_of_month))} ${time}`
}

export const isoDay = (iso: string | null): string => (iso ? iso.slice(0, 16).replace('T', ' ') : '')

// ── API ─────────────────────────────────────────────────────────────────────

const json = (method: string, body: unknown): RequestInit => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const fetchMailStatus = () => apiJson<MailStatus>('/subscriptions/status')

export async function listSubscriptions(dashboardId: string): Promise<Subscription[]> {
  const r = await apiJson<{ subscriptions?: Subscription[] }>(`/subscriptions?dashboard_id=${encodeURIComponent(dashboardId)}`)
  return Array.isArray(r.subscriptions) ? r.subscriptions : []
}

export async function createSubscription(dashboardId: string, i: SubInput): Promise<void> {
  const body = buildSubBody(dashboardId, i)
  if (!body) throw new Error('invalid')
  await apiJson('/subscriptions', json('POST', body))
}

export async function deleteSubscription(id: string): Promise<void> {
  await apiFetch(`/subscriptions/${encodeURIComponent(id)}`, { method: 'DELETE' })      // 204 sans corps
}

export const sendSubscriptionNow = (id: string) =>
  apiJson<{ sent: boolean; channel: 'smtp' | 'outbox' }>(`/subscriptions/${encodeURIComponent(id)}/send-now`, { method: 'POST' })
