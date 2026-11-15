import { useQuery } from '@tanstack/react-query'
import type { Dict } from '../lib/i18n'
import { isApiConfigured } from '../lib/api'
import { fetchAiMode, iconOf, labelOf, titleOf, toneOf } from '../lib/aiMode'

/** Pastille du mode IA dans l'en-tête : local, externe strict ou externe non strict. Rien si l'état est inconnu. */
export default function AiModeBadge({ t }: { t: Dict }) {
  const q = useQuery({ queryKey: ['ai-mode'], queryFn: fetchAiMode, enabled: isApiConfigured(), retry: false, staleTime: 5 * 60_000 })
  const m = q.data
  if (!m) return null
  const label = labelOf(m.kind, t)
  return (
    <span className={`ai-badge ai-${toneOf(m.kind)}`} data-testid="ai-mode" data-kind={m.kind} role="note" title={titleOf(m, t)} aria-label={label}>
      <span aria-hidden="true">{iconOf(m.kind)}</span> {label}
    </span>
  )
}
