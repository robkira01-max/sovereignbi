// P-039 — Modal « changer mon mot de passe » (utilisateur courant, POST /auth/password).
import { useState } from 'react'
import type { Dict } from '../lib/i18n'
import type { AccountsService } from '../lib/accounts'
import { MIN_PASSWORD_CHARS } from '../lib/accounts'

interface Props {
  t: Dict
  service: AccountsService
  onClose(): void
  /** True when in demo mode — simule la réussite sans appel serveur. */
  isDemo?: boolean
}

type Status = 'idle' | 'busy' | 'success'

export default function ChangePasswordModal({ t, service, onClose, isDemo }: Props) {
  const tc = t.changePwd
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNext, setShowNext] = useState(false)
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState<string | null>(null)

  const errMsg = (code: string): string => {
    switch (code) {
      case 'wrongPassword': return tc.errWrong
      case 'passwordShort': return tc.errShort.replace('{min}', String(MIN_PASSWORD_CHARS))
      case 'passwordLong': return tc.errLong
      case 'busy': return tc.errBusy
      default: return tc.errUnknown
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (next !== confirm) { setError(tc.mismatch); return }
    setStatus('busy')
    try {
      await service.changePassword(current, next)
      setStatus('success')
    } catch (err: unknown) {
      setStatus('idle')
      const code = (err instanceof Error && 'code' in err) ? (err as { code: string }).code : 'unknown'
      setError(errMsg(code))
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={tc.title}
      style={{
        position: 'fixed', inset: 0, zIndex: 9000,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgba(0,0,0,0.45)', backdropFilter: 'blur(2px)',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        style={{
          background: 'var(--surface, #fff)', borderRadius: 12, padding: '28px 32px',
          width: 'min(420px, calc(100vw - 32px))', boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
        }}
      >
        <h2 style={{ margin: '0 0 20px', fontSize: 18, fontWeight: 700 }}>{tc.title}</h2>

        {status === 'success' ? (
          <>
            <p style={{ color: 'var(--success, #2a7a2a)', marginBottom: 20 }}>{tc.success}</p>
            <button className="btn-primary" onClick={onClose} style={{ width: '100%' }}>{tc.cancel}</button>
          </>
        ) : (
          <form onSubmit={handleSubmit} noValidate>
            {isDemo && (
              <p style={{ fontSize: 12, color: 'var(--muted, #888)', marginBottom: 12 }}>
                Mode démo — aucun appel serveur.
              </p>
            )}

            <label style={{ display: 'block', marginBottom: 14 }}>
              <span style={{ display: 'block', marginBottom: 4, fontSize: 13, fontWeight: 600 }}>{tc.current}</span>
              <div style={{ position: 'relative' }}>
                <input
                  type={showCurrent ? 'text' : 'password'}
                  value={current}
                  onChange={(e) => setCurrent(e.target.value)}
                  required
                  autoComplete="current-password"
                  style={{ width: '100%', paddingInlineEnd: 60, boxSizing: 'border-box' }}
                />
                <button
                  type="button"
                  onClick={() => setShowCurrent((v) => !v)}
                  style={{ position: 'absolute', insetInlineEnd: 8, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: 'var(--muted, #666)' }}
                >
                  {showCurrent ? t.admin.hidePw : t.admin.showPw}
                </button>
              </div>
            </label>

            <label style={{ display: 'block', marginBottom: 14 }}>
              <span style={{ display: 'block', marginBottom: 4, fontSize: 13, fontWeight: 600 }}>{tc.new}</span>
              <div style={{ position: 'relative' }}>
                <input
                  type={showNext ? 'text' : 'password'}
                  value={next}
                  onChange={(e) => setNext(e.target.value)}
                  required
                  autoComplete="new-password"
                  style={{ width: '100%', paddingInlineEnd: 60, boxSizing: 'border-box' }}
                />
                <button
                  type="button"
                  onClick={() => setShowNext((v) => !v)}
                  style={{ position: 'absolute', insetInlineEnd: 8, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: 'var(--muted, #666)' }}
                >
                  {showNext ? t.admin.hidePw : t.admin.showPw}
                </button>
              </div>
            </label>

            <label style={{ display: 'block', marginBottom: 20 }}>
              <span style={{ display: 'block', marginBottom: 4, fontSize: 13, fontWeight: 600 }}>{tc.confirm}</span>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                autoComplete="new-password"
                style={{ width: '100%', boxSizing: 'border-box' }}
              />
            </label>

            {error && (
              <p role="alert" style={{ color: 'var(--error, #c0392b)', fontSize: 13, marginBottom: 14 }}>{error}</p>
            )}

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button type="button" className="btn-ghost" onClick={onClose} disabled={status === 'busy'}>{tc.cancel}</button>
              <button type="submit" className="btn-primary" disabled={status === 'busy' || !current || !next || !confirm}>
                {status === 'busy' ? '…' : tc.save}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
