// P-080 (décision D-2) : un chiffre issu d'une formule versionnée est « Calculé » ; tout le reste est
// « Exploratoire, non certifié ». La pastille ne dit « Calculé » que si un run existe (jamais sur un simple texte).
export type Provenance = 'calculated' | 'exploratory' | 'formula_unavailable'

export interface ProvenanceInfo {
  provenance?: Provenance | string | null
  formula?: { code: string; version: number; label: string } | null
  runId?: string | null
}

export interface ProvenanceText { calculated: string; exploratory: string; unavailable: string; seeCalc: string }

/** Provenance effective : « calculated » sans run n'est jamais affiché comme calculé. */
export function effectiveProvenance(p: ProvenanceInfo): Provenance | null {
  if (p.provenance === 'calculated') return p.runId ? 'calculated' : 'exploratory'
  if (p.provenance === 'exploratory' || p.provenance === 'formula_unavailable') return p.provenance
  return null
}

const COLORS: Record<Provenance, { bg: string; fg: string }> = {
  calculated: { bg: 'oklch(30% 0.09 155 / .6)', fg: 'oklch(82% 0.15 155)' },
  exploratory: { bg: 'oklch(34% 0.08 55 / .6)', fg: 'oklch(82% 0.15 65)' },
  formula_unavailable: { bg: 'oklch(32% 0.1 25 / .6)', fg: 'oklch(78% 0.15 25)' },
}

export function ProvenanceBadge({ info, text, onOpenRun }: { info: ProvenanceInfo; text: ProvenanceText; onOpenRun?: (runId: string) => void }) {
  const p = effectiveProvenance(info)
  if (!p) return null
  const label = p === 'calculated' ? text.calculated : p === 'exploratory' ? text.exploratory : text.unavailable
  const c = COLORS[p]
  return (
    <div data-provenance={p} style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', fontSize: 12 }}>
      <span className="badge" style={{ background: c.bg, color: c.fg }}>{label}</span>
      {p === 'calculated' && info.formula && (
        <span className="muted">{info.formula.code} v{info.formula.version}{info.runId ? ` · ${info.runId.slice(0, 8)}…` : ''}</span>
      )}
      {p === 'calculated' && info.runId && onOpenRun && (
        <button type="button" onClick={() => onOpenRun(info.runId as string)} style={{ cursor: 'pointer', border: 0, background: 'transparent', color: 'oklch(75% 0.15 265)', fontWeight: 600, fontSize: 12, padding: 0 }}>
          {text.seeCalc}
        </button>
      )}
    </div>
  )
}
