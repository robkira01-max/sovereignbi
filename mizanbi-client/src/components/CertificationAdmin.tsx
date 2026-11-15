import { useCallback, useEffect, useState } from 'react'
import type { Dict } from '../lib/i18n'
import { ApiError, isApiConfigured } from '../lib/api'
import { certifyTable, fetchCertifications, revokeCertification, buildCertifyBody, type CertInfo } from '../lib/certification'
import CertificationBadge from './CertificationBadge'

// P-069 — Administration des jeux de données certifiés (admin). Le serveur applique les droits et l'audit.

function errorText(e: unknown, a: Dict['admin']): string {
  if (e instanceof ApiError) {
    if (e.status === 401) return a.errUnauthorized
    if (e.status === 403) return a.errForbidden
    if ((e.status === 422 || e.status === 404) && e.detail) return e.detail      // messages du serveur (déjà en français)
    return a.errUnknown
  }
  return a.errNetwork
}

export default function CertificationAdmin({ t }: { t: Dict }) {
  const a = t.admin
  const [rows, setRows] = useState<CertInfo[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [table, setTable] = useState('')
  const [certifier, setCertifier] = useState('')
  const [reference, setReference] = useState('')
  const [until, setUntil] = useState('')
  const [confirmed, setConfirmed] = useState(false)

  const [revokeId, setRevokeId] = useState<string | null>(null)
  const [reason, setReason] = useState('')

  const load = useCallback(async () => {
    try {
      const m = await fetchCertifications()
      setRows(Object.values(m).sort((x, y) => x.table.localeCompare(y.table)))
      setError(null)
    } catch (e) {
      setError(errorText(e, a))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => { if (isApiConfigured()) void load() }, [load])

  const run = async (fn: () => Promise<void>, done: string, reset: () => void) => {
    setBusy(true); setError(null); setNotice(null)
    try {
      await fn()
      reset()
      setNotice(done)
      await load()
    } catch (e) {
      setError(errorText(e, a))
    } finally {
      setBusy(false)
    }
  }

  const canSubmit = confirmed && !busy && buildCertifyBody({ table, certifier, reference, validUntil: until }) !== null
  const field = { display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13 } as const

  return (
    <section className="card-solid" aria-labelledby="cert-admin-title" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div id="cert-admin-title" style={{ fontWeight: 600 }}>{a.certSection}</div>
      <p className="muted" style={{ margin: 0 }}>{a.certIntro}</p>

      {!isApiConfigured() ? (
        <div className="muted" role="status">{a.certDemo}</div>
      ) : (
        <>
          {notice && <div role="status" className="badge badge-ok" style={{ alignSelf: 'flex-start', fontSize: 13 }}>{notice}</div>}
          {error && <div role="alert" className="badge badge-off" style={{ alignSelf: 'flex-start', fontSize: 13 }}>{error}</div>}

          {rows !== null && rows.length === 0 && <div className="muted">{a.certNoTables}</div>}
          {rows !== null && rows.length > 0 && (
            <div className="table-wrap" style={{ maxHeight: 'none' }}>
              <table className="data">
                <thead><tr><th>{a.certTable}</th><th>{a.certColStatus}</th><th>{a.certColAction}</th></tr></thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.table}>
                      <td dir="ltr" style={{ textAlign: 'start' }}>{r.table}</td>
                      <td>{r.status === 'none' ? <span className="muted">{a.certNone}</span> : <CertificationBadge info={r} t={t} />}</td>
                      <td>
                        {r.status !== 'none' && r.status !== 'revoked' && r.certification_id && (
                          revokeId === r.certification_id ? (
                            <form noValidate onSubmit={(e) => { e.preventDefault(); void run(() => revokeCertification(r.certification_id!, reason), a.certRevokedDone, () => { setRevokeId(null); setReason('') }) }}
                              style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                              <input className="input" aria-label={a.certReason} placeholder={a.certReason} value={reason} maxLength={300}
                                onChange={(e) => setReason(e.target.value)} autoFocus style={{ minWidth: 180 }} />
                              <button className="btn" type="submit" disabled={busy || !reason.trim()} style={{ fontSize: 12, padding: '4px 10px' }}>{a.certRevokeConfirm}</button>
                              <button className="btn-ghost" type="button" onClick={() => { setRevokeId(null); setReason('') }} style={{ fontSize: 12, padding: '4px 10px' }}>{a.cancel}</button>
                            </form>
                          ) : (
                            <button className="btn-ghost" disabled={busy} style={{ fontSize: 12, padding: '4px 10px' }}
                              onClick={() => setRevokeId(r.certification_id!)}>{a.certRevoke}</button>
                          )
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <form noValidate style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
            onSubmit={(e) => {
              e.preventDefault()
              void run(() => certifyTable({ table, certifier, reference, validUntil: until }), a.certDone,
                () => { setTable(''); setCertifier(''); setReference(''); setUntil(''); setConfirmed(false) })
            }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
              <label style={field}>{a.certTable}
                <select className="input" value={table} onChange={(e) => setTable(e.target.value)}>
                  <option value="" />
                  {(rows ?? []).map((r) => <option key={r.table} value={r.table}>{r.table}</option>)}
                </select>
              </label>
              <label style={field}>{a.certInstitution}
                <input className="input" value={certifier} maxLength={120} onChange={(e) => setCertifier(e.target.value)} />
              </label>
              <label style={field}>{a.certReference}
                <input className="input" value={reference} maxLength={300} onChange={(e) => setReference(e.target.value)} />
              </label>
              <label style={field}>{a.certUntil}
                <input className="input" type="date" value={until} onChange={(e) => setUntil(e.target.value)} dir="ltr" />
              </label>
            </div>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 13 }}>
              <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
              {a.certConfirmBox}
            </label>
            <div><button className="btn" type="submit" disabled={!canSubmit}>{a.certSubmit}</button></div>
          </form>
        </>
      )}
    </section>
  )
}
