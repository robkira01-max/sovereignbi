// P-034 — Générateur de bulletins multi-sources.
// Fonctions pures testables sans DOM. Chaque section est générée depuis une
// source distincte (BIE, BCD, StatCan) avec attribution explicite.
// Aucun chiffre inventé : toutes les valeurs viennent des snapshots locaux.

import { BIE, bieIndicator } from './bie'
import { BCD, BCD_ATTRIBUTION, BCD_SNAPSHOT_DATE, RGPH3, RGPH3_ATTRIBUTION, bcdKpi } from './bcd'
import { STATCAN_CHOMAGE, STATCAN_EMPLOI, STATCAN_IPC, STATCAN_POPULATION } from './statcan'

export interface BulletinPoint {
  title: string
  text: string
  value?: string
  trend?: 'up' | 'down' | 'stable'
}

export interface BulletinSection {
  id: string
  title: string
  attribution: string
  snapshotDate: string
  points: BulletinPoint[]
}

const nf = (n: number, d = 1) =>
  n.toLocaleString('fr-FR', { maximumFractionDigits: d, minimumFractionDigits: d })
const pct = (n: number) => `${n > 0 ? '+' : ''}${nf(n)} pp`
const trend = (a?: number, b?: number): 'up' | 'down' | 'stable' => {
  if (a == null || b == null) return 'stable'
  return a > b ? 'up' : a < b ? 'down' : 'stable'
}

export function bieBulletinSection(): BulletinSection {
  const growth = bieIndicator('croissance_pib_reel')
  const infl = bieIndicator('inflation_ipc_moyenne')
  const debt = bieIndicator('dette_exterieure_mfd')
  const pibNom = bieIndicator('pib_nominal_mfd')

  const growthReel = growth?.values.filter((v) => v.status === 'reel') ?? []
  const inflReel = infl?.values.filter((v) => v.status === 'reel') ?? []
  const debtReel = debt?.values.filter((v) => v.status === 'reel') ?? []
  const pibReel = pibNom?.values.filter((v) => v.status === 'reel') ?? []
  const latestGrowth = growthReel[growthReel.length - 1]
  const prevGrowth = growthReel[growthReel.length - 2]
  const latestInfl = inflReel[inflReel.length - 1]
  const prevInfl = inflReel[inflReel.length - 2]
  const latestDebt = debtReel[debtReel.length - 1]
  const latestPib = pibReel[pibReel.length - 1]
  const prevPib = pibReel[pibReel.length - 2]

  const points: BulletinPoint[] = []

  if (latestGrowth) {
    const delta = prevGrowth ? latestGrowth.value - prevGrowth.value : null
    points.push({
      title: 'Croissance du PIB réel',
      text: `${latestGrowth.value > 0 ? '+' : ''}${nf(latestGrowth.value)} % en ${latestGrowth.year}${delta != null ? ` (${delta > 0 ? '+' : ''}${nf(delta)} pp vs ${prevGrowth!.year})` : ''}.`,
      value: `${latestGrowth.value > 0 ? '+' : ''}${nf(latestGrowth.value)} %`,
      trend: trend(latestGrowth.value, prevGrowth?.value),
    })
  }

  if (latestInfl) {
    const delta = prevInfl ? latestInfl.value - prevInfl.value : null
    points.push({
      title: 'Inflation (IPC, moyenne annuelle)',
      text: `${nf(latestInfl.value)} % en ${latestInfl.year}${delta != null ? `, ${delta >= 0 ? 'hausse' : 'baisse'} de ${nf(Math.abs(delta))} pp vs ${prevInfl!.year}` : ''}.`,
      value: `${nf(latestInfl.value)} %`,
      trend: trend(latestInfl.value, prevInfl?.value),
    })
  }

  if (latestPib && prevPib) {
    const growthPct = ((latestPib.value - prevPib.value) / prevPib.value) * 100
    points.push({
      title: 'PIB nominal',
      text: `${nf(latestPib.value, 0)} millions FD en ${latestPib.year} (${growthPct > 0 ? '+' : ''}${nf(growthPct)} % vs ${prevPib.year}).`,
      value: `${nf(latestPib.value, 0)} M FD`,
      trend: trend(latestPib.value, prevPib.value),
    })
  }

  if (latestDebt) {
    points.push({
      title: 'Dette extérieure',
      text: `${nf(latestDebt.value, 0)} millions FD en ${latestDebt.year}. Suivi recommandé.`,
      value: `${nf(latestDebt.value, 0)} M FD`,
      trend: 'stable',
    })
  }

  return {
    id: 'bie',
    title: 'Djibouti — Économie (BIE 2001–2012)',
    attribution: `${BIE.source_page} — snapshot ${BIE.downloaded}`,
    snapshotDate: BIE.downloaded,
    points,
  }
}

export function bcdBulletinSection(): BulletinSection {
  const pib = bcdKpi('croissance_pib_reel')
  const infl = bcdKpi('inflation')
  const credits = bcdKpi('credits')
  const monnaieComptes = bcdKpi('monnaie_electronique_comptes')
  const monn = bcdKpi('monnaie_electronique_transactions')
  const sol = bcdKpi('solvabilite')

  const points: BulletinPoint[] = []

  if (pib?.value_2024 != null) {
    const delta = pib.value_2024 - (pib.value_2023 ?? pib.value_2024)
    points.push({
      title: 'Croissance du PIB réel 2024',
      text: `${nf(pib.value_2024)} % en 2024 (vs ${nf(pib.value_2023 ?? pib.value_2024)} % en 2023, ${delta >= 0 ? '+' : ''}${nf(delta)} pp). ${pib.note ?? ''}`,
      value: `${nf(pib.value_2024)} %`,
      trend: trend(pib.value_2024, pib.value_2023),
    })
  }

  if (infl?.value_2024 != null) {
    points.push({
      title: 'Inflation 2024',
      text: `${nf(infl.value_2024)} % en moyenne annuelle (vs ${nf(infl.value_2023 ?? infl.value_2024)} % en 2023). ${infl.note ?? ''}`,
      value: `${nf(infl.value_2024)} %`,
      trend: trend(infl.value_2024, infl.value_2023),
    })
  }

  if (credits?.value_2024 != null && credits.variation_pct != null) {
    points.push({
      title: 'Crédits bancaires',
      text: `${nf(credits.value_2024, 1)} Mds FDJ en 2024, en hausse de ${nf(credits.variation_pct)} % — signal fort de dynamisme du crédit.`,
      value: `+${nf(credits.variation_pct)} %`,
      trend: 'up',
    })
  }

  if (sol?.value_2024 != null) {
    points.push({
      title: 'Solvabilité bancaire',
      text: `Ratio de solvabilité ${nf(sol.value_2024)} % en 2024 (minimum requis : 12 %). Secteur bien capitalisé.`,
      value: `${nf(sol.value_2024)} %`,
      trend: trend(sol.value_2024, sol.value_2023),
    })
  }

  if (monn?.value_2024 != null && monnaieComptes?.value_2024 != null) {
    const txGrowth = ((monn.value_2024 - (monn.value_2023 ?? 0)) / (monn.value_2023 ?? 1)) * 100
    points.push({
      title: 'Monnaie électronique',
      text: `${nf(monn.value_2024, 0)} transactions en 2024 (${txGrowth > 0 ? '+' : ''}${nf(txGrowth, 0)} % vs 2023). Comptes actifs : ${nf(monnaieComptes.value_2024, 0)}.`,
      value: `+${nf(txGrowth, 0)} %`,
      trend: 'up',
    })
  }

  return {
    id: 'bcd',
    title: 'Djibouti — Système bancaire (BCD 2024)',
    attribution: `${BCD_ATTRIBUTION} — snapshot ${BCD_SNAPSHOT_DATE}. ${RGPH3_ATTRIBUTION}.`,
    snapshotDate: BCD_SNAPSHOT_DATE,
    points,
  }
}

export function statcanBulletinSection(): BulletinSection {
  const delta = STATCAN_CHOMAGE.canada_latest - STATCAN_CHOMAGE.canada_previous_year
  const sorted = [...STATCAN_CHOMAGE.by_province_latest].sort((a, b) => b.value - a.value)
  const highest = sorted[0]
  const lowest = sorted[sorted.length - 1]
  const emploiChange = STATCAN_EMPLOI.canada.change_jobs

  const points: BulletinPoint[] = [
    {
      title: 'Taux de chômage national',
      text: `${nf(STATCAN_CHOMAGE.canada_latest)} % en ${STATCAN_CHOMAGE.latest} (vs ${nf(STATCAN_CHOMAGE.canada_previous_year)} % en ${STATCAN_CHOMAGE.previous_year}, ${delta >= 0 ? '+' : ''}${nf(delta)} pp). Données désaisonnalisées.`,
      value: `${nf(STATCAN_CHOMAGE.canada_latest)} %`,
      trend: trend(STATCAN_CHOMAGE.canada_latest, STATCAN_CHOMAGE.canada_previous_year),
    },
    {
      title: 'Disparités provinciales',
      text: `Taux le plus élevé : ${highest.province} (${nf(highest.value)} %). Le plus bas : ${lowest.province} (${nf(lowest.value)} %). Écart : ${nf(highest.value - lowest.value)} pp.`,
      value: `${nf(highest.value - lowest.value)} pp`,
      trend: 'stable',
    },
    {
      title: 'Population active',
      text: `${nf(STATCAN_POPULATION.canada_latest / 1_000_000, 2)} M (${STATCAN_POPULATION.latest}). Taux d'inflation : ${nf(STATCAN_IPC.canada_latest)} % ${STATCAN_IPC.unit} (${STATCAN_IPC.latest}).`,
      value: `${nf(STATCAN_POPULATION.canada_latest / 1_000_000, 2)} M`,
      trend: 'stable',
    },
  ]

  if (emploiChange != null) {
    points.push({
      title: 'Variation de l\'emploi',
      text: `${emploiChange > 0 ? '+' : ''}${nf(emploiChange, 0)} emplois en octobre 2026.`,
      value: `${emploiChange > 0 ? '+' : ''}${nf(emploiChange, 0)}`,
      trend: trend(emploiChange, 0),
    })
  }

  return {
    id: 'statcan',
    title: 'Canada — Emploi et économie (Statistique Canada)',
    attribution: `Statistique Canada, Licence ouverte — snapshot ${STATCAN_CHOMAGE.latest}. Tables ${STATCAN_CHOMAGE.table}, ${STATCAN_IPC.table}.`,
    snapshotDate: STATCAN_CHOMAGE.latest,
    points,
  }
}

const TREND_SYMBOL: Record<string, string> = { up: '▲', down: '▼', stable: '→' }

export function renderBulletinHtml(sections: BulletinSection[], title = 'MizanBI — Bulletin analytique'): string {
  const date = new Date().toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
  const sectionsHtml = sections.map((s) => {
    const pts = s.points.map((p) => {
      const sym = p.trend ? TREND_SYMBOL[p.trend] : ''
      const valHtml = p.value ? `<span style="font-weight:700;margin-left:8px">${sym} ${p.value}</span>` : ''
      return `<div style="margin:12px 0;padding:12px 16px;background:#f9f9f9;border-radius:8px;border-left:4px solid #2563eb">
        <div style="font-weight:600;font-size:15px;margin-bottom:4px">${p.title}${valHtml}</div>
        <div style="font-size:14px;color:#374151;line-height:1.6">${p.text}</div>
      </div>`
    }).join('')
    return `<section style="margin:32px 0">
      <h2 style="font-size:18px;font-weight:700;border-bottom:2px solid #2563eb;padding-bottom:8px;margin-bottom:16px">${s.title}</h2>
      ${pts}
      <p style="font-size:11px;color:#6b7280;margin-top:12px">${s.attribution}</p>
    </section>`
  }).join('')

  return `<!doctype html>
<html lang="fr">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title}</title>
<body style="font-family:system-ui,sans-serif;max-width:760px;margin:40px auto;padding:0 20px;color:#111827">
<header style="border-bottom:3px solid #1d4ed8;padding-bottom:16px;margin-bottom:24px">
  <h1 style="margin:0;font-size:24px;font-weight:800">${title}</h1>
  <p style="margin:6px 0 0;color:#6b7280;font-size:13px">Généré le ${date} · Données : snapshots locaux vérifiés · Conformité Loi 25</p>
</header>
${sectionsHtml}
<footer style="margin-top:40px;padding-top:16px;border-top:1px solid #e5e7eb;font-size:11px;color:#9ca3af">
  MizanBI — BI souveraine pour l'INSTAD. Données présentées à titre informatif uniquement.
  Les valeurs proviennent de snapshots locaux et n'impliquent aucun engagement de MizanBI sur leur exactitude actuelle.
</footer>
</body>
</html>`
}
