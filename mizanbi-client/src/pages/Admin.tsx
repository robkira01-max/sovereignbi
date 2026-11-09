import { Fragment, useCallback, useEffect, useState } from 'react'
import type { Dict, Lang } from '../lib/i18n'
import { isApiConfigured } from '../lib/api'
import {
  AccountsError, MIN_PASSWORD_CHARS, ROLES, validateEmail, validatePassword,
  type Account, type AccountErrorCode, type AccountsService, type Me, type Role,
} from '../lib/accounts'
import { fmt } from '../lib/geoai'

// P-038 — Écran administrateur : gestion des comptes (rôles, activation, mots de passe).
// Mode connecté : /auth/users* (le serveur applique les règles et l'audit).
// Mode démo : comptes fictifs en mémoire (lib/accounts.ts).

type Texts = Dict['admin']

const ERR_KEY: Record<AccountErrorCode, keyof Texts> = {
  exists: 'errExists', lastAdmin: 'errLastAdmin', notFound: 'errNotFound', invalidEmail: 'errInvalidEmail',
  passwordShort: 'errPasswordShort', passwordLong: 'errPasswordLong', forbidden: 'errForbidden',
  unauthorized: 'errUnauthorized', wrongPassword: 'errUnknown', busy: 'errBusy', network: 'errNetwork', unknown: 'errUnknown',
}

const ROLE_KEY: Record<Role, { label: keyof Texts; help: keyof Texts }> = {
  viewer: { label: 'roleViewer', help: 'roleViewerHelp' },
  editor: { label: 'roleEditor', help: 'roleEditorHelp' },
  admin: { label: 'roleAdmin', help: 'roleAdminHelp' },
}

function PasswordField({ value, onChange, t, id, autoFocus }: {
  value: string; onChange: (v: string) => void; t: Texts; id: string; autoFocus?: boolean
}) {
  const [shown, setShown] = useState(false)
  return (
    <div style={{ display: 'flex', gap: 6 }}>
      <input
        id={id} className="input" type={shown ? 'text' : 'password'} value={value} autoFocus={autoFocus}
        onChange={(e) => onChange(e.target.value)} autoComplete="new-password" dir="ltr" style={{ flex: 1 }}
      />
      <button type="button" className="btn-ghost" onClick={() => setShown((s) => !s)} style={{ fontSize: 12, padding: '4px 10px' }}>
        {shown ? t.hidePw : t.showPw}
      </button>
    </div>
  )
}

export default function AdminPage({ t, lang, service, me, onSelfChanged }: {
  t: Dict; lang: Lang; service: AccountsService; me: Me | null; onSelfChanged: () => void
}) {
  const a = t.admin
  const demo = !isApiConfigured()
  const [accounts, setAccounts] = useState<Account[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [forbidden, setForbidden] = useState(false)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<Role>('viewer')

  const [resetId, setResetId] = useState<number | null>(null)
  const [resetPw, setResetPw] = useState('')
  const [confirmId, setConfirmId] = useState<number | null>(null)

  const roleLabel = (r: Role) => a[ROLE_KEY[r].label]
  const errText = (e: unknown): string => {
    const code: AccountErrorCode = e instanceof AccountsError ? e.code : 'unknown'
    return fmt(a[ERR_KEY[code]], { min: MIN_PASSWORD_CHARS })
  }

  const load = useCallback(async () => {
    try {
      setAccounts(await service.list())
      setForbidden(false)
    } catch (e) {
      if (e instanceof AccountsError && e.code === 'forbidden') setForbidden(true)
      else setError(errText(e))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [service, lang])

  // Messages are stored already formatted: drop them when the language changes.
  useEffect(() => { setNotice(null); setError(null) }, [lang])

  useEffect(() => {
    if (me && me.role !== 'admin') { setForbidden(true); return }
    if (me) void load()
  }, [me, load])

  /** Runs one mutation: single in-flight action, uniform error/notice handling. */
  const run = async (action: () => Promise<string>) => {
    if (busy) return
    setBusy(true); setError(null); setNotice(null)
    try { setNotice(await action()) } catch (e) { setError(errText(e)) } finally { setBusy(false) }
  }

  const replace = (u: Account) => setAccounts((list) => (list ?? []).map((x) => (x.id === u.id ? u : x)))

  const create = (e: React.FormEvent) => {
    e.preventDefault()
    void run(async () => {
      const clean = validateEmail(email)
      validatePassword(password)
      const u = await service.create(clean, password, role)
      setAccounts((list) => [...(list ?? []), u])
      setEmail(''); setPassword(''); setRole('viewer')
      return fmt(a.created, { email: u.email })
    })
  }

  const changeRole = (u: Account, next: Role) =>
    run(async () => {
      replace(await service.update(u.id, { role: next }))
      if (me && u.id === me.id) onSelfChanged()
      return fmt(a.roleChanged, { email: u.email, role: roleLabel(next) })
    })

  const setActive = (u: Account, active: boolean) =>
    run(async () => {
      replace(await service.update(u.id, { is_active: active }))
      setConfirmId(null)
      if (me && u.id === me.id) onSelfChanged()
      return fmt(active ? a.reactivated : a.deactivated, { email: u.email })
    })

  const saveReset = (u: Account) =>
    run(async () => {
      validatePassword(resetPw)
      await service.resetPassword(u.id, resetPw)
      setResetId(null); setResetPw('')
      return fmt(a.passwordReset, { email: u.email })
    })

  if (forbidden) {
    return <div className="card-solid" role="alert" style={{ maxWidth: 560 }}>{a.restricted}</div>
  }

  // ISO date (YYYY-MM-DD): unambiguous in every language and free of bidi marks.
  const dateOf = (s: string | null) => (s ? s.slice(0, 10) : '—')

  return (
    <div style={{ maxWidth: 980, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, letterSpacing: '-.02em' }}>{a.title}</h1>
        <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 13 }}>
          {a.subtitle} · {demo ? <span style={{ color: 'oklch(72% 0.18 55)' }}>{a.demoNote}</span> : a.auditNote}
        </p>
      </div>

      <div aria-live="polite" style={{ display: 'contents' }}>
        {notice && <div role="status" className="badge badge-ok" style={{ alignSelf: 'flex-start', fontSize: 13 }}>{notice}</div>}
        {error && <div role="alert" className="badge badge-off" style={{ alignSelf: 'flex-start', fontSize: 13 }}>{error}</div>}
      </div>

      <form onSubmit={create} noValidate className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ fontWeight: 600 }}>{a.createTitle}</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13 }}>
            {a.email}
            <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} dir="ltr" autoComplete="off" />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13 }}>
            {a.password}
            <PasswordField id="admin-new-pw" value={password} onChange={setPassword} t={a} />
            <span className="muted" style={{ fontSize: 11 }}>{fmt(a.passwordHint, { min: MIN_PASSWORD_CHARS })}</span>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 13 }}>
            {a.role}
            <select className="input" value={role} onChange={(e) => setRole(e.target.value as Role)}>
              {ROLES.map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
            </select>
            <span className="muted" style={{ fontSize: 11 }}>{a[ROLE_KEY[role].help]}</span>
          </label>
        </div>
        <div>
          <button className="btn" type="submit" disabled={busy || !email.trim() || !password}>{a.create}</button>
        </div>
      </form>

      <div className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ fontSize: 13, color: 'var(--muted)' }}>
          {accounts === null ? a.loading : fmt(a.count, { n: accounts.length })}
        </div>
        {accounts !== null && accounts.length === 0 && <div>{a.empty}</div>}
        {accounts !== null && accounts.length > 0 && (
          <div className="table-wrap" style={{ maxHeight: 'none' }}>
            <table className="data">
              <thead>
                <tr>
                  <th>{a.colEmail}</th><th>{a.colRole}</th><th>{a.colStatus}</th><th>{a.colCreated}</th><th>{a.colActions}</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((u) => (
                  <Fragment key={u.id}>
                    <tr>
                      <td dir="ltr" style={{ textAlign: 'start' }}>
                        {u.email}{me && u.id === me.id && <span className="muted"> {a.you}</span>}
                      </td>
                      <td>
                        <select
                          className="input" aria-label={`${a.colRole} — ${u.email}`} value={u.role} disabled={busy}
                          onChange={(e) => void changeRole(u, e.target.value as Role)} style={{ padding: '4px 8px' }}
                        >
                          {ROLES.map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
                        </select>
                      </td>
                      <td><span className={`badge ${u.is_active ? 'badge-ok' : 'badge-off'}`}>{u.is_active ? a.statusActive : a.statusInactive}</span></td>
                      <td dir="ltr" style={{ textAlign: 'start' }}>{dateOf(u.created_at)}</td>
                      <td>
                        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                          <button className="btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }} disabled={busy}
                            onClick={() => { setResetId(resetId === u.id ? null : u.id); setResetPw(''); setConfirmId(null) }}>
                            {a.resetPassword}
                          </button>
                          {!u.is_active ? (
                            <button className="btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }} disabled={busy} onClick={() => void setActive(u, true)}>{a.reactivate}</button>
                          ) : confirmId === u.id ? (
                            <>
                              <button className="btn" style={{ fontSize: 12, padding: '4px 10px' }} disabled={busy} onClick={() => void setActive(u, false)}>{a.confirm}</button>
                              <button className="btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => setConfirmId(null)}>{a.cancel}</button>
                            </>
                          ) : (
                            <button className="btn-ghost" style={{ fontSize: 12, padding: '4px 10px' }} disabled={busy}
                              onClick={() => { setConfirmId(u.id); setResetId(null) }}>{a.deactivate}</button>
                          )}
                        </div>
                      </td>
                    </tr>
                    {resetId === u.id && (
                      <tr>
                        <td colSpan={5}>
                          <form noValidate onSubmit={(e) => { e.preventDefault(); void saveReset(u) }}
                            style={{ display: 'flex', flexDirection: 'column', gap: 6, padding: '4px 0' }}>
                            <label htmlFor={`reset-${u.id}`} style={{ fontSize: 13, fontWeight: 600 }}>{fmt(a.resetTitle, { email: u.email })}</label>
                            <PasswordField id={`reset-${u.id}`} value={resetPw} onChange={setResetPw} t={a} autoFocus />
                            <span className="muted" style={{ fontSize: 11 }}>{fmt(a.passwordHint, { min: MIN_PASSWORD_CHARS })} {a.resetNote}</span>
                            <div style={{ display: 'flex', gap: 6 }}>
                              <button className="btn" type="submit" disabled={busy || !resetPw} style={{ fontSize: 12, padding: '4px 12px' }}>{a.save}</button>
                              <button className="btn-ghost" type="button" onClick={() => { setResetId(null); setResetPw('') }} style={{ fontSize: 12, padding: '4px 12px' }}>{a.cancel}</button>
                            </div>
                          </form>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
