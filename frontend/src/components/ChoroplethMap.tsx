import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'
import type { EChartsType } from 'echarts'
import djiGeojson from '../data/dji_adm1.geojson'

// GeoJSON region names → INSTAD table region names
const GEO_TO_INSTAD: Record<string, string> = {
  'Djibouti': 'Djibouti-ville',
  'Ali Sabieh': 'Ali Sabieh',
  'Arta': 'Arta',
  'Dikhil': 'Dikhil',
  'Tadjourah': 'Tadjourah',
  'Obock': 'Obock',
}
const INSTAD_TO_GEO = Object.fromEntries(
  Object.entries(GEO_TO_INSTAD).map(([geo, ins]) => [ins, geo])
)

interface Props {
  data: { columns: string[]; rows: unknown[][] }
  title: string
  unit?: string
  colorScheme?: 'blue' | 'green' | 'red' | 'orange'
}

const PALETTES: Record<string, [string, string]> = {
  blue:   ['#dbeafe', '#1a4a8c'],
  green:  ['#d1fae5', '#065f46'],
  red:    ['#fee2e2', '#991b1b'],
  orange: ['#ffedd5', '#9a3412'],
}

export function ChoroplethMap({ data, title, unit = '', colorScheme = 'blue' }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const chartRef = useRef<EChartsType | null>(null)

  // Derive column names at component scope (needed in JSX and in effect)
  const valueCol = data.columns[1] ?? ''

  useEffect(() => {
    if (!ref.current) return

    // Register map once
    if (!echarts.getMap('djibouti-adm1')) {
      echarts.registerMap('djibouti-adm1', djiGeojson as never)
    }

    const chart = echarts.init(ref.current, null, { renderer: 'svg' })
    chartRef.current = chart

    // Build value map: geoName → value
    const regionCol = data.columns[0]
    const regionIdx = data.columns.indexOf(regionCol)
    const valueIdx = data.columns.indexOf(valueCol)

    const mapData = data.rows.map(row => {
      const instadName = String(row[regionIdx] ?? '')
      const geoName = INSTAD_TO_GEO[instadName] ?? instadName
      const val = Number(row[valueIdx] ?? 0)
      return { name: geoName, value: val }
    })

    const values = mapData.map(d => d.value).filter(v => !isNaN(v))
    const minVal = Math.min(...values)
    const maxVal = Math.max(...values)
    const [colorLow, colorHigh] = PALETTES[colorScheme]

    chart.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: (params: { name: string; value: number }) => {
          const instad = GEO_TO_INSTAD[params.name] ?? params.name
          const val = isNaN(params.value) ? '—' : `${params.value.toFixed(1)} ${unit}`
          return `<b>${instad}</b><br/>${valueCol.replace(/_/g, ' ')}: ${val}`
        },
      },
      visualMap: {
        min: minVal,
        max: maxVal,
        text: [String(maxVal.toFixed(0)), String(minVal.toFixed(0))],
        calculable: true,
        orient: 'vertical',
        left: 'right',
        bottom: '15%',
        inRange: { color: [colorLow, colorHigh] },
        textStyle: { color: 'var(--text, #ccc)', fontSize: 10 },
      },
      series: [{
        type: 'map',
        map: 'djibouti-adm1',
        data: mapData,
        nameProperty: 'shapeName',
        label: {
          show: true,
          fontSize: 9,
          color: '#fff',
          formatter: (p: { name: string }) => GEO_TO_INSTAD[p.name] ?? p.name,
        },
        emphasis: {
          label: { show: true, fontSize: 10, fontWeight: 'bold' },
          itemStyle: { areaColor: '#f59e0b' },
        },
        itemStyle: {
          borderColor: '#ffffff',
          borderWidth: 1,
        },
        aspectScale: 1,
        layoutCenter: ['50%', '50%'],
        layoutSize: '95%',
      }],
    })

    const resize = () => chart.resize()
    window.addEventListener('resize', resize)
    return () => {
      window.removeEventListener('resize', resize)
      chart.dispose()
    }
  }, [data, colorScheme, unit])

  return (
    <div data-testid="tile-map" style={{ width: '100%' }}>
      <div ref={ref} style={{ width: '100%', height: 320 }} />
      {unit && (
        <div style={{ textAlign: 'center', fontSize: '0.7rem', color: 'var(--muted)', marginTop: 4 }}>
          {valueCol?.replace(/_/g, ' ')} — {unit}
        </div>
      )}
    </div>
  )
}
