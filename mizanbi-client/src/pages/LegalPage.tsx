import type { Dict, Lang } from '../lib/i18n'
import type { LegalKind } from '../lib/legalContent'
import LegalDocument from '../components/LegalDocument'

interface Props {
  kind: LegalKind
  t: Dict
  lang: Lang
  onBack: () => void
  /** Ouvre le choix cookies (page cookies uniquement). */
  onManageCookies?: () => void
  /** Choix actuel : true = accepté, false = refusé, null = aucun. */
  cookieChoice?: boolean | null
}

export default function LegalPage({ kind, t, lang, onBack, onManageCookies, cookieChoice = null }: Props) {
  const choiceLabel = cookieChoice === null ? t.cookies.choiceNone : cookieChoice ? t.cookies.choiceAccepted : t.cookies.choiceDeclined
  return (
    <div style={{ maxWidth: 740, margin: '0 auto', padding: '32px 16px 64px' }}>
      <button className="btn-ghost" onClick={onBack} style={{ marginBottom: 24 }}>← {t.back}</button>
      <LegalDocument kind={kind} lang={lang} t={t} />
      {kind === 'cookies' && onManageCookies && (
        <div style={{ marginTop: 8, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="btn" onClick={onManageCookies}>{t.cookies.manage}</button>
          <span className="muted" style={{ fontSize: 13 }}>{t.cookies.choiceTitle} : <strong data-testid="cookie-choice">{choiceLabel}</strong></span>
        </div>
      )}
    </div>
  )
}
