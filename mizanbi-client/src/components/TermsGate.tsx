import { useState } from 'react'
import type { Dict, Lang } from '../lib/i18n'
import LegalDocument from './LegalDocument'

interface Props {
  t: Dict
  lang: Lang
  onAccept: () => Promise<void>
  onRefuse: () => void
}

/** Fenêtre bloquante : CGU + confidentialité à accepter à la première connexion et à chaque nouvelle version. */
export default function TermsGate({ t, lang, onAccept, onRefuse }: Props) {
  const [tab, setTab] = useState<'terms' | 'privacy'>('terms')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)

  const accept = async () => {
    setBusy(true)
    setError(false)
    try {
      await onAccept()
    } catch {
      setError(true)
      setBusy(false)
    }
  }

  return (
    <div role="dialog" aria-modal="true" aria-label={t.termsGate.title}
      style={{ position: 'fixed', inset: 0, zIndex: 10000, background: 'rgba(7,7,17,.85)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div style={{ background: 'var(--surface-solid, #12121f)', border: '1px solid var(--border, #2a2a4a)', borderRadius: 16, width: '100%', maxWidth: 760, maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '20px 24px 12px' }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>{t.termsGate.title}</h2>
          <p className="muted" style={{ fontSize: 13, margin: '6px 0 12px' }}>{t.termsGate.intro}</p>
          <div className="view-switch" role="tablist">
            <button role="tab" aria-selected={tab === 'terms'} className={tab === 'terms' ? 'active' : ''} onClick={() => setTab('terms')}>{t.termsGate.tabTerms}</button>
            <button role="tab" aria-selected={tab === 'privacy'} className={tab === 'privacy' ? 'active' : ''} onClick={() => setTab('privacy')}>{t.termsGate.tabPrivacy}</button>
          </div>
        </div>
        <div style={{ padding: '0 24px', overflowY: 'auto', flex: 1 }}>
          <LegalDocument kind={tab} lang={lang} t={t} compact />
        </div>
        <div style={{ padding: '12px 24px 20px', display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', borderTop: '1px solid var(--border, #2a2a4a)' }}>
          <button className="btn" onClick={accept} disabled={busy}>{busy ? t.termsGate.saving : t.termsGate.accept}</button>
          <button className="btn-ghost" onClick={onRefuse} disabled={busy}>{t.termsGate.refuse}</button>
          {error && <span role="alert" style={{ color: 'oklch(75% 0.17 25)', fontSize: 13 }}>{t.termsGate.error}</span>}
        </div>
      </div>
    </div>
  )
}
