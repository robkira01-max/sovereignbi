export interface TradeFlow {
  id: string
  from: [number, number]  // [lng, lat]
  to: [number, number]
  commodity: string
  tonnageK: number  // thousands of tonnes/year (synthetic UNCTAD-style data)
  color: string
  destination: string
  country: string
}

// Port de Djibouti: 11.582°N, 43.146°E
export const PORT_DJIBOUTI: [number, number] = [43.146, 11.582]

export const TRADE_FLOWS: TradeFlow[] = [
  {
    id: 'f1',
    from: PORT_DJIBOUTI,
    to: [38.737, 9.032],
    commodity: 'Céréales & denrées',
    tonnageK: 2800,
    color: '#f97316',
    destination: 'Addis-Abeba',
    country: 'Éthiopie',
  },
  {
    id: 'f2',
    from: PORT_DJIBOUTI,
    to: [41.862, 9.596],
    commodity: 'Carburant & énergie',
    tonnageK: 1900,
    color: '#ef4444',
    destination: 'Dire Dawa',
    country: 'Éthiopie',
  },
  {
    id: 'f3',
    from: PORT_DJIBOUTI,
    to: [39.475, 13.490],
    commodity: 'Engrais agricoles',
    tonnageK: 950,
    color: '#22c55e',
    destination: 'Mekele',
    country: 'Éthiopie',
  },
  {
    id: 'f4',
    from: PORT_DJIBOUTI,
    to: [39.634, 11.130],
    commodity: 'Équipements industriels',
    tonnageK: 620,
    color: '#3b82f6',
    destination: 'Dessie',
    country: 'Éthiopie',
  },
  {
    id: 'f5',
    from: PORT_DJIBOUTI,
    to: [37.456, 7.051],
    commodity: 'Biens de consommation',
    tonnageK: 480,
    color: '#a855f7',
    destination: 'Hawassa',
    country: 'Éthiopie',
  },
]

export const MAX_TONNAGE_K = Math.max(...TRADE_FLOWS.map(f => f.tonnageK))
