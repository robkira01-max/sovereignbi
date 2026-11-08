import type { Dict } from '../lib/i18n'
import { PROVENANCE } from '../data/demo'

// P-023 — Certificat de précision : la méthode, pas une promesse de score.
// Aucun taux de précision (ex. 95 %) n'est affirmé : il doit être mesuré
// par le harnais d'évaluation sur les données du client, pas inventé ici.
export default function CertificatePage({ t }: { t: Dict }) {
  return (
    <div style={{ maxWidth: 900, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, letterSpacing: '-.02em' }}>{t.certificate}</h1>
        <p style={{ margin: '4px 0 0', color: 'var(--muted)' }}>{t.demoBadge} — {t.loi25}</p>
      </div>
      <section className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h3>Comment un chiffre est produit — et comment il est vérifié</h3>
        <ol style={{ margin: 0, paddingInlineStart: 20, lineHeight: 1.8, fontSize: 14 }}>
          <li><b>Couche sémantique d'abord.</b> Chaque question passe par les métriques définies (ex. taux de chômage = population active sans emploi / population active), pas directement par les noms de colonnes brutes. Sans elle, le text-to-SQL brut échoue souvent sur des schémas réels.</li>
          <li><b>SQL toujours visible.</b> La requête générée est affichée, repliable, copiable. Un chiffre sans SQL visible n'est pas un chiffre vérifiable.</li>
          <li><b>Dry-run avant réponse.</b> Le SQL est exécuté en lecture seule, avec garde-fou (SELECT uniquement, tables autorisées, LIMIT forcé). Aucune écriture, aucune donnée personnelle envoyée hors de l'infrastructure.</li>
          <li><b>S'abstenir plutôt qu'halluciner.</b> Hors périmètre des tables chargées, ou quand la confiance est faible, l'assistant dit « Je m'abstiens » au lieu d'inventer une réponse plausible mais fausse.</li>
          <li><b>Provenance sur chaque tuile.</b> Table, année et requête sont affichées sous chaque KPI et chaque réponse du chat, en démo comme en production.</li>
        </ol>
      </section>
      <section className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <h3>Provenance des chiffres démo affichés dans cette application</h3>
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th>Indicateur</th><th>Table</th><th>Année</th><th>Requête</th></tr></thead>
            <tbody>
              <tr><td>Chômage par région (23,5 % pondéré)</td><td>emploi_region</td><td>2024</td><td dir="ltr" style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 11 }}>{PROVENANCE.unemployment.sql}</td></tr>
              <tr><td>Population (1 030 000 hab.)</td><td>population_region</td><td>2024</td><td dir="ltr" style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 11 }}>{PROVENANCE.population.sql}</td></tr>
              <tr><td>Pauvreté par région</td><td>pauvrete_district</td><td>2024</td><td dir="ltr" style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 11 }}>{PROVENANCE.poverty.sql}</td></tr>
            </tbody>
          </table>
        </div>
        <p className="muted">Données de démonstration, marquées Démo partout. Les vrais chiffres doivent venir de l'INSTAD. Le certificat de précision sur les données du client est construit par le harnais d'évaluation, à partir de ses questions validées — il n'est pas affirmé ici.</p>
      </section>
      <section className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <h3>Ce que ce certificat ne promet pas</h3>
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.7 }}>Aucun score de précision global (par exemple 95 %) n'est affiché : il dépend du schéma, de la couche sémantique et du jeu d'évaluation du client. Les prévisions 2030 (23,1 %, IC 20,5–26,0) sont une projection indicative par tendance linéaire, pas un modèle validé. Les 11 quartiers de Djibouti-ville sont approximatifs, à valider avec la mairie. Les flux commerciaux illustratifs sont masqués par défaut (voir MizanSIG).</p>
      </section>
    </div>
  )
}
