import type { Tile, TileData } from './api'

// ── CSV ───────────────────────────────────────────────────────────────────────

export function tileDataToCsv(title: string, data: TileData): string {
  const escape = (v: unknown): string => {
    const s = v === null || v === undefined ? '' : String(v)
    return s.includes(',') || s.includes('"') || s.includes('\n')
      ? `"${s.replace(/"/g, '""')}"`
      : s
  }
  const header = data.columns.map(escape).join(',')
  const rows = data.rows.map((row) => row.map(escape).join(','))
  return [header, ...rows].join('\r\n')
}

// ── Bulletin HTML ─────────────────────────────────────────────────────────────

function tileToHtmlBlock(tile: Tile): string {
  const data = tile.data
  if (!data) {
    return `<section class="tile"><h3>${tile.title}</h3><p class="empty">Aucune donnée</p></section>`
  }
  if (tile.type === 'kpi') {
    const val = data.rows[0]?.[0] ?? '—'
    return `<section class="tile tile-kpi"><h3>${tile.title}</h3><div class="kpi-val">${val}</div></section>`
  }
  const thead = `<tr>${data.columns.map((c) => `<th>${c}</th>`).join('')}</tr>`
  const tbody = data.rows
    .slice(0, 50)
    .map((row) => `<tr>${row.map((v) => `<td>${v === null || v === undefined ? '—' : v}</td>`).join('')}</tr>`)
    .join('')
  return `<section class="tile"><h3>${tile.title}</h3><table><thead>${thead}</thead><tbody>${tbody}</tbody></table></section>`
}

export function dashboardToBulletinHtml(dashTitle: string, tiles: Tile[]): string {
  const date = new Date().toLocaleDateString('fr-FR', { year: 'numeric', month: 'long', day: 'numeric' })
  const body = tiles.map(tileToHtmlBlock).join('\n')
  return `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>${dashTitle} — Bulletin</title>
<style>
  body{font-family:system-ui,sans-serif;max-width:900px;margin:40px auto;padding:0 24px;color:#111}
  h1{font-size:22px;margin-bottom:4px}
  .meta{color:#666;font-size:13px;margin-bottom:32px}
  .tile{margin-bottom:28px;border:1px solid #e2e8f0;border-radius:8px;padding:16px}
  .tile h3{margin:0 0 12px;font-size:15px;font-weight:600}
  .tile-kpi .kpi-val{font-size:36px;font-weight:700;color:#1a4a8c}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th{text-align:left;padding:6px 8px;background:#f8fafc;font-weight:600;border-bottom:2px solid #e2e8f0}
  td{padding:6px 8px;border-bottom:1px solid #f1f5f9}
  .empty{color:#999;font-style:italic}
  .footer{margin-top:40px;padding-top:16px;border-top:1px solid #e2e8f0;font-size:11px;color:#999}
</style>
</head>
<body>
<h1>${dashTitle}</h1>
<p class="meta">Bulletin généré le ${date} — MizanBI (données démo)</p>
${body}
<p class="footer">MizanBI — Outil d'aide à la décision. Les analyses produites sont indicatives. L'utilisateur reste responsable de ses décisions.</p>
</body>
</html>`
}

// ── Download trigger ──────────────────────────────────────────────────────────

export function triggerDownload(content: string, filename: string, mimeType: string, addBom = false): void {
  const bom = addBom ? '﻿' : ''
  const blob = new Blob([bom + content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
