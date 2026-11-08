import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Dict } from '../lib/i18n'
import { BCD, BCD_ATTRIBUTION, RGPH3, RGPH3_ATTRIBUTION, bcdKpi } from '../lib/bcd'
import { Provenance } from '../components/Proof'
import { currentTheme } from '../lib/theme'

// P-033 — BCD Rapport Annuel 2024 + INSTAD RGPH-3.
// Données réelles, snapshot local du 8 nov. 2026. Aucune carte : l'utilisateur
// a demandé de retirer la cartographie, elle ne ressemblait pas à Djibouti.
// Graphiques en barres 2023 vs 2024 uniquement.
const nf = (n: number, d = 1) => n.toLocaleString('fr-FR', { maximumFractionDigits: d, minimumFractionDigits: d })
const fmtInt = (n: number) => n.toLocaleString('fr-FR')

function Kpi({ label, value, sub, source }: { label: string; value: string; sub: string; source: string }) {
  return (
    <div className="card-solid">
      <div style={{ fontSize: 12, color: 'var(--muted)' }}>{label}</div>
      <div className="kpi-value">{value}</div>
      <div style={{ fontSize: 12, fontWeight: 600 }}>{sub}</div>
      <Provenance table="Rapport Annuel 2024" year={2024} sourceNote={source} />
    </div>
  )
}

export default function BcdPage({ t }: { t: Dict }) {
  const th = currentTheme()
  const tickMuted = th.vars['--muted-2']
  const pairs = (ids: string[]) => ids.map((id) => {
    const k = bcdKpi(id)!
    return { name: k.label_fr.replace(' du PIB réel', '').replace(', moyenne annuelle', ''), '2023': k.value_2023 ?? null, '2024': k.value_2024 ?? null }
  })
  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span className="badge badge-ok">{t.bcdBadge}</span>
          <span className="badge badge-ok">{t.offlineBadge}</span>
          <span className="badge badge-volet2">{t.bcdReal}</span>
        </div>
        <h1 style={{ margin: '8px 0 0', fontSize: 26, fontWeight: 700, letterSpacing: '-.02em' }}>{t.bcd}</h1>
        <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 14, lineHeight: 1.6 }}>{t.bcdSub}</p>
        <p style={{ margin: '8px 0 0', fontSize: 13, lineHeight: 1.6, padding: '10px 14px', borderRadius: 12, background: 'oklch(30% 0.09 155 / .5)' }}>{t.bcdNote}</p>
      </div>

      <h2 style={{ margin: 0, fontSize: 18 }}>Banque Centrale — Rapport Annuel 2024</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 12 }}>
        <Kpi label="Croissance du PIB réel — 2024" value="6,8 %" sub="7,4 % en 2023 · perspectives ~7 % en 2025-2028" source={BCD_ATTRIBUTION} />
        <Kpi label="Inflation moyenne — 2024" value="2,1 %" sub="1,5 % en 2023" source={BCD_ATTRIBUTION} />
        <Kpi label="Masse monétaire — 2024" value="524,7 Mds FD" sub="+3,4 % vs 507,4 Mds en 2023" source={BCD_ATTRIBUTION} />
        <Kpi label="Dette publique extérieure — 2024" value="508,9 Mds FD" sub="+4,4 % vs 487,5 Mds en 2023" source={BCD_ATTRIBUTION} />
        <Kpi label="Recettes publiques — 2024" value="137,5 Mds FD" sub="+9,4 % vs 125,7 Mds en 2023 · dépenses 157,1 Mds" source={BCD_ATTRIBUTION} />
        <Kpi label="Déficit budgétaire — 2024" value="-2,5 % du PIB" sub="-3,4 % en 2023" source={BCD_ATTRIBUTION} />
        <Kpi label="Crédits à la clientèle — 2024" value="287,7 Mds FD" sub="+35,4 % vs 212,4 Mds en 2023" source={BCD_ATTRIBUTION} />
        <Kpi label="Dépôts de la clientèle — 2024" value="487,3 Mds FD" sub="+3,6 % vs 470,4 Mds en 2023" source={BCD_ATTRIBUTION} />
      </div>

      <div className="card-solid">
        <h2 style={{ margin: '0 0 4px', fontSize: 18 }}>2023 vs 2024 — finances publiques et monnaie</h2>
        <p style={{ margin: '0 0 12px', fontSize: 13, color: 'var(--muted)' }}>Montants en milliards FD, sauf croissance et inflation en %.</p>
        <div style={{ height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={pairs(['croissance_pib_reel', 'inflation', 'masse_monetaire', 'recettes', 'depenses', 'dette_exterieure'])} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fill: tickMuted, fontSize: 11 }} interval={0} angle={-20} textAnchor="end" height={70} />
              <YAxis tick={{ fill: tickMuted, fontSize: 12 }} width={70} />
              <Tooltip contentStyle={{ background: 'var(--surface-solid)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text)' }} />
              <Bar dataKey="2023" fill="var(--brand)" name="2023" />
              <Bar dataKey="2024" fill="var(--accent)" name="2024" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <Provenance table="Rapport Annuel 2024" year={2024} sourceNote={BCD_ATTRIBUTION} />
      </div>

      <div className="card-solid">
        <h2 style={{ margin: '0 0 12px', fontSize: 18 }}>Solidité bancaire et monnaie électronique — 2024</h2>
        <ul style={{ margin: 0, paddingLeft: 20, fontSize: 14, lineHeight: 1.8 }}>
          <li><b>Bilan des banques :</b> 668,7 Mds FD, +4,9 % vs 637,3 Mds en 2023.</li>
          <li><b>Fonds propres :</b> 52,3 Mds FD, +10,4 %. <b>Solvabilité :</b> 21 % contre 19,4 % en 2023, minimum requis 12 %.</li>
          <li><b>Créances en souffrance :</b> 3,54 % contre 4,18 % en 2023, soit -15,3 %.</li>
          <li><b>Compte courant :</b> excédent 110,4 Mds FD contre 125,8 Mds en 2023, -14,6 %, contraction de 85,7 % du solde des biens.</li>
          <li><b>Service de la dette :</b> 27,183 Mds FD en 2024, dont 19,176 Mds de principal et 8,008 Mds d'intérêts, +9 % vs 2023.</li>
          <li><b>Monnaie électronique :</b> 142 681 comptes actifs contre 69 133 en 2023. 14 876 739 transactions en 2024, valeur 73,1 Mds FD contre 3 461 524 transactions et 53,4 Mds en 2023.</li>
        </ul>
        <Provenance table="Rapport Annuel 2024" year={2024} sourceNote={BCD_ATTRIBUTION} />
      </div>

      <h2 style={{ margin: 0, fontSize: 18 }}>INSTAD — RGPH-3, population</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 12 }}>
        <Kpi label="Population — 20 mai 2024" value="1 066 809" sub="818 159 en 2009 · +1,8 % par an en moyenne" source={RGPH3_ATTRIBUTION} />
        <Kpi label="Djibouti-Ville" value="767 250" sub="71,9 % de la population, résultats définitifs" source={RGPH3_ATTRIBUTION} />
        <Kpi label="Âge moyen / médian" value="25,6 / 22,9 ans" sub="Jeunesse prédominante" source={RGPH3_ATTRIBUTION} />
        <Kpi label="Ménages" value="174 658" sub="Taille moyenne : 6 personnes · urbain : 84,3 %" source={RGPH3_ATTRIBUTION} />
      </div>
      <div className="card-solid">
        <h2 style={{ margin: '0 0 12px', fontSize: 18 }}>RGPH-3 — repères</h2>
        <ul style={{ margin: 0, paddingLeft: 20, fontSize: 14, lineHeight: 1.8 }}>
          <li><b>Femmes :</b> {fmtInt(RGPH3.population_femmes)} · <b>Hommes :</b> {fmtInt(RGPH3.population_hommes)}.</li>
          <li><b>Djibouti-Ville :</b> 72,8 % dans les résultats provisoires, 71,9 % dans les résultats définitifs, 767 250 habitants. La page retient le chiffre définitif et signale l'écart.</li>
          <li><b>Recensements précédents :</b> 1983 et 2009. Le RGPH-3 est le troisième recensement général de la population et de l'habitat.</li>
        </ul>
        <Provenance table="RGPH-3" year={2024} sourceNote={RGPH3_ATTRIBUTION} />
        <p style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.6, margin: '8px 0 0' }}>
          {BCD.method} {BCD.source_url}
        </p>
      </div>
    </div>
  )
}
