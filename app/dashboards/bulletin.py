"""Generate a self-contained HTML narrative bulletin from a dashboard."""
from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Optional

from app.dashboards.models import Dashboard
from app.dashboards.renderer import render_tile
from app.data.duckdb_store import DataStore

_CSS = """
body{font-family:system-ui,sans-serif;max-width:900px;margin:40px auto;
     color:#1a1a2e;padding:0 24px;line-height:1.6}
h1{font-size:1.6rem;color:#1e3a5f;border-bottom:2px solid #3b82f6;
   padding-bottom:10px;margin-bottom:4px}
h2{font-size:1.05rem;margin-top:32px;color:#1e3a5f;border-bottom:1px solid #e5e7eb;
   padding-bottom:4px}
table{width:100%;border-collapse:collapse;font-size:0.82rem;margin:10px 0}
th{background:#eff6ff;border:1px solid #bfdbfe;padding:7px 10px;text-align:left;
   font-weight:600}
td{border:1px solid #dbeafe;padding:5px 10px;font-variant-numeric:tabular-nums}
tr:nth-child(even) td{background:#f8fafc}
.insight{background:#ede9fe;border-left:3px solid #7c3aed;padding:8px 12px;
         border-radius:4px;font-size:0.83rem;color:#3730a3;margin:10px 0}
.ia{font-weight:700;font-size:0.68rem;letter-spacing:.06em;color:#7c3aed;
    margin-right:6px;vertical-align:middle}
.disclaimer{background:#fef9c3;border:1px solid #fbbf24;padding:12px 16px;
            border-radius:6px;font-size:0.79rem;color:#78350f;margin:20px 0}
.err{color:#dc2626;font-size:0.8rem}
.source-attr{font-size:0.72rem;color:#6b7280;margin:4px 0 12px;font-style:italic}
.source-attr::before{content:"Source : "}
footer{margin-top:48px;border-top:1px solid #e5e7eb;padding-top:12px;
       font-size:0.72rem;color:#9ca3af}
@media print{.disclaimer{border-color:#d1d5db}.insight{break-inside:avoid}}
"""

_MAX_ROWS = 20


def _table_html(columns: list[str], rows: list) -> str:
    if not columns or not rows:
        return '<p class="err">Aucune donnée disponible.</p>'
    ths = "".join(f"<th>{html.escape(c.replace('_', ' '))}</th>" for c in columns)
    trs = ""
    for row in rows[:_MAX_ROWS]:
        tds = "".join(
            f"<td>{html.escape(str(v) if v is not None else '—')}</td>"
            for v in row
        )
        trs += f"<tr>{tds}</tr>"
    if len(rows) > _MAX_ROWS:
        extra = len(rows) - _MAX_ROWS
        trs += (
            f"<tr><td colspan='{len(columns)}' "
            f"style='color:#9ca3af;text-align:center;font-style:italic'>"
            f"… {extra} ligne{'s' if extra > 1 else ''} supplémentaire{'s' if extra > 1 else ''}"
            f"</td></tr>"
        )
    return f"<table><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>"


def generate_bulletin_html(
    d: Dashboard,
    store: DataStore,
    cached_insights: Optional[dict[str, str]] = None,
) -> str:
    """Return a self-contained HTML bulletin for `d`.

    `cached_insights` maps tile_id → insight text; tiles not present get no
    IA section. Only tiles with sql_pinned are rendered.
    """
    if cached_insights is None:
        cached_insights = {}

    generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y à %H:%M UTC")
    title_esc = html.escape(d.title)

    sections: list[str] = []
    for tile in d.tiles:
        if not tile.sql_pinned:
            continue
        result = render_tile(tile, store)
        heading = html.escape(tile.title)
        if result.get("error"):
            sections.append(
                f"<h2>{heading}</h2>"
                f"<p class='err'>{html.escape(str(result['error']))}</p>"
            )
            continue
        table = _table_html(result["columns"], result["rows"])
        insight_text = cached_insights.get(tile.id, "")
        insight_block = (
            f'<div class="insight"><span class="ia">IA</span>{html.escape(insight_text)}</div>'
            if insight_text
            else ""
        )
        source_block = (
            f'<p class="source-attr">{html.escape(tile.source)}</p>'
            if tile.source
            else ""
        )
        sections.append(f"<h2>{heading}</h2>{table}{insight_block}{source_block}")

    body = "\n".join(sections) or "<p>Aucune tuile avec SQL disponible.</p>"

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title_esc}</title>
<style>{_CSS}</style>
</head>
<body>
<h1>{title_esc}</h1>
<p style="color:#6b7280;font-size:0.82rem;margin-top:4px">Généré le {generated_at}</p>
<div class="disclaimer">
  <strong>Avertissement :</strong> Ce bulletin est produit à titre informatif uniquement.
  Les données proviennent des sources statistiques référencées.
  Les analyses assistées par intelligence artificielle doivent être vérifiées
  par un professionnel avant tout usage officiel.
  Ce document ne constitue pas un avis juridique ou statistique officiel.
</div>
{body}
<footer>
  Produit par <strong>MizanBI</strong> &mdash; {title_esc} &mdash; {generated_at}
</footer>
</body>
</html>"""
