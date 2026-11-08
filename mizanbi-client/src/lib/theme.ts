// P-028 — Bibliothèque de thèmes, pilotée par les données et la cartographie.
// Projet à vocation commerciale : l'utilisateur choisit son thème, et le thème
// « prend vie » avec les données — la rampe choroplèthe, l'accent du dashboard
// et l'intensité des KPI se calculent à partir des valeurs affichées DANS le
// thème choisi. Changer de thème ne change JAMAIS les chiffres, que les couleurs.
// - Auto (par défaut) : le thème suit le jeu de données (Djibouti = Teal/Ocre,
//   Canada = Violet/Vert, accueil = Violet/Vert neutre). Dès que l'utilisateur
//   choisit un thème, son choix prime et est mémorisé (localStorage).
// - Aucune couleur de carte n'est codée en dur par région : colorForValue()
//   calcule la couleur à partir de la valeur et d'une échelle construite sur
//   les données affichées (min/max réels + quartiles).
// - Accessibilité : la couleur seule n'informe jamais (chaque zone porte son
//   nom et sa valeur, légende avec valeurs numériques) ; textOnFill() choisit
//   le texte blanc ou sombre selon la clarté réelle du remplissage, ce qui
//   vaut pour les 7 thèmes, thème clair compris.

export type ThemeId =
  | 'violet-green' // 1) Violet / Vert — thème actuel, par défaut
  | 'teal-ochre' // 2) Teal / Ocre — Djibouti
  | 'ocean' // 3) Océan — bleus
  | 'forest' // 4) Forêt — verts profonds
  | 'sunset' // 5) Coucher de soleil — ambre / corail
  | 'plum-rose' // 6) Prune / Rose
  | 'light' // 7) Clair — fond clair, démo institutionnelle

export type DatasetId = 'neutral' | 'djibouti' | 'canada'
export type ThemeMode = 'auto' | ThemeId
export type IndicatorId = 'unemployment' | 'population' | 'cpi' | 'poverty'

export const THEME_MODE_KEY = 'mizan_theme_mode'

export interface ThemeDef {
  id: ThemeId
  label: string
  /** Pastilles du sélecteur : [brand, accent]. */
  swatch: [string, string]
  /** Variables CSS appliquées sur :root (voir index.css). */
  vars: Record<string, string>
  /** Remplissage choroplèthe : bas → milieu → haut (oklch). */
  mapLow: string
  mapMid: string
  mapHigh: string
  /** Couleur des barres / lignes par défaut. */
  chart: string
  /** Seuil d'alerte affiché sur la légende (ex. 25 % Djibouti, 6,7 % Canada). */
  alertThreshold: number | null
  alertLabel: string
}

const VIOLET_GREEN: ThemeDef = {
  id: 'violet-green',
  label: 'Violet / Vert',
  swatch: ['oklch(65% 0.22 265)', 'oklch(68% 0.18 155)'],
  vars: {
    '--bg': '#070711', '--surface': 'oklch(13% 0.025 265 / 0.85)', '--surface-solid': 'oklch(17% 0.04 265)',
    '--border': 'oklch(25% 0.04 265 / 0.6)', '--brand': 'oklch(65% 0.22 265)', '--brand-hover': 'oklch(70% 0.22 265)',
    '--accent': 'oklch(68% 0.18 155)', '--accent-soft': 'oklch(80% 0.17 155)',
    '--warning': 'oklch(72% 0.19 55)', '--danger': 'oklch(58% 0.22 25)',
    '--text': '#f0f0fa', '--muted': 'oklch(70% 0.03 265)', '--muted-2': 'oklch(62% 0.03 265)',
    '--glow-1': 'oklch(35% 0.18 265 / 0.55)', '--glow-2': 'oklch(40% 0.14 155 / 0.28)', '--glow-3': 'oklch(32% 0.16 295 / 0.45)',
  },
  mapLow: 'oklch(34% 0.14 265)', mapMid: 'oklch(50% 0.16 200)', mapHigh: 'oklch(64% 0.18 155)',
  chart: '#34d399', alertThreshold: 6.7, alertLabel: 'Référence nationale : 6,7 % (oct. 2026, réel)',
}

const TEAL_OCHRE: ThemeDef = {
  id: 'teal-ochre',
  label: 'Teal / Ocre — Djibouti',
  swatch: ['oklch(62% 0.16 190)', 'oklch(72% 0.18 55)'],
  vars: {
    '--bg': '#08110f', '--surface': 'oklch(14% 0.03 180 / 0.85)', '--surface-solid': 'oklch(18% 0.045 180)',
    '--border': 'oklch(28% 0.04 180 / 0.6)', '--brand': 'oklch(62% 0.16 190)', '--brand-hover': 'oklch(68% 0.16 190)',
    '--accent': 'oklch(72% 0.18 55)', '--accent-soft': 'oklch(82% 0.15 65)',
    '--warning': 'oklch(72% 0.19 55)', '--danger': 'oklch(58% 0.22 25)',
    '--text': '#f2f5f0', '--muted': 'oklch(72% 0.03 180)', '--muted-2': 'oklch(64% 0.03 180)',
    '--glow-1': 'oklch(35% 0.14 190 / 0.55)', '--glow-2': 'oklch(40% 0.13 55 / 0.28)', '--glow-3': 'oklch(32% 0.12 160 / 0.45)',
  },
  mapLow: 'oklch(38% 0.12 190)', mapMid: 'oklch(52% 0.14 120)', mapHigh: 'oklch(58% 0.2 25)',
  chart: '#2dd4bf', alertThreshold: 25, alertLabel: 'Seuil d’alerte chômage : 25 % (démo, 2024)',
}

const OCEAN: ThemeDef = {
  id: 'ocean',
  label: 'Océan',
  swatch: ['oklch(60% 0.18 240)', 'oklch(68% 0.15 195)'],
  vars: {
    '--bg': '#060d18', '--surface': 'oklch(13% 0.03 240 / 0.85)', '--surface-solid': 'oklch(17% 0.045 240)',
    '--border': 'oklch(26% 0.05 240 / 0.6)', '--brand': 'oklch(60% 0.18 240)', '--brand-hover': 'oklch(66% 0.18 240)',
    '--accent': 'oklch(68% 0.15 195)', '--accent-soft': 'oklch(80% 0.14 195)',
    '--warning': 'oklch(72% 0.19 55)', '--danger': 'oklch(58% 0.22 25)',
    '--text': '#eef3fb', '--muted': 'oklch(72% 0.03 240)', '--muted-2': 'oklch(64% 0.03 240)',
    '--glow-1': 'oklch(35% 0.16 240 / 0.55)', '--glow-2': 'oklch(40% 0.13 195 / 0.3)', '--glow-3': 'oklch(32% 0.14 265 / 0.45)',
  },
  mapLow: 'oklch(36% 0.13 245)', mapMid: 'oklch(52% 0.16 225)', mapHigh: 'oklch(66% 0.16 195)',
  chart: '#38bdf8', alertThreshold: null, alertLabel: '',
}

const FOREST: ThemeDef = {
  id: 'forest',
  label: 'Forêt',
  swatch: ['oklch(55% 0.16 150)', 'oklch(70% 0.18 130)'],
  vars: {
    '--bg': '#071009', '--surface': 'oklch(13% 0.03 150 / 0.85)', '--surface-solid': 'oklch(17% 0.045 150)',
    '--border': 'oklch(26% 0.05 150 / 0.6)', '--brand': 'oklch(55% 0.16 150)', '--brand-hover': 'oklch(62% 0.16 150)',
    '--accent': 'oklch(70% 0.18 130)', '--accent-soft': 'oklch(82% 0.16 130)',
    '--warning': 'oklch(72% 0.19 55)', '--danger': 'oklch(58% 0.22 25)',
    '--text': '#eef7f0', '--muted': 'oklch(72% 0.03 150)', '--muted-2': 'oklch(64% 0.03 150)',
    '--glow-1': 'oklch(32% 0.14 150 / 0.55)', '--glow-2': 'oklch(38% 0.13 130 / 0.3)', '--glow-3': 'oklch(30% 0.12 180 / 0.45)',
  },
  mapLow: 'oklch(32% 0.11 155)', mapMid: 'oklch(48% 0.15 145)', mapHigh: 'oklch(64% 0.18 125)',
  chart: '#4ade80', alertThreshold: null, alertLabel: '',
}

const SUNSET: ThemeDef = {
  id: 'sunset',
  label: 'Coucher de soleil',
  swatch: ['oklch(65% 0.2 55)', 'oklch(62% 0.22 25)'],
  vars: {
    '--bg': '#120a08', '--surface': 'oklch(14% 0.03 35 / 0.85)', '--surface-solid': 'oklch(18% 0.045 35)',
    '--border': 'oklch(28% 0.05 35 / 0.6)', '--brand': 'oklch(65% 0.2 55)', '--brand-hover': 'oklch(70% 0.2 55)',
    '--accent': 'oklch(62% 0.22 25)', '--accent-soft': 'oklch(78% 0.18 35)',
    '--warning': 'oklch(72% 0.19 55)', '--danger': 'oklch(55% 0.22 15)',
    '--text': '#fbf1ea', '--muted': 'oklch(72% 0.03 35)', '--muted-2': 'oklch(64% 0.03 35)',
    '--glow-1': 'oklch(38% 0.16 45 / 0.55)', '--glow-2': 'oklch(40% 0.15 20 / 0.3)', '--glow-3': 'oklch(32% 0.13 320 / 0.45)',
  },
  mapLow: 'oklch(40% 0.14 60)', mapMid: 'oklch(55% 0.18 40)', mapHigh: 'oklch(60% 0.2 20)',
  chart: '#fb923c', alertThreshold: null, alertLabel: '',
}

const PLUM_ROSE: ThemeDef = {
  id: 'plum-rose',
  label: 'Prune / Rose',
  swatch: ['oklch(60% 0.2 320)', 'oklch(68% 0.18 10)'],
  vars: {
    '--bg': '#110710', '--surface': 'oklch(13% 0.03 320 / 0.85)', '--surface-solid': 'oklch(17% 0.045 320)',
    '--border': 'oklch(26% 0.05 320 / 0.6)', '--brand': 'oklch(60% 0.2 320)', '--brand-hover': 'oklch(66% 0.2 320)',
    '--accent': 'oklch(68% 0.18 10)', '--accent-soft': 'oklch(80% 0.16 10)',
    '--warning': 'oklch(72% 0.19 55)', '--danger': 'oklch(58% 0.22 25)',
    '--text': '#fbf0f6', '--muted': 'oklch(72% 0.03 320)', '--muted-2': 'oklch(64% 0.03 320)',
    '--glow-1': 'oklch(35% 0.16 320 / 0.55)', '--glow-2': 'oklch(40% 0.14 10 / 0.3)', '--glow-3': 'oklch(32% 0.14 265 / 0.45)',
  },
  mapLow: 'oklch(36% 0.14 320)', mapMid: 'oklch(52% 0.16 340)', mapHigh: 'oklch(62% 0.18 5)',
  chart: '#f472b6', alertThreshold: null, alertLabel: '',
}

const LIGHT: ThemeDef = {
  id: 'light',
  label: 'Clair — démo institutionnelle',
  swatch: ['oklch(50% 0.22 265)', 'oklch(48% 0.16 155)'],
  vars: {
    '--bg': '#f4f2ee', '--surface': 'oklch(99% 0.005 265 / 0.9)', '--surface-solid': '#ffffff',
    '--border': 'oklch(82% 0.02 265 / 0.8)', '--brand': 'oklch(50% 0.22 265)', '--brand-hover': 'oklch(45% 0.22 265)',
    '--accent': 'oklch(48% 0.16 155)', '--accent-soft': 'oklch(42% 0.15 155)',
    '--warning': 'oklch(55% 0.18 55)', '--danger': 'oklch(48% 0.2 25)',
    '--text': '#171724', '--muted': 'oklch(45% 0.02 265)', '--muted-2': 'oklch(38% 0.02 265)',
    '--glow-1': 'oklch(85% 0.1 265 / 0.6)', '--glow-2': 'oklch(88% 0.08 155 / 0.5)', '--glow-3': 'oklch(85% 0.08 295 / 0.5)',
  },
  mapLow: 'oklch(72% 0.1 265)', mapMid: 'oklch(55% 0.16 230)', mapHigh: 'oklch(40% 0.18 155)',
  chart: '#059669', alertThreshold: null, alertLabel: '',
}

export const THEMES: Record<ThemeId, ThemeDef> = {
  'violet-green': VIOLET_GREEN,
  'teal-ochre': TEAL_OCHRE,
  ocean: OCEAN,
  forest: FOREST,
  sunset: SUNSET,
  'plum-rose': PLUM_ROSE,
  light: LIGHT,
}

/** Ordre d'affichage du sélecteur (pastilles + noms). */
export const THEME_LIST: ThemeDef[] = [
  VIOLET_GREEN, TEAL_OCHRE, OCEAN, FOREST, SUNSET, PLUM_ROSE, LIGHT,
]

/** Thème d'un jeu de données en mode Auto. */
export const AUTO_THEME: Record<DatasetId, ThemeId> = {
  neutral: 'violet-green',
  djibouti: 'teal-ochre',
  canada: 'violet-green',
}

/** Accent d'indicateur : change avec l'indicateur, dans la palette du thème. */
export function indicatorAccent(theme: ThemeDef, indicator: IndicatorId): string {
  switch (indicator) {
    case 'unemployment': return theme.vars['--danger'] ?? theme.vars['--accent']
    case 'poverty': return theme.vars['--warning'] ?? theme.vars['--accent']
    case 'cpi': return theme.vars['--warning'] ?? theme.vars['--accent']
    case 'population': return theme.vars['--brand']
    default: return theme.vars['--accent']
  }
}

/** Jeu de données d'une page : l'accueil est neutre, Canada est Canada, le reste Djibouti. */
export function datasetForPage(page: string): DatasetId {
  if (page === 'canada' || page === 'canadanat') return 'canada'
  if (page === 'home') return 'neutral'
  return 'djibouti'
}

/** Mode Auto = suit la page ; choix manuel = prime sur la page. */
export function resolveTheme(mode: ThemeMode, page: string): ThemeId {
  if (mode === 'auto') return AUTO_THEME[datasetForPage(page)]
  return mode
}

/** Applique un thème : variables CSS sur :root + attribut data-theme, sans rechargement. */
export function applyTheme(themeId: ThemeId, indicator: IndicatorId = 'unemployment'): ThemeDef {
  const theme = THEMES[themeId]
  const root = document.documentElement
  root.dataset.theme = themeId
  for (const [k, v] of Object.entries(theme.vars)) root.style.setProperty(k, v)
  root.style.setProperty('--map-low', theme.mapLow)
  root.style.setProperty('--map-mid', theme.mapMid)
  root.style.setProperty('--map-high', theme.mapHigh)
  root.style.setProperty('--indicator-accent', indicatorAccent(theme, indicator))
  root.style.setProperty('--chart', theme.chart)
  return theme
}

export function loadThemeMode(): ThemeMode {
  const v = localStorage.getItem(THEME_MODE_KEY)
  if (v === 'auto') return 'auto'
  if (v && v in THEMES) return v as ThemeId
  return 'auto'
}

/** Thème actuellement appliqué sur :root (posé par applyTheme). */
export function currentTheme(): ThemeDef {
  const id = document.documentElement.dataset.theme as ThemeId | undefined
  return (id && THEMES[id]) || THEMES['violet-green']
}

// --- Choroplèthe pilotée par les données ---

export interface ChoroplethScale {
  min: number
  max: number
  q1: number
  median: number
  q3: number
  low: string
  mid: string
  high: string
  unit: string
  /** Seuil d'alerte / référence à afficher sur la légende, si pertinent. */
  reference: number | null
  referenceLabel: string
}

/** Échelle calculée sur les valeurs affichées : min/max réels + quartiles. Aucun seuil codé en dur par région.
 * La référence (seuil d'alerte / valeur nationale) est propre au JEU DE DONNÉES,
 * pas au thème : elle se passe en option, sinon c'est celle du thème. */
export function scaleFor(values: number[], theme: ThemeDef, unit = '%', opts?: { reference?: number | null; referenceLabel?: string }): ChoroplethScale {
  const sorted = [...values].filter((v) => Number.isFinite(v)).sort((a, b) => a - b)
  const reference = opts?.reference !== undefined ? opts.reference : theme.alertThreshold
  const referenceLabel = opts?.referenceLabel ?? theme.alertLabel
  if (sorted.length === 0) return { min: 0, max: 1, q1: 0, median: 0.5, q3: 1, low: theme.mapLow, mid: theme.mapMid, high: theme.mapHigh, unit, reference, referenceLabel }
  const q = (p: number) => sorted[Math.min(sorted.length - 1, Math.floor(p * (sorted.length - 1)))]
  return {
    min: sorted[0], max: sorted[sorted.length - 1],
    q1: q(0.25), median: q(0.5), q3: q(0.75),
    low: theme.mapLow, mid: theme.mapMid, high: theme.mapHigh,
    unit, reference, referenceLabel,
  }
}

type Oklch = { l: number; c: number; h: number }

function parseOklch(s: string): Oklch | null {
  const m = s.match(/oklch\(\s*([\d.]+)%\s+([\d.]+)\s+([\d.]+)/)
  if (!m) return null
  return { l: Number(m[1]), c: Number(m[2]), h: Number(m[3]) }
}

function lerp(a: Oklch, b: Oklch, t: number): string {
  // Interpolation la plus courte sur la teinte (cercle 0–360).
  let dh = b.h - a.h
  if (dh > 180) dh -= 360
  if (dh < -180) dh += 360
  const l = a.l + (b.l - a.l) * t
  const c = a.c + (b.c - a.c) * t
  const h = ((a.h + dh * t) % 360 + 360) % 360
  return `oklch(${l.toFixed(1)}% ${c.toFixed(3)} ${h.toFixed(0)})`
}

/** Couleur d'une valeur sur l'échelle : bas → milieu (t < 0,5) → haut (t ≥ 0,5). */
export function colorForValue(value: number, scale: ChoroplethScale): string {
  const t = scale.max === scale.min ? 0.5 : Math.min(1, Math.max(0, (value - scale.min) / (scale.max - scale.min)))
  const low = parseOklch(scale.low)
  const mid = parseOklch(scale.mid)
  const high = parseOklch(scale.high)
  if (!low || !mid || !high) return scale.mid
  return t < 0.5 ? lerp(low, mid, t * 2) : lerp(mid, high, (t - 0.5) * 2)
}

/** Position normalisée d'une valeur sur l'échelle (0–1), pour les légendes. */
export function valueT(value: number, scale: ChoroplethScale): number {
  return scale.max === scale.min ? 0.5 : Math.min(1, Math.max(0, (value - scale.min) / (scale.max - scale.min)))
}

/**
 * Couleur de texte lisible sur un remplissage : sombre si le remplissage est
 * clair (clarté oklch > 58 %), blanc sinon. Vaut pour les 7 thèmes, thème
 * clair compris (sa rampe basse est claire : texte sombre sur les zones basses).
 */
export function textOnFill(value: number, scale: ChoroplethScale): string {
  const fill = parseOklch(colorForValue(value, scale))
  return fill && fill.l > 58 ? '#070711' : '#ffffff'
}
