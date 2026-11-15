import { badgeFor, type CertInfo, type CertLabels } from '../lib/certification'

interface Props {
  info: CertInfo | undefined
  t: CertLabels
}

/** Pastille « validé par … ». Texte + icône (jamais la couleur seule). Rien si la table n'est pas certifiée. */
export default function CertificationBadge({ info, t }: Props) {
  const b = badgeFor(info, t)
  if (!b) return null
  return (
    <span className={`cert-badge cert-${b.tone}`} title={b.title} aria-label={b.label} role="note">
      <span aria-hidden="true">{b.icon}</span> {b.label}
    </span>
  )
}
