import { useCallback, useEffect, useState } from 'react'
import type { Dict } from '../lib/i18n'
import { ApiError } from '../lib/api'
import {
  FREQUENCIES, createSubscription, daysOf, deleteSubscription, describeSchedule, fetchMailStatus, isoDay, listSubscriptions,
  sendSubscriptionNow, subIssues, type MailStatus, type SubInput, type Subscription,
} from '../lib/subscriptions'

// P-067 — Gestion des abonnements courriel d'un tableau de bord (éditeur ou admin). Le serveur applique droits et audit.

type T = Dict['dashboard']

function errorText(e: unknown, t: T): string {
  if (e instanceof ApiError && (e.status === 409 || e.status === 422 || e.status === 502 || e.status === 404) && e.detail) return e.detail
  return t.subErrGeneric
}

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

export default function SubscriptionsPanel({ dashId, t }: { dashId: string; t: T }) {
  const [subs, setSubs] = useState<Subscription[] | null>(null)
  const [mail, setMail] = useState<MailStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [pending, setPending] = useState<{ id: string; action: 'send' | 'delete' } | null>(null)

  const [form, setForm] = useState<SubInput>({ email: '', frequency: 'weekly', hourUtc: 7, weekday: 0, dayOfMonth: 1, consent: false })
  const set = <K extends keyof SubInput>(k: K, v: SubInput[K]) => setForm((f) => ({ ...f, [k]: v }))

  const load = useCallback(async () => {
    try {
      const [list, status] = await Promise.all([listSubscriptions(dashId), fetchMailStatus().catch(() => null)])
      setSubs(list)
      setMail(status)
      setError(null)
    } catch (e) {
      setError(errorText(e, t))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dashId])

  useEffect(() => { setSubs(null); setPending(null); void load() }, [load])

  const run = async (fn: () => Promise<string>, after?: () => void) => {
    setBusy(true); setError(null); setNotice(null)
    try {
      setNotice(await fn())
      after?.()
      await load()
    } catch (e) {
      setError(errorText(e, t))
    } finally {
      setBusy(false)
      setPending(null)
    }
  }

  const issues = subIssues(form)
  const blocking = issues.filter((i) => i !== 'consent')
  const field = { display: 'flex', flexDirection: 'column', gap: 3, fontSize: 12 } as const
  const small = { fontSize: 12, padding: '4px 10px' } as const
  const bad = { color: 'oklch(78% 0.15 25)', fontSize: 11 } as const

  return (
    <section className="card-solid" aria-labelledby={`subs-title-${dashId}`} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div id={`subs-title-${dashId}`} style={{ fontWeight: 600 }}>{t.subTitle}</div>
      <p className="muted" style={{ margin: 0 }}>{t.subIntro}</p>
      {mail && (
        <div role="status" className={`badge ${mail.smtp_configured ? 'badge-ok' : 'badge-demo'}`} style={{ alignSelf: 'flex-start', fontSize: 12 }}>
          {mail.smtp_configured ? t.subModeSmtp : t.subModeOutbox}
        </div>
      )}
      {notice && <div role="status" className="badge badge-ok" style={{ alignSelf: 'flex-start', fontSize: 12 }}>{notice}</div>}
      {error && <div role="alert" className="badge badge-off" style={{ alignSelf: 'flex-start', fontSize: 12 }}>{error}</div>}

      {subs !== null && subs.length === 0 && <div className="muted">{t.subNone}</div>}
      {subs !== null && subs.length > 0 && (
        <div className="table-wrap" style={{ maxHeight: 'none' }}>
          <table className="data">
            <tbody>
              {subs.map((s) => (
                <tr key={s.id}>
                  <td dir="ltr" style={{ textAlign: 'start' }}>{s.email}</td>
                  <td>
                    <div>{describeSchedule(s, t)}</div>
                    <div className="muted" style={{ fontSize: 11 }}>
                      {t.subLastSent} : {s.last_sent_at ? isoDay(s.last_sent_at) : t.subNever}
                    </div>
                    {s.last_error && <div role="alert" style={bad}>{t.subErrorLabel} : {s.last_error}</div>}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {pending?.id === s.id && pending.action === 'send' ? (
                        <>
                          <button className="btn" style={small} disabled={busy}
                            onClick={() => void run(async () => (await sendSubscriptionNow(s.id)).channel === 'smtp' ? t.subSentSmtp : t.subSentOutbox)}>{t.subSendConfirm}</button>
                          <button className="btn-ghost" style={small} onClick={() => setPending(null)}>{t.subCancel}</button>
                        </>
                      ) : pending?.id === s.id && pending.action === 'delete' ? (
                        <>
                          <button className="btn" style={small} disabled={busy}
                            onClick={() => void run(async () => { await deleteSubscription(s.id); return t.subDeleted })}>{t.subDeleteConfirm}</button>
                          <button className="btn-ghost" style={small} onClick={() => setPending(null)}>{t.subCancel}</button>
                        </>
                      ) : (
                        <>
                          <button className="btn-ghost" style={small} disabled={busy} onClick={() => setPending({ id: s.id, action: 'send' })}>{t.subSendNow}</button>
                          <button className="btn-ghost" style={small} disabled={busy} onClick={() => setPending({ id: s.id, action: 'delete' })}>{t.subDelete}</button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <form noValidate style={{ display: 'flex', flexDirection: 'column', gap: 10 }}
        onSubmit={(e) => { e.preventDefault(); void run(async () => { await createSubscription(dashId, form); return t.subAdded }, () => setForm((f) => ({ ...f, email: '', consent: false }))) }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 10 }}>
          <label style={field}>{t.subEmail}
            <input className="input" type="email" dir="ltr" value={form.email} maxLength={254} autoComplete="off" onChange={(e) => set('email', e.target.value)}
              aria-invalid={form.email !== '' && issues.includes('email')} />
            {form.email !== '' && issues.includes('email') && <span role="alert" style={bad}>{t.subErrEmail}</span>}
          </label>
          <label style={field}>{t.subFrequency}
            <select className="input" value={form.frequency} onChange={(e) => set('frequency', e.target.value)}>
              {FREQUENCIES.map((f) => <option key={f} value={f}>{f === 'daily' ? t.subDaily : f === 'weekly' ? t.subEveryWeek : t.subEveryMonth}</option>)}
            </select>
          </label>
          {form.frequency === 'weekly' && (
            <label style={field}>{t.subWeekday}
              <select className="input" value={form.weekday} onChange={(e) => set('weekday', Number(e.target.value))}>
                {daysOf(t).map((d, i) => <option key={d} value={i}>{cap(d)}</option>)}
              </select>
            </label>
          )}
          {form.frequency === 'monthly' && (
            <label style={field}>{t.subDayOfMonth}
              <input className="input" type="number" min={1} max={28} value={form.dayOfMonth} onChange={(e) => set('dayOfMonth', Number(e.target.value))} dir="ltr" />
              {issues.includes('day') && <span role="alert" style={bad}>{t.subErrDay}</span>}
            </label>
          )}
          <label style={field}>{t.subHour}
            <input className="input" type="number" min={0} max={23} value={form.hourUtc} onChange={(e) => set('hourUtc', Number(e.target.value))} dir="ltr" />
            {issues.includes('hour') && <span role="alert" style={bad}>{t.subErrHour}</span>}
          </label>
        </div>
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13 }}>
          <input type="checkbox" checked={form.consent} onChange={(e) => set('consent', e.target.checked)} />
          {t.subConsent}
        </label>
        <span className="muted" style={{ fontSize: 11 }}>{t.subNote}</span>
        <div><button className="btn" type="submit" disabled={busy || blocking.length > 0 || !form.consent || form.email.trim() === ''}>{t.subAdd}</button></div>
      </form>
    </section>
  )
}
