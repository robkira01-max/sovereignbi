// Données de démonstration — COHÉRENTES PARTOUT (validées dans le front-end mizanbi-2).
// Population totale = 1 030 000 = somme exacte des 6 régions.
// Chômage national pondéré = 23,5 % (somme pop × taux / 1 030 000 = 23,4999 %).
// ÉCART DOCUMENTÉ : le prototype Claude Design affichait 26,8 % et 1 062 000 habitants
// (Obock 33,2 %, Dikhil 31,5 %). Ces valeurs NE sont PAS reprises ici : elles
// contredisaient les totaux. Voir README.md, section « Données de démonstration ».

export interface Region {
  name: string
  iso: string
  population: number
  unemployment: number // %
  poverty?: number // % — démo
  density?: number // hab/km² — démo
}

export const REGIONS: Region[] = [
  { name: 'Djibouti-ville', iso: 'DJ-DJ', population: 745300, unemployment: 22.3, poverty: 18.4, density: 3726 },
  { name: 'Ali Sabieh', iso: 'DJ-AS', population: 91800, unemployment: 24.6, poverty: 31.2, density: 42 },
  { name: 'Dikhil', iso: 'DJ-DI', population: 72400, unemployment: 28.4, poverty: 38.7, density: 10 },
  { name: 'Tadjourah', iso: 'DJ-TA', population: 67100, unemployment: 27.1, poverty: 35.9, density: 9 },
  { name: 'Obock', iso: 'DJ-OB', population: 28500, unemployment: 29.1, poverty: 36.4, density: 6 },
  { name: 'Arta', iso: 'DJ-AR', population: 24900, unemployment: 25.0, poverty: 29.8, density: 14 },
]

export const TOTAL_POPULATION = REGIONS.reduce((a, r) => a + r.population, 0) // 1 030 000
export const WEIGHTED_UNEMPLOYMENT =
  Math.round((REGIONS.reduce((a, r) => a + r.population * r.unemployment, 0) / TOTAL_POPULATION) * 10) / 10 // 23,5

export const UNEMPLOYMENT_TREND = [
  { year: 2009, rate: 28.9 },
  { year: 2012, rate: 27.6 },
  { year: 2016, rate: 26.4 },
  { year: 2020, rate: 25.8 },
  { year: 2022, rate: 24.6 },
  { year: 2024, rate: 23.5 },
]

// Prévisions 2030 — projection indicative (tendance linéaire), reprise du prototype.
// Valeur 23,1 %, IC 20,5 – 26,0. À remplacer par un vrai modèle quand l'API le fournira.
export const FORECAST_2030 = { value: 23.1, ciLow: 20.5, ciHigh: 26.0 }

export const DEMO_TABLES = ['emploi_region', 'population_region', 'menages_2024', 'pauvrete_district']

// --- P-032 — Utilisateur de démonstration ---
// Robleh Hassan est l'utilisateur / propriétaire du projet. Aucun nom fictif
// du prototype ni de la maquette : le compte démo affiche Robleh Hassan,
// initiales RH, dans le Login et dans la topbar. Aucun email, mot de passe
// ni rôle inventé.
export const DEMO_USER = { name: 'Robleh Hassan', initials: 'RH' } as const

export interface DashboardTile {
  id: string
  type: 'kpi' | 'bar' | 'line' | 'pie' | 'table' | 'choropleth' | 'grid'
  title: string
  unit?: string
  delta?: number
  data: { columns: string[]; rows: (string | number)[][] }
}

export interface Dashboard {
  id: string
  title: string
  description: string
  tiles: DashboardTile[]
}

const regionRows = REGIONS.map((r) => [r.name, r.unemployment] as (string | number)[])

export const DEMO_DASHBOARDS: Dashboard[] = [
  {
    id: 'emploi-population',
    title: 'Emploi et population — Djibouti',
    description: '8 tuiles · Données : Démo',
    tiles: [
      { id: 'k1', type: 'kpi', title: 'Taux de chômage moyen', unit: '%', delta: -1.4, data: { columns: ['v'], rows: [[23.5]] } },
      { id: 'k2', type: 'kpi', title: 'Population (2024)', unit: 'habitants', delta: 2.1, data: { columns: ['v'], rows: [[1030000]] } },
      { id: 'b1', type: 'bar', title: 'Chômage par région (2024)', data: { columns: ['region', 'taux'], rows: regionRows } },
      { id: 'l1', type: 'line', title: 'Évolution du chômage', data: { columns: ['annee', 'taux'], rows: UNEMPLOYMENT_TREND.map((t) => [t.year, t.rate]) } },
      { id: 'p1', type: 'pie', title: "Répartition de l'emploi", data: { columns: ['secteur', 'part'], rows: [['Services', 62], ['Commerce', 18], ['Industrie', 12], ['Agriculture', 8]] } },
      { id: 'm1', type: 'choropleth', title: 'Chômage — carte des régions', data: { columns: ['region', 'taux'], rows: regionRows } },
      {
        id: 't1', type: 'table', title: 'Détail par région',
        data: { columns: ['region', 'population', 'taux_chomage_pct'], rows: REGIONS.map((r) => [r.name, r.population, r.unemployment]) },
      },
      {
        id: 'g1', type: 'grid', title: 'Tendances par région',
        data: { columns: ['region', 'annee', 'taux'], rows: REGIONS.flatMap((r) => [[r.name, 2016, +(r.unemployment + 2.9).toFixed(1)], [r.name, 2020, +(r.unemployment + 1.2).toFixed(1)], [r.name, 2024, r.unemployment]]) },
      },
    ],
  },
  {
    id: 'pauvrete-district',
    title: 'Pauvreté par district',
    description: '4 tuiles · Données : Démo',
    tiles: [
      { id: 'k1', type: 'kpi', title: 'Taux de pauvreté moyen', unit: '%', delta: -0.8, data: { columns: ['v'], rows: [[24.6]] } },
      { id: 'b1', type: 'bar', title: 'Pauvreté par région', data: { columns: ['region', 'taux'], rows: REGIONS.map((r) => [r.name, r.poverty ?? 0]) } },
      { id: 'l1', type: 'line', title: 'Évolution de la pauvreté', data: { columns: ['annee', 'taux'], rows: [[2009, 31.2], [2016, 28.4], [2020, 27.1], [2024, 24.6]] } },
      { id: 't1', type: 'table', title: 'Détail par région', data: { columns: ['region', 'pauvrete_pct', 'densite'], rows: REGIONS.map((r) => [r.name, r.poverty ?? 0, r.density ?? 0]) } },
    ],
  },
]

// --- Volet 2 — Cartographie SIG ---
// 11 quartiers de Djibouti-ville. DÉLIMITATIONS APPROXIMATIVES, à valider avec la mairie.
// Positions schématiques (grille) dans la carte SIG, pas des contours officiels.
export const QUARTIERS = [
  { name: 'Balbala', unemployment: 26.8, population: 198000 },
  { name: 'Arhiba', unemployment: 25.4, population: 86400 },
  { name: 'Ambouli', unemployment: 21.9, population: 73200 },
  { name: 'Centre-ville', unemployment: 19.8, population: 68400 },
  { name: 'Einguela', unemployment: 23.7, population: 52100 },
  { name: 'Quartier 1', unemployment: 24.2, population: 48300 },
  { name: 'Quartier 2', unemployment: 22.6, population: 41900 },
  { name: 'Quartier 3', unemployment: 25.9, population: 38600 },
  { name: 'Quartier 4', unemployment: 23.1, population: 34200 },
  { name: 'Quartier 5', unemployment: 27.3, population: 29800 },
  { name: 'Quartier 6', unemployment: 24.9, population: 23400 },
]

// Flux commerciaux Port de Djibouti → Éthiopie.
// CHOIX P-025 : valeurs ILLUSTRATIVES, masquées par défaut dans le SIG.
// Les vraies valeurs viennent du connecteur UN Comtrade Plus (P-020) quand la clé
// est configurée côté backend uniquement (COMTRADE_API_KEY, jamais dans le front).
// Ne pas les présenter comme des données réelles dans une démo institutionnelle.
export const TRADE_FLOWS = [
  { to: 'Addis-Abeba', value: 412, share: 38 },
  { to: 'Dire Dawa', value: 238, share: 22 },
  { to: 'Mekele', value: 151, share: 14 },
  { to: 'Dessie', value: 140, share: 13 },
  { to: 'Hawassa', value: 141, share: 13 },
]

// --- P-022 / P-023 / P-024 : agent, preuve de confiance, bulletins ---
// Provenance unique des chiffres démo, affichée sur chaque tuile et chaque réponse.
export const PROVENANCE = {
  unemployment: { table: 'emploi_region', year: 2024, sql: 'SELECT region, AVG(taux_chomage_pct) AS taux FROM emploi_region GROUP BY region ORDER BY taux DESC LIMIT 6' },
  population: { table: 'population_region', year: 2024, sql: 'SELECT region, SUM(population) FROM population_region GROUP BY region' },
  poverty: { table: 'pauvrete_district', year: 2024, sql: 'SELECT region, taux_pauvrete_pct FROM pauvrete_district' },
} as const

// Alerte démo (P-022) : seuil 25 % dépassé. Valeurs démo, à remplacer par l'API.
export const DEMO_ALERT = {
  title: 'Obock reste la région la plus touchée',
  detail: 'Chômage 29,1 % à Obock (seuil 25 % dépassé), contre 23,5 % en moyenne nationale pondérée (démo, 2024).',
}

// Bulletin narratif hebdomadaire démo (P-024) — semaine du 3 novembre 2026.
export const WEEKLY_BULLETIN = {
  week: 'Semaine du 3 novembre 2026',
  schedule: 'Chaque lundi, sans envoi réel en mode démo',
  points: [
    { title: 'Le chômage recule lentement', text: 'Taux national pondéré 23,5 % en 2024 (démo), contre 28,9 % en 2009. La baisse est régulière mais lente : −5,4 points en 15 ans.' },
    { title: 'Obock et Dikhil restent au-dessus de 28 %', text: 'Obock 29,1 % et Dikhil 28,4 % dépassent le seuil de 25 %. Djibouti-ville, la plus peuplée (745 300 hab.), est à 22,3 %.' },
    { title: 'Population concentrée dans la capitale', text: '1 030 000 habitants au total (démo) ; 745 300 vivent à Djibouti-ville, soit plus de 7 habitants sur 10.' },
  ],
}

export const fmt = (v: number | string): string => {
  if (typeof v === 'number') {
    return Number.isInteger(v) ? v.toLocaleString('fr-FR') : (Math.round(v * 100) / 100).toLocaleString('fr-FR')
  }
  return String(v ?? '')
}

export const fmtPct = (v: number): string => `${String(v).replace('.', ',')} %`
