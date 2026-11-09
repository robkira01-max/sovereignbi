import type { Dict } from '../lib/i18n'

const COOKIE_KEY = 'mizan_cookie_consent'

export function useCookieConsent(): [boolean | null, (v: boolean) => void] {
  const stored = localStorage.getItem(COOKIE_KEY)
  const value = stored === null ? null : stored === 'true'
  const set = (accepted: boolean) => {
    localStorage.setItem(COOKIE_KEY, String(accepted))
  }
  return [value, set]
}

interface Props {
  t: Dict
  onAccept: () => void
  onDecline: () => void
}

export default function CookieBanner({ t, onAccept, onDecline }: Props) {
  return (
    <div
      role="dialog"
      aria-label={t.cookies.message}
      style={{
        position: 'fixed',
        bottom: 0,
        insetInlineStart: 0,
        insetInlineEnd: 0,
        zIndex: 9999,
        background: 'var(--surface-solid, #12121f)',
        borderTop: '1px solid var(--border, #2a2a4a)',
        padding: '14px 24px',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        flexWrap: 'wrap',
        fontSize: 13,
      }}
    >
      <span style={{ flex: 1, minWidth: 220 }}>
        {t.cookies.message}{' '}
        <button
          onClick={onDecline}
          style={{ background: 'none', border: 'none', textDecoration: 'underline', cursor: 'pointer', color: 'var(--muted)', fontSize: 13, padding: 0 }}
        >
          {t.cookies.policy}
        </button>
      </span>
      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn-ghost" style={{ padding: '5px 14px' }} onClick={onDecline}>
          {t.cookies.decline}
        </button>
        <button className="btn" style={{ padding: '5px 14px' }} onClick={onAccept}>
          {t.cookies.accept}
        </button>
      </div>
    </div>
  )
}
