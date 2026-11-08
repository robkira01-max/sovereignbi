// P-031 — Tableau de bord national Canada, d'après la maquette fournie par
// Robleh (fichier 56845_3_gcgm.webp). Mise en page de la maquette conservée :
// onglets en haut, navigation latérale, 3 KPI, emploi par province, carte du
// Canada, tranches d'âge, pied « © 2026 MizanBI • Données : Statistique Canada ».
// Thème Violet/Vert (P-028), celui de la maquette.
//
// RÈGLE D'OR — VÉRITÉ DES CHIFFRES : seuls 2 chiffres de la maquette étaient
// déjà vérifiés (chômage 6,7 % oct. 2026, population 41 798 407). TOUS les
// autres chiffres de la maquette ont été VÉRIFIÉS en direct via le WDS
// (table 14-10-0287-01, téléchargement du 8 nov. 2026) et ils étaient FAUX :
//   - chômage « -0,3 pt vs sept. 2026 » → en réalité +0,2 pt (6,5 % → 6,7 %)
//   - population « +0,8 % vs 2025 » → en réalité +0,5 % (+189 425)
//   - « 12 450 emplois créés, +1 204 » → en réalité -4 700 emplois (21 104 800 → 21 100 100)
//   - emploi par province (Ontario 3 120, Québec 2 540, …) → remplacé par les
//     variations vérifiées sept. → oct. 2026 (ex. Alberta -24 300, C.-B. +12 300)
//   - tranches d'âge 9,2 % / 68,5 % / 22,3 % → 12,6 % / 66,8 % / 20,5 %
//   - « Région la plus active : Québec » / « Alberta +4,2 % » → faux :
//     plus forte hausse = Colombie-Britannique (+12 300), plus forte baisse =
//     Alberta (-24 300, chômage +0,9 pt).
// Aucun chiffre de la maquette n'est repris sans vérification. Les écarts sont
// documentés dans la section « Corrections par rapport à la maquette » et dans
// docs/proposals-p031.md. « Plan Pro » et l'utilisatrice de la
// maquette ne sont PAS reproduits (aucun utilisateur inventé, aucun paywall —
// modèle P-026 : licence annuelle par installation).
// Carte : contours simplifiés des 10 provinces + 3 territoires
// (src/data/ca_provinces.json, Click That Hood, données ouvertes, tolérance
// de simplification ~0,15°) ; les territoires n'ont pas de série provinciale
// dans la table 14-10-0287-01, ils sont affichés en gris « sans données ».
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Dict } from '../lib/i18n'
import { STATCAN_CHOMAGE, STATCAN_EMPLOI, STATCAN_POPULATION, provinceFr, statcanAttribution } from '../lib/statcan'
import { Provenance } from '../components/Proof'
import { fmt } from '../data/demo'
import { colorForValue, currentTheme, scaleFor } from '../lib/theme'
import provinces from '../data/ca_provinces.json'

const ATTR = 'Source : Statistique Canada, Caractéristiques de la population active, données mensuelles désaisonnalisées et la tendance-cycle, octobre 2026 (table 14-10-0287-01)'
const ATTR_POP = 'Source : Statistique Canada, Estimations de la population, trimestrielles, 1er juillet 2026 (table 17-10-0009-01)'

type Tab = 'overview' | 'population' | 'emploi' | 'regions' | 'analyses'
const TABS: { id: Tab; label: string; anchor: string }[] = [
  { id: 'overview', label: "Vue d'ensemble", anchor: 'top' },
  { id: 'population', label: 'Population', anchor: 'kpi' },
  { id: 'emploi', label: 'Emploi', anchor: 'emploi-province' },
  { id: 'regions', label: 'Régions', anchor: 'carte' },
  { id: 'analyses', label: 'Analyses', anchor: 'corrections' },
]
const NAV: { label: string; anchor: string }[] = [
  { label: 'Tableau de bord', anchor: 'top' },
  { label: 'Population', anchor: 'kpi' },
  { label: 'Emploi & Chômage', anchor: 'emploi-province' },
  { label: 'Cartographie', anchor: 'carte' },
  { label: 'Rapports', anchor: 'age' },
  { label: 'Sources de données', anchor: 'sources' },
]

// Projection équirectangulaire simple pour la carte du Canada.
const LON_MIN = -168, LON_MAX = -52, LAT_MIN = 41, LAT_MAX = 84
const MW = 760, MH = 520
function project(lon: number, lat: number): [number, number] {
  return [((lon - LON_MIN) / (LON_MAX - LON_MIN)) * MW, ((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * MH]
}
function ringToPath(ring: number[][]): string {
  return ring.map(([lon, lat], i) => `${i === 0 ? 'M' : 'L'}${project(lon, lat)[0].toFixed(1)},${project(lon, lat)[1].toFixed(1)}`).join(' ') + ' Z'
}

export default function CanadaNationalPage({ t }: { t: Dict }) {
  const [tab, setTab] = useState<Tab>('overview')
  const th = currentTheme()
  const emp = STATCAN_EMPLOI
  const ch = STATCAN_CHOMAGE
  const pop = STATCAN_POPULATION
  const go = (anchor: string) => {
    document.getElementById(`canadanat-${anchor}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  const goTab = (tb: (typeof TABS)[number]) => { setTab(tb.id); go(tb.anchor) }

  const popChange = pop.canada_latest - pop.canada_previous_year
  const popChangePct = ((pop.canada_latest / pop.canada_previous_year - 1) * 100).toFixed(1).replace('.', ',')
  const rows = emp.by_province
    .filter((r) => r.province !== 'Canada')
    .map((r) => ({ province: provinceFr(r.province), change: r.change_jobs, chomage: r.unemployment_oct_2026 }))
    .sort((a, b) => b.change - a.change)
  const changes = rows.map((r) => r.change)
  const scale = scaleFor(changes, th, ' emplois', { reference: 0, referenceLabel: 'Référence : 0 (aucune variation)' })
  const byProv = new Map(emp.by_province.map((r) => [r.province, r]))
  const maxGain = rows[0]
  const maxLoss = rows[rows.length - 1]

  const exportCsv = () => {
    const lines = [
      'province;emploi_sept_2026;emploi_oct_2026;variation_emplois;chomage_sept_2026_pct;chomage_oct_2026_pct',
      ...emp.by_province.map((r) => `${r.province};${r.employment_sep_2026};${r.employment_oct_2026};${r.change_jobs};${r.unemployment_sep_2026};${r.unemployment_oct_2026}`),
      '',
      'tranche_age;emploi_oct_2026;part_pct;taux_chomage_oct_2026_pct',
      ...emp.by_age_oct_2026.map((a) => `${a.label_fr};${a.employment};${a.share_pct};${a.unemployment_rate}`),
      '',
      'Source : Statistique Canada, table 14-10-0287-01, octobre 2026, snapshot local du 8 novembre 2026. Licence ouverte de Statistique Canada.',
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'mizanbi-canada-emploi-oct-2026.csv'
    a.click()
    URL.revokeObjectURL(a.href)
  }

  return (
    <div style={{ maxWidth: 1080, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div id="canadanat-top">
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span className="badge badge-ok">{t.statcanBadge}</span>
          <span className="badge badge-ok">{t.loi25}</span>
          <span className="badge badge-ok">{t.offlineBadge}</span>
          <span className="badge badge-ok">Maquette intégrée — chiffres vérifiés</span>
        </div>
        <h1 style={{ margin: '8px 0 0', fontSize: 26, fontWeight: 700, letterSpacing: '-.02em' }}>Tableau de bord — Analyse nationale</h1>
        <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 14, lineHeight: 1.6 }}>
          Données mises à jour le 8 novembre 2026 • Canada • Thème Violet / Vert (celui de la maquette).
          Tous les chiffres ci-dessous sont vérifiés dans le snapshot StatCan local — les chiffres de la
          maquette qui se sont révélés faux sont corrigés, et les écarts sont listés en bas de page.
        </p>
      </div>

      {/* Barre d'onglets de la maquette + Exporter */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        {TABS.map((tb) => (
          <button key={tb.id} onClick={() => goTab(tb)} className={tab === tb.id ? 'btn' : 'btn-ghost'} style={{ padding: '7px 14px' }}>{tb.label}</button>
        ))}
        <span style={{ marginInlineStart: 'auto', fontSize: 13, color: 'var(--muted)' }}>Période : oct. 2026</span>
        <button onClick={exportCsv} className="btn">+ Exporter (CSV vérifié)</button>
      </div>

      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* Navigation latérale de la maquette */}
        <nav className="card-solid" aria-label="Navigation du tableau de bord" style={{ width: 200, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 2, padding: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.08em', color: 'var(--muted)', padding: '4px 10px' }}>NAVIGATION</div>
          {NAV.map((n) => (
            <button key={n.label} onClick={() => go(n.anchor)} className="btn-ghost" style={{ textAlign: 'start', justifyContent: 'flex-start', padding: '8px 10px' }}>{n.label}</button>
          ))}
        </nav>

        <div style={{ flex: 1, minWidth: 300, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* 3 KPI */}
          <div id="canadanat-kpi" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))', gap: 12 }}>
            <div className="card-solid">
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>Chômage — oct. 2026</div>
              <div className="kpi-value">{String(ch.canada_latest).replace('.', ',')} %</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'oklch(72% 0.17 155)' }}>▲ +0,2 pt vs sept. 2026 (6,5 %)</div>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>La maquette disait −0,3 pt : corrigé, voir en bas de page.</div>
              <Provenance table="14-10-0287-01" year={2026} sourceNote={statcanAttribution(ch.title_fr, 'octobre 2026')} />
            </div>
            <div className="card-solid">
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>Population — 1er juill. 2026</div>
              <div className="kpi-value">{fmt(pop.canada_latest)}</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'oklch(72% 0.17 155)' }}>▲ +{popChangePct} % vs 2025 (+{fmt(popChange)})</div>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>La maquette disait +0,8 % : corrigé, voir en bas de page.</div>
              <Provenance table="17-10-0009-01" year={2026} sourceNote={statcanAttribution(pop.title_fr, '1er juillet 2026')} />
            </div>
            <div className="card-solid">
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>Emplois — variation sept. → oct. 2026</div>
              <div className="kpi-value" style={{ color: 'oklch(72% 0.19 55)' }}>{fmt(emp.canada.change_jobs)}</div>
              <div style={{ fontSize: 12, fontWeight: 600 }}>Emploi total : {fmt(emp.canada.employment_oct_2026)} personnes</div>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>La maquette disait +12 450 emplois créés : corrigé, voir en bas de page.</div>
              <Provenance table="14-10-0287-01" year={2026} sourceNote={ATTR} />
            </div>
          </div>

          {/* Emploi par province */}
          <section id="canadanat-emploi-province" className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
              <div style={{ fontWeight: 600 }}>Variation de l'emploi par province — sept. → oct. 2026 (emplois)</div>
              <span className="muted" style={{ fontSize: 12 }}>2026 · désaisonnalisé</span>
            </div>
            <div dir="ltr" style={{ height: 320 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 24 }}>
                  <CartesianGrid stroke="oklch(25% 0.04 265)" strokeDasharray="3 3" />
                  <XAxis type="number" domain={[-26000, 14000]} tick={{ fill: th.vars['--muted-2'], fontSize: 11 }} tickFormatter={(v: number) => `${Math.round(v / 1000)} k`} />
                  <YAxis type="category" dataKey="province" width={150} tick={{ fill: th.vars['--text'], fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: th.vars['--surface-solid'], border: '1px solid var(--border)', borderRadius: 10, color: th.vars['--text'] }} formatter={(v) => [`${fmt(Number(v))} emplois`, 'Variation sept. → oct. 2026']} />
                  <Bar dataKey="change" radius={[0, 6, 6, 0]}>
                    {rows.map((d) => (
                      <Cell key={d.province} fill={d.change >= 0 ? '#34d399' : 'oklch(58% 0.22 25)'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="muted" style={{ margin: 0 }}>Vert : hausse de l'emploi ; rouge : baisse. Les valeurs de la maquette (Ontario 3 120, Québec 2 540, Colombie-Britannique 1 890, …) n'ont pas pu être vérifiées et ne sont pas reprises.</p>
            <Provenance table="14-10-0287-01" year={2026} sourceNote={`${ATTR} · Emploi, 15 ans et plus, Total - Gender, en milliers de personnes, converti en emplois.`} />
          </section>

          {/* Carte du Canada */}
          <section id="canadanat-carte" className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
              <div style={{ fontWeight: 600 }}>Répartition géographique — variation de l'emploi par province</div>
              <span className="muted" style={{ fontSize: 12 }}>Canada</span>
            </div>
            <svg viewBox={`0 0 ${MW} ${MH}`} style={{ width: '100%', display: 'block', background: 'var(--surface)', borderRadius: 10 }} role="img" aria-label="Carte du Canada colorée par la variation de l'emploi, septembre à octobre 2026">
              {provinces.features.map((f) => {
                const prov = byProv.get(f.properties.name)
                const fill = prov ? colorForValue(prov.change_jobs, scale) : 'oklch(30% 0.02 265)'
                return (
                  <g key={f.properties.name}>
                    {f.geometry.coordinates.map((poly: number[][][], pi: number) => (
                      <g key={pi}>
                        {poly.map((ring: number[][], ri: number) => (
                          <path key={ri} d={ringToPath(ring)} fill={fill} stroke="var(--bg)" strokeWidth={1} />
                        ))}
                      </g>
                    ))}
                    <title>{f.properties.name}{prov ? ` : ${fmt(prov.change_jobs)} emplois, chômage ${String(prov.unemployment_oct_2026).replace('.', ',')} %` : ' : sans données provinciales (territoire)'}</title>
                  </g>
                )
              })}
            </svg>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--muted)' }}>
              <span>{fmt(scale.min)} emplois</span>
              <span className="legend-bar" />
              <span>+{fmt(scale.max)} emplois</span>
              <span style={{ marginInlineStart: 8 }}>Variation de l'emploi, sept. → oct. 2026 · Gris : territoires, sans série provinciale</span>
            </div>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13 }}>
              <span>🟢 Plus forte hausse : <b>{maxGain.province} {fmt(maxGain.change)} emplois</b></span>
              <span>🔴 Plus forte baisse : <b>{maxLoss.province} {fmt(maxLoss.change)} emplois</b></span>
            </div>
            <p className="muted" style={{ margin: 0 }}>
              La maquette disait « Région la plus active : Québec » et « Croissance la plus forte : Alberta +4,2 % ».
              Vérification : l'Alberta est la province qui perd le plus d'emplois (−24 300) et dont le chômage
              augmente le plus (+0,9 pt, 6,4 % → 7,3 %). Ces deux mentions ne sont donc pas reprises.
            </p>
            <Provenance table="14-10-0287-01" year={2026} sourceNote={`${ATTR} · Contours simplifiés (Click That Hood, données ouvertes).`} />
          </section>

          {/* Tranches d'âge */}
          <section id="canadanat-age" className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontWeight: 600 }}>Indicateurs clés — Répartition de l'emploi par tranche d'âge, oct. 2026</div>
            {emp.by_age_oct_2026.map((a) => (
              <div key={a.age}>
                <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8, fontSize: 14 }}>
                  <span>{a.label_fr} : <b>{String(a.share_pct).replace('.', ',')} %</b> de l'emploi</span>
                  <span className="muted">{fmt(a.employment)} emplois · chômage {String(a.unemployment_rate).replace('.', ',')} %</span>
                </div>
                <div style={{ height: 8, borderRadius: 4, background: 'oklch(25% 0.04 265)', marginTop: 4 }}>
                  <div style={{ width: `${a.share_pct}%`, height: '100%', borderRadius: 4, background: '#34d399' }} />
                </div>
              </div>
            ))}
            <p className="muted" style={{ margin: 0 }}>
              La maquette disait 9,2 % / 68,5 % / 22,3 % : corrigé. Parts calculées sur l'emploi total
              d'octobre 2026 ({fmt(emp.canada.employment_oct_2026)}).
            </p>
            <Provenance table="14-10-0287-01" year={2026} sourceNote={`${ATTR} · Emploi par groupe d'âge, 15 ans et plus, Total - Gender, désaisonnalisé.`} />
          </section>

          {/* Corrections */}
          <section id="canadanat-corrections" className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontWeight: 600 }}>Corrections par rapport à la maquette — ce qui a été vérifié, ce qui a été corrigé</div>
            <div className="table-wrap">
              <table className="data">
                <thead><tr><th>Chiffre de la maquette</th><th>Maquette</th><th>Vérifié (StatCan)</th><th>Statut</th></tr></thead>
                <tbody>
                  <tr><td>Chômage Canada, oct. 2026</td><td>6,7 %</td><td>6,7 %</td><td>✓ Vérifié</td></tr>
                  <tr><td>Variation du chômage vs sept. 2026</td><td>−0,3 pt</td><td>+0,2 pt (6,5 % → 6,7 %)</td><td>Corrigé</td></tr>
                  <tr><td>Population Canada</td><td>41 798 407</td><td>41 798 407</td><td>✓ Vérifié</td></tr>
                  <tr><td>Population vs 2025</td><td>+0,8 %</td><td>+0,5 % (+189 425)</td><td>Corrigé</td></tr>
                  <tr><td>Emplois créés (mois)</td><td>12 450 (+1 204)</td><td>−4 700 emplois</td><td>Corrigé</td></tr>
                  <tr><td>Emploi par province</td><td>Ontario 3 120, Québec 2 540, C.-B. 1 890, Alberta 1 340, Manitoba 520, Saskatchewan 410, N.-É. 280</td><td>Variations sept. → oct. : C.-B. +12 300, Québec +7 500, Alberta −24 300, Ontario −8 600…</td><td>Corrigé</td></tr>
                  <tr><td>Tranches d'âge</td><td>9,2 % / 68,5 % / 22,3 %</td><td>12,6 % / 66,8 % / 20,5 %</td><td>Corrigé</td></tr>
                  <tr><td>Région la plus active / croissance</td><td>Québec / Alberta +4,2 %</td><td>Plus forte hausse : C.-B. +12 300 ; plus forte baisse : Alberta −24 300</td><td>Corrigé</td></tr>
                </tbody>
              </table>
            </div>
            <p className="muted" style={{ margin: 0 }}>
              Méthode : CSV complet de la table 14-10-0287-01 téléchargé via le WDS le 8 novembre 2026,
              filtré sur Estimate, données désaisonnalisées, Total - Gender, 15 ans et plus.
              Emploi en milliers de personnes, converti en emplois. Les chiffres de la maquette
              non vérifiables ne sont repris nulle part comme des données réelles.
            </p>
          </section>

          <section id="canadanat-sources" className="card-solid" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontWeight: 600 }}>Sources de données</div>
            <p style={{ margin: 0, fontSize: 13, lineHeight: 1.6 }}>
              {ATTR} · {ATTR_POP} · Licence ouverte de Statistique Canada : usage, reproduction et
              distribution permis, avec attribution, sans suggérer que Statistique Canada approuve MizanBI.
              Snapshot local du 8 novembre 2026 (emploi) et du 7 novembre 2026 (chômage, population, IPC) —
              à rafraîchir, voir README, section Statistique Canada. Les chiffres canadiens ne sont jamais
              mélangés aux chiffres démo de Djibouti (1 030 000 hab., chômage 23,5 %).
            </p>
            <Provenance table="14-10-0287-01 / 17-10-0009-01" year={2026} sourceNote={`${ATTR} · ${ATTR_POP}`} />
          </section>

          <footer style={{ textAlign: 'center', fontSize: 12, color: 'var(--muted)', padding: '8px 0 4px' }}>
            © 2026 MizanBI • Données : Statistique Canada • Mode sombre activé
          </footer>
        </div>
      </div>
    </div>
  )
}
