"""MizanBI MCP server — expose dashboards, tile data and Q&A as MCP tools.

Usage (stdio, for Claude Code):
    python tools/run_mcp.py

Environment:
    SOVEREIGN_VIEWER_KEY   — API key to authenticate internal calls (default: viewer)
    SOVEREIGN_MCP_BASE_URL — Backend base URL (default: http://localhost:9001)
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

_BASE = os.environ.get("SOVEREIGN_MCP_BASE_URL", "http://localhost:9001").rstrip("/")
_KEY = os.environ.get("SOVEREIGN_VIEWER_KEY", "viewer")
_HEADERS = {"X-Api-Key": _KEY, "Content-Type": "application/json"}

mcp = FastMCP(
    "MizanBI",
    instructions=(
        "MizanBI est une plateforme BI conversationnelle pour les données "
        "statistiques de Djibouti et d'Afrique de l'Est (INSTAD). "
        "Utilisez list_dashboards pour découvrir les rapports disponibles, "
        "get_dashboard pour voir les tuiles d'un rapport, "
        "query_tile pour obtenir les données d'une tuile, "
        "et ask pour poser des questions en langage naturel sur les données."
    ),
)


def _get(path: str, params: dict | None = None) -> Any:
    r = httpx.get(f"{_BASE}{path}", headers=_HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def _post(path: str, body: dict) -> Any:
    r = httpx.post(f"{_BASE}{path}", headers=_HEADERS, json=body, timeout=60)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def list_dashboards() -> str:
    """Liste tous les dashboards disponibles avec leur titre, description et tags."""
    data = _get("/dashboards")
    items = data if isinstance(data, list) else data.get("items", [])
    rows = []
    for d in items:
        tags = ", ".join(d.get("tags", [])) or "—"
        rows.append(f"- **{d['id']}** : {d['title']} [{tags}]")
    if not rows:
        return "Aucun dashboard disponible."
    return "## Dashboards MizanBI\n\n" + "\n".join(rows)


@mcp.tool()
def get_dashboard(dashboard_id: str) -> str:
    """Retourne la structure complète d'un dashboard (tuiles, types, SQL).

    Args:
        dashboard_id: identifiant du dashboard (ex: instad-emploi-marche-travail)
    """
    d = _get(f"/dashboards/{dashboard_id}")
    tiles = d.get("tiles", [])
    lines = [f"# {d['title']}", f"*{d.get('description', '')}*", ""]
    for t in tiles:
        sql = f"\n  SQL: `{t['sql_pinned'][:80]}…`" if t.get("sql_pinned") else ""
        opts = json.dumps(t.get("options", {}), ensure_ascii=False) if t.get("options") else ""
        lines.append(f"- **{t['id']}** ({t['type']}) : {t['title']}{sql}")
        if opts and opts != "{}":
            lines.append(f"  Options: {opts}")
    return "\n".join(lines)


@mcp.tool()
def query_tile(dashboard_id: str, tile_id: str) -> str:
    """Exécute la requête SQL d'une tuile et retourne les données en markdown.

    Args:
        dashboard_id: identifiant du dashboard
        tile_id: identifiant de la tuile
    """
    data = _get(f"/dashboards/{dashboard_id}/tiles/{tile_id}/data")
    columns: list[str] = data.get("columns", [])
    rows: list[list] = data.get("rows", [])
    if not columns:
        return "Aucune donnée."

    # markdown table (max 50 rows)
    header = " | ".join(columns)
    sep = " | ".join(["---"] * len(columns))
    lines = [f"| {header} |", f"| {sep} |"]
    for row in rows[:50]:
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    if len(rows) > 50:
        lines.append(f"\n*…{len(rows) - 50} lignes supplémentaires*")
    return "\n".join(lines)


@mcp.tool()
def get_tile_insight(dashboard_id: str, tile_id: str) -> str:
    """Retourne l'insight IA généré pour une tuile.

    Args:
        dashboard_id: identifiant du dashboard
        tile_id: identifiant de la tuile
    """
    data = _get(f"/dashboards/{dashboard_id}/tiles/{tile_id}/insight")
    insight = data.get("insight", "")
    cached = data.get("cached", False)
    suffix = " *(depuis cache)*" if cached else ""
    return f"{insight}{suffix}" if insight else "Aucun insight disponible pour cette tuile."


@mcp.tool()
def ask(question: str, use_data_pipeline: bool = True) -> str:
    """Pose une question en langage naturel sur les données statistiques.

    Génère du SQL si nécessaire, exécute la requête et retourne une réponse
    structurée avec les données sous forme de tableau.

    Args:
        question: question en français, anglais ou arabe
        use_data_pipeline: True (défaut) pour tenter une requête SQL sur les données
    """
    body: dict = {"question": question, "use_data_pipeline": use_data_pipeline}
    resp = _post("/api/v1/chatbot", body)

    answer = resp.get("answer", "")
    sql = resp.get("sql", "")
    result_data = resp.get("data")
    confidence = resp.get("confidence", "")

    parts = [answer]
    if sql:
        parts.append(f"\n**SQL généré :**\n```sql\n{sql}\n```")
    if result_data:
        columns = result_data.get("columns", [])
        rows = result_data.get("rows", [])
        if columns and rows:
            header = " | ".join(columns)
            sep = " | ".join(["---"] * len(columns))
            table_lines = [f"| {header} |", f"| {sep} |"]
            for row in rows[:20]:
                table_lines.append("| " + " | ".join(str(v) for v in row) + " |")
            parts.append("\n**Données :**\n" + "\n".join(table_lines))
    if confidence:
        parts.append(f"\n*Confiance : {confidence}*")

    return "\n".join(parts)


@mcp.tool()
def list_tables() -> str:
    """Liste les tables de données chargées dans MizanBI (DuckDB)."""
    data = _get("/health")
    tables: list[str] = data.get("tables", [])
    if not tables:
        return "Aucune table chargée."
    return "## Tables disponibles\n\n" + "\n".join(f"- `{t}`" for t in tables)
