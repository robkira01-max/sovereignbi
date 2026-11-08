import { useState } from 'react'
import { CartesianGrid, ComposedChart, Line, Area, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Dict } from '../lib/i18n'
import { BIE, BIE_SOURCES, bieAttribution, bieForecast, bieIndicator, yoy } from '../lib/bie'
import { Provenance } from '../components/Proof'
import { fmt } from '../data/demo'
import { currentTheme } from '../lib/theme'

// P-030 — Analyse BIE, Ministère des Finances de Djibouti.
// Données RÉELLES (snapshot local du 8 nov. 2026), séparées des chiffres démo
// de Djibouti (1 030 000 hab. / 23,5 %) et des données StatCan Canada.
// Accent sur L'ÉVOLUTION (graphiques, variations d'année en année, ruptures,
// tableau récapitulatif par année) + partie PRÉVISIONS séparée et étiquetée :
// modèle MizanBI (tendance linéaire, intervalle), jamais présenté comme une
// donnée du ministère ; les prévisions du ministère (BIE 2008) sont montrées
// à part, pour comparaison. Aucun prix, client ou délai inventé.
type IndId = 'croissance_pib_reel' | 'pib_nominal_mfd' | 'inflation_ipc_moyenne' | 'recettes_depenses' | 'dette_exterieure_mfd'
const INDICATORS: { id: IndId; label: string }[] = [
  { id: 'croissance_pib_reel', label: 'Croissance du PIB réel (%)' },
  { id: 'pib_nominal_mfd', label: 'PIB nominal (millions FD)' },
  { id: 'inflation_ipc_moyenne', label: 'Inflation, IPC moyenne annuelle (%)' },
  { id: 'recettes_depenses', label: 'Recettes et dépenses (millions FD)' },
  { id: 'dette_exterieure_mfd', label: 'Dette extérieure (millions FD)' },
]

const nf = (n: number, d = 1) => n.toLocaleString('fr-FR', { maximumFractionDigits: d, minimumFractionDigits: d })
const pct = (n: number | null) => (n === null ? '—' : `${n > 0 ? '+' : ''}${nf(n)} %`)

export default function BiePage({ t }: { t: Dict }) {
  const [ind, setInd] = useState<IndId>('croissance_pib_reel')
  const th = currentTheme()
  const tickMuted = th.vars['--muted-2']
  const growth = bieIndicator('croissance_pib_reel')!
  const pib = bieIndicator('pib_nominal_mfd')!
  const infl = bieIndicator('inflation_ipc_moyenne')!
  const rec = bieIndicator('recettes_dons_mfd')!
  const dep = bieIndicator('depenses_totales_mfd')!
  const solde = bieIndicator('solde_mfd')!
  const dette = bieIndicator('dette_exterieure_mfd')!
  const detPib = bieIndicator('dette_pib_pct')!
  const fc = bieForecast(ind === 'recettes_depenses' || ind === 'inflation_ipc_moyenne' ? 'croissance_pib_reel' : ind)

  // Données du graphique : réel (solide) + prévisions du ministère (pointillé)
  // + prévisions du modèle MizanBI (bande d'intervalle) pour les 3 indicateurs prévus.
  const chartData = (() => {
    const years = [2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012]
    const real = (id: string) => new Map(bieIndicator(id)!.values.filter((v) => v.status === 'reel').map((v) => [v.year, v.value]))
    const mf = BIE.ministry_forecasts_2008
    return years.map((y) => {
      const row: Record<string, number | null> = { year: y }
      if (ind === 'croissance_pib_reel') {
        row.reel = real('croissance_pib_reel').get(y) ?? null
        row.ministere = mf.croissance_pib_reel.find((v) => v.year === y)?.value ?? null
        const f = bieForecast('croissance_pib_reel')!.values.find((v) => v.year === y)
        row.modele = f?.central ?? null; row.bas = f?.low ?? null; row.haut = f?.high ?? null
      } else if (ind === 'pib_nominal_mfd') {
        row.reel = real('pib_nominal_mfd').get(y) ?? null
        row.ministere = mf.pib_nominal_mfd.find((v) => v.year === y)?.value ?? null
        const f = bieForecast('pib_nominal_mfd')!.values.find((v) => v.year === y)
        row.modele = f?.central ?? null; row.bas = f?.low ?? null; row.haut = f?.high ?? null
      } else if (ind === 'inflation_ipc_moyenne') {
        row.reel = real('inflation_ipc_moyenne').get(y) ?? null
      } else if (ind === 'recettes_depenses') {
        row.recettes = real('recettes_dons_mfd').get(y) ?? null
        row.depenses = real('depenses_totales_mfd').get(y) ?? null
      } else {
        row.reel = real('dette_exterieure_mfd').get(y) ?? null
        const f = bieForecast('dette_exterieure_mfd')!.values.find((v) => v.year === y)
        row.modele = f?.central ?? null; row.bas = f?.low ?? null; row.haut = f?.high ?? null
      }
      return row
    })
  })()
  const hasForecast = ind === 'croissance_pib_reel' || ind === 'pib_nominal_mfd' || ind === 'dette_exterieure_mfd'
  const hasMinistry = ind === 'croissance_pib_reel' || ind === 'pib_nominal_mfd'

  const years = [2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012]
  const val = (id: string, y: number) => bieIndicator(id)!.values.find((v) => v.year === y && v.status === 'reel')?.value ?? null

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span className="badge badge-ok">{t.bieBadge}</span>
          <span className="badge badge-ok">{t.offlineBadge}</span>
          <span className="badge badge-volet2">{t.bieReal}</span>
        </div>
        <h1 style={{ margin: '8px 0 0', fontSize: 26, fontWeight: 700, letterSpacing: '-.02em' }}>{t.bie}</h1>
        <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 14, lineHeight: 1.6 }}>{t.bieSub}</p>
        <p style={{ margin: '8px 0 0', fontSize: 13, lineHeight: 1.6, padding: '10px 14px', borderRadius: 12, background: 'oklch(30% 0.09 155 / .5)' }}>
          {t.bieNote}
        </p>
      </div>

      {/* KPI 2008, dernière année complète des BIE annuels */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 12 }}>
        <div className="card-solid">
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>Croissance du PIB réel — 2008</div>
          <div className="kpi-value">5,8 %</div>
          <div style={{ fontSize: 12, fontWeight: 600 }}>▲ +0,5 pt vs 2007 (5,3 %)</div>
          <Provenance table="BIE 2008" year={2008} sourceNote={bieAttribution(growth.values.find((v) => v.year === 2008)?.source)} />
        </div>
        <div className="card-solid">
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>Inflation moyenne — 2008</div>
          <div className="kpi-value">6,0 %</div>
          <div style={{ fontSize: 12, fontWeight: 600 }}>▲ +1,0 pt vs 2007 (5,0 %)</div>
          <Provenance table="BIE 2008" year={2008} sourceNote={bieAttribution(infl.values.find((v) => v.year === 2008)?.source)} />
        </div>
        <div className="card-solid">
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>Dette extérieure — 2008</div>
          <div className="kpi-value">100,9 Mds FD</div>
          <div style={{ fontSize: 12, fontWeight: 600 }}>57,8 % du PIB — seuil 60 % proche</div>
          <Provenance table="BIE 2008" year={2008} sourceNote={bieAttribution(dette.values.find((v) => v.year === 2008)?.source)} />
        </div>
        <div className="card-solid">
          <div style={{ fontSize: 12, color: 'var(--muted)' }}>Recettes et dons — 2011</div>
          <div className="kpi-value">76,0 Mds FD</div>
          <div style={{ fontSize: 12, fontWeight: 600 }}>Dépenses 77,7 Mds — solde −1,7 Md</div>
          <Provenance table="Note T4 2011" year={2011} sourceNote={bieAttribution(rec.values.find((v) => v.year === 2011)?.source)} />
        </div>
      </div>

      {/* Évolution */}
      <div className="card-solid">
        <h2 style={{ margin: '0 0 4px', fontSize: 18 }}>Évolution 2000-2012</h2>
        <p style={{ margin: '0 0 12px', fontSize: 13, color: 'var(--muted)', lineHeight: 1.6 }}>
          Trait plein : données du ministère. Pointillé : prévisions du ministère (BIE 2008). Bande : prévisions du modèle MizanBI avec intervalle.
          Les années manquantes coupent la courbe : elles ne sont jamais interpolées.
        </p>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
          {INDICATORS.map((i) => (
            <button key={i.id} className={ind === i.id ? 'btn' : 'btn-ghost'} onClick={() => setInd(i.id)}>{i.label}</button>
          ))}
        </div>
        <div style={{ height: 320 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
              <XAxis dataKey="year" tick={{ fill: tickMuted, fontSize: 12 }} />
              <YAxis tick={{ fill: tickMuted, fontSize: 12 }} width={70} />
              <Tooltip contentStyle={{ background: 'var(--surface-solid)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text)' }} />
              {hasForecast && <Area type="monotone" dataKey="haut" stroke="none" fill="var(--accent)" fillOpacity={0.12} connectNulls name="Borne haute (modèle)" />}
              {hasForecast && <Area type="monotone" dataKey="bas" stroke="none" fill="var(--surface-solid)" fillOpacity={1} connectNulls name="Borne basse (modèle)" />}
              {ind === 'recettes_depenses' ? (
                <>
                  <Line type="monotone" dataKey="recettes" stroke="var(--accent)" strokeWidth={2} dot={false} connectNulls={false} name="Recettes et dons" />
                  <Line type="monotone" dataKey="depenses" stroke="var(--danger)" strokeWidth={2} dot={false} connectNulls={false} name="Dépenses totales" />
                </>
              ) : (
                <>
                  <Line type="monotone" dataKey="reel" stroke="var(--accent)" strokeWidth={2.5} dot={{ r: 3 }} connectNulls={false} name="Réel (ministère)" />
                  {hasMinistry && <Line type="monotone" dataKey="ministere" stroke="var(--warning)" strokeWidth={2} strokeDasharray="5 5" dot={false} connectNulls={false} name="Prévision du ministère (2008)" />}
                  {hasForecast && <Line type="monotone" dataKey="modele" stroke="var(--brand)" strokeWidth={2} strokeDasharray="2 3" dot={false} connectNulls={false} name="Modèle MizanBI (central)" />}
                </>
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
        <Provenance table="BIE" year={2008} sourceNote={bieAttribution((ind === 'recettes_depenses' ? rec : bieIndicator(ind)!)?.values.find((v) => v.status === 'reel')?.source)} />
        {fc && ind !== 'recettes_depenses' && ind !== 'inflation_ipc_moyenne' && (
          <p style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.6, margin: '8px 0 0' }}>{fc.method}</p>
        )}
      </div>

      {/* Tableau récapitulatif par année */}
      <div className="card-solid">
        <h2 style={{ margin: '0 0 12px', fontSize: 18 }}>Tableau récapitulatif par année</h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead><tr style={{ textAlign: 'left', color: 'var(--muted)' }}>
              <th style={{ padding: '6px 8px' }}>Année</th><th style={{ padding: '6px 8px' }}>Croissance PIB</th><th style={{ padding: '6px 8px' }}>Recettes et dons</th><th style={{ padding: '6px 8px' }}>Dépenses</th><th style={{ padding: '6px 8px' }}>Solde</th><th style={{ padding: '6px 8px' }}>Dette ext.</th><th style={{ padding: '6px 8px' }}>Dette / PIB</th>
            </tr></thead>
            <tbody>
              {years.map((y) => (
                <tr key={y} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={{ padding: '6px 8px', fontWeight: 700 }}>{y}</td>
                  <td style={{ padding: '6px 8px' }}>{val('croissance_pib_reel', y) !== null ? `${nf(val('croissance_pib_reel', y)!, 1)} % (${pct(yoy(growth.values, y))})` : '—'}</td>
                  <td style={{ padding: '6px 8px' }}>{val('recettes_dons_mfd', y) !== null ? `${fmt(val('recettes_dons_mfd', y)!)} (${pct(yoy(rec.values.filter((v) => v.status === 'reel'), y))})` : '—'}</td>
                  <td style={{ padding: '6px 8px' }}>{val('depenses_totales_mfd', y) !== null ? fmt(val('depenses_totales_mfd', y)!) : '—'}</td>
                  <td style={{ padding: '6px 8px' }}>{val('solde_mfd', y) !== null ? fmt(val('solde_mfd', y)!) : '—'}</td>
                  <td style={{ padding: '6px 8px' }}>{val('dette_exterieure_mfd', y) !== null ? fmt(val('dette_exterieure_mfd', y)!) : '—'}</td>
                  <td style={{ padding: '6px 8px' }}>{val('dette_pib_pct', y) !== null ? `${nf(val('dette_pib_pct', y)!, 1)} %` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.6 }}>Montants en millions FD. Les variations entre parenthèses sont d'année en année. 2009 : pas de total annuel (note T4 absente). 2012 : cumuls à fin septembre seulement, hors tableau annuel.</p>
      </div>

      {/* Analyse */}
      <div className="card-solid">
        <h2 style={{ margin: '0 0 12px', fontSize: 18 }}>Analyse — ce que montrent les bulletins</h2>
        <ol style={{ margin: 0, paddingLeft: 20, fontSize: 14, lineHeight: 1.8 }}>
          <li><b>Accélération de la croissance, puis rupture en 2006.</b> La croissance du PIB réel passe de 0,4 % en 2000 à 3,2 % en 2005, puis bondit : 4,8 % en 2006, 5,3 % en 2007, 5,8 % en 2008. Le BIE 2008 l'attribue aux IDE, au port et au bâtiment, avec un secteur primaire dynamique.</li>
          <li><b>L'inflation suit la flambée mondiale.</b> IPC moyen : 3,1 % en 2005, 3,5 % en 2006, 5,0 % en 2007, 6,0 % en 2008 (pétrole, alimentation, logement, eau et électricité), puis retour à 2,7 % en moyenne en 2011. L'indice général passe de 141,0 en déc. 2009 à 144,9 en déc. 2010 (+2,8 %).</li>
          <li><b>2008, année exceptionnelle pour les finances publiques.</b> Recettes et dons +37,9 % (73,1 Mds FD), tirées par les dons +205 % (22,8 Mds FD). Dépenses +24,6 % (70,9 Mds FD), investissements +43,4 %. Résultat : le seul excédent de la série, +2,2 Mds FD, après −3,9 Mds en 2007.</li>
          <li><b>Le déficit revient dès 2010.</b> Recettes 71,1 Mds contre dépenses 72,1 Mds en 2010 (solde −1,0 Md), puis 76,0 Mds contre 77,7 Mds en 2011 (solde −1,7 Md). Les salaires passent de 20,8 Mds en 2007 à 24,6 Mds en 2011.</li>
          <li><b>La dette double presque en sept ans.</b> Encours extérieur : 47,6 Mds FD en 2001, 100,9 Mds en 2008 (+112 %), soit 57,8 % du PIB en 2008, proche du seuil de 60 % cité par le BIE. Les multilatéraux dominent (75 % en 2008, IDA et BAD en tête).</li>
          <li><b>Un commerce extérieur structurellement déficitaire.</b> Exportations de biens et services : 40,6 % du PIB en 2005, 43,3 % en 2007. Importations : −55 % puis −75,3 % du PIB en 2007. L'écart se creuse avec les investissements (Doraleh, zone franche).</li>
          <li><b>L'investissement change d'échelle.</b> Investissement brut : 23,2 % du PIB en 2005, 35,0 % en 2006, 42,1 % en 2007 — porté par les IDE (8,3 % du PIB en 2005, 21,3 % en 2006, 23 % en 2007), le port de Doraleh, la zone franche et l'hôtellerie.</li>
          <li><b>Limites à garder en tête.</b> 2001-2004 : documents inaccessibles (cadres, fichiers vides). 2009 : pas de total annuel. Les bulletins révisent leurs propres chiffres (croissance 2006 : 4,5 % provisoire puis 4,8 % ; recettes 2005 : 43,5 puis 46,7 Mds FD) — la page retient la dernière vintage et signale l'écart. Les valeurs 2008-2010 des tableaux prospectifs sont des prévisions du ministère, pas du réalisé.</li>
        </ol>
      </div>

      {/* Prévisions */}
      <div className="card-solid" style={{ border: '2px solid var(--warning)' }}>
        <h2 style={{ margin: '0 0 4px', fontSize: 18 }}>Prévisions — modèle MizanBI, horizon 2009-2012</h2>
        <p style={{ margin: '0 0 12px', fontSize: 13, color: 'var(--muted)', lineHeight: 1.6 }}>
          Ces prévisions sont produites par MizanBI, pas par le ministère. Méthode simple et transparente, identique pour les trois indicateurs :
          tendance linéaire par moindres carrés ordinaires sur la série réalisée, intervalle à ±1,96 × écart-type résiduel (environ 95 %).
          La prévision du ministère (BIE 2008) est affichée à côté, pour comparaison.
        </p>
        {BIE.forecasts_model.map((f) => (
          <div key={f.indicator} style={{ marginBottom: 16 }}>
            <h3 style={{ margin: '0 0 6px', fontSize: 15 }}>{f.label_fr} ({f.unit})</h3>
            <p style={{ margin: '0 0 8px', fontSize: 12, color: 'var(--muted)', lineHeight: 1.6 }}>{f.method}</p>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead><tr style={{ textAlign: 'left', color: 'var(--muted)' }}>
                  <th style={{ padding: '6px 8px' }}>Année</th><th style={{ padding: '6px 8px' }}>Modèle (central)</th><th style={{ padding: '6px 8px' }}>Intervalle</th><th style={{ padding: '6px 8px' }}>Prévision du ministère (2008)</th>
                </tr></thead>
                <tbody>
                  {f.values.map((v) => {
                    const mf = f.indicator === 'croissance_pib_reel' ? BIE.ministry_forecasts_2008.croissance_pib_reel.find((x) => x.year === v.year)?.value
                      : f.indicator === 'pib_nominal_mfd' ? BIE.ministry_forecasts_2008.pib_nominal_mfd.find((x) => x.year === v.year)?.value : null
                    return (
                      <tr key={v.year} style={{ borderTop: '1px solid var(--border)' }}>
                        <td style={{ padding: '6px 8px', fontWeight: 700 }}>{v.year}</td>
                        <td style={{ padding: '6px 8px' }}>{f.indicator === 'croissance_pib_reel' ? `${nf(v.central, 2)} %` : fmt(Math.round(v.central))}</td>
                        <td style={{ padding: '6px 8px' }}>[{f.indicator === 'croissance_pib_reel' ? `${nf(v.low, 2)} %` : fmt(Math.round(v.low))} ; {f.indicator === 'croissance_pib_reel' ? `${nf(v.high, 2)} %` : fmt(Math.round(v.high))}]</td>
                        <td style={{ padding: '6px 8px' }}>{mf !== null && mf !== undefined ? (f.indicator === 'croissance_pib_reel' ? `${nf(mf, 1)} %` : fmt(mf)) : '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <p style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.6, margin: '6px 0 0' }}>⚠ {f.warning}</p>
          </div>
        ))}
        <h3 style={{ margin: '12px 0 6px', fontSize: 15 }}>Pas de prévision pour ces indicateurs</h3>
        <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, lineHeight: 1.7, color: 'var(--muted)' }}>
          {BIE.no_forecast.map((n) => (
            <li key={n.indicator}><b style={{ color: 'var(--text)' }}>{bieIndicator(n.indicator)?.label_fr ?? n.indicator}</b> — {n.reason}</li>
          ))}
        </ul>
      </div>

      {/* Couverture */}
      <div className="card-solid">
        <h2 style={{ margin: '0 0 12px', fontSize: 18 }}>Couverture par année — ce qui est accessible, ce qui ne l'est pas</h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead><tr style={{ textAlign: 'left', color: 'var(--muted)' }}>
              <th style={{ padding: '6px 8px' }}>Année</th><th style={{ padding: '6px 8px' }}>Statut</th><th style={{ padding: '6px 8px' }}>Détail</th>
            </tr></thead>
            <tbody>
              {BIE.coverage.map((c) => (
                <tr key={c.year} style={{ borderTop: '1px solid var(--border)' }}>
                  <td style={{ padding: '6px 8px', fontWeight: 700 }}>{c.year}</td>
                  <td style={{ padding: '6px 8px' }}>{c.status === 'accessible' ? '✅ Accessible' : c.status === 'partiel' ? '⚠ Partiel' : '❌ Inaccessible'}</td>
                  <td style={{ padding: '6px 8px' }}>{c.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p style={{ fontSize: 12, color: 'var(--muted)', lineHeight: 1.6 }}>
          {BIE_SOURCES.documents.filter((d) => d.status === 'ok').length} documents accessibles sur {BIE_SOURCES.documents.length} liens listés, téléchargés le 8 novembre 2026 depuis {BIE.source_page}.
          Les PDF bruts ne sont pas dans le dépôt : seul le snapshot JSON léger est embarqué.
        </p>
      </div>
    </div>
  )
}
