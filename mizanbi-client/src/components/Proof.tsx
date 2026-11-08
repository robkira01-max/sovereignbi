// P-023 — Preuve de confiance : provenance, SQL, score, abstention.
// Affiché sur chaque tuile KPI / dashboard et chaque réponse Chat.
// Aucun chiffre de précision affirmé : la confiance est qualitative (démo)
// et la méthode est expliquée dans la page Certificat de précision.

export function Provenance({ table, year, sql, confidence, sourceNote }: { table: string; year: number; sql?: string; confidence?: 'high' | 'medium' | 'low'; sourceNote?: string }) {
  const label = confidence === 'high' ? 'Confiance élevée' : confidence === 'low' ? 'Confiance faible' : 'Confiance moyenne'
  return (
    <div className="muted" style={{ fontSize: 11, lineHeight: 1.6, borderTop: '1px solid oklch(25% 0.04 265 / .6)', paddingTop: 8 }}>
      <div>{sourceNote ?? <>Source : <code>{table}</code> ({year}, démo) · {label}</>}</div>
      {sql && (
        <div dir="ltr" style={{ fontFamily: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace", whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {sql}
        </div>
      )}
    </div>
  )
}

export function AbstainBox({ reason }: { reason: string }) {
  return (
    <div style={{ padding: '12px 16px', borderRadius: 12, background: 'oklch(32% 0.1 25 / .5)', color: 'oklch(80% 0.14 25)', fontSize: 14, lineHeight: 1.6 }}>
      <b>Je m'abstiens.</b> {reason}
    </div>
  )
}
