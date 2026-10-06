"""Tests du parser SemanticModel (model.py)."""
import textwrap
from pathlib import Path

import pytest
import yaml

from app.semantic.model import (
    ColumnInfo,
    JoinInfo,
    MetricInfo,
    SemanticModel,
    TableInfo,
    load_model,
    model_to_prompt_text,
)


# ── fixtures ────────────────────────────────────────────────────────────────

def _write_yaml(tmp_path: Path, content: dict) -> Path:
    p = tmp_path / "model.yaml"
    p.write_text(yaml.dump(content, allow_unicode=True), encoding="utf-8")
    return p


# ── load_model ───────────────────────────────────────────────────────────────

def test_load_model_missing_file(tmp_path):
    m = load_model(tmp_path / "nope.yaml")
    assert m.schema_version == "1"
    assert m.tables == []
    assert m.metrics == []


def test_load_model_empty_file(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("", encoding="utf-8")
    m = load_model(p)
    assert m.schema_version == "1"


def test_load_model_v2_tables(tmp_path):
    data = {
        "schema_version": "2",
        "tables": [
            {
                "name": "ventes_detail",
                "description": "Lignes de vente",
                "columns": [
                    {"name": "id_ligne", "type": "integer", "description": "PK"},
                    {"name": "montant_ht", "type": "float", "description": "Montant HT"},
                ],
            }
        ],
    }
    m = load_model(_write_yaml(tmp_path, data))
    assert m.schema_version == "2"
    assert len(m.tables) == 1
    t = m.tables[0]
    assert t.name == "ventes_detail"
    assert len(t.columns) == 2
    assert t.columns[0].name == "id_ligne"
    assert t.columns[1].type == "float"


def test_load_model_metrics(tmp_path):
    data = {
        "schema_version": "2",
        "metrics": [
            {
                "name": "chiffre d'affaires",
                "aliases": ["CA", "revenu"],
                "sql": "SUM(montant_ht)",
                "tables": ["ventes_detail"],
                "description": "CA total",
            }
        ],
        "tables": [],
    }
    m = load_model(_write_yaml(tmp_path, data))
    assert len(m.metrics) == 1
    me = m.metrics[0]
    assert me.name == "chiffre d'affaires"
    assert "CA" in me.aliases
    assert me.join_required is False


def test_load_model_metric_join_required(tmp_path):
    data = {
        "schema_version": "2",
        "metrics": [
            {
                "name": "marge brute",
                "aliases": [],
                "sql": "SUM(montant_ht - quantite * cout_unitaire)",
                "tables": ["ventes_detail", "produits"],
                "join_required": True,
            }
        ],
        "tables": [],
    }
    m = load_model(_write_yaml(tmp_path, data))
    assert m.metrics[0].join_required is True


def test_load_model_joins(tmp_path):
    data = {
        "schema_version": "2",
        "tables": [],
        "joins": [
            {
                "from_table": "ventes_detail",
                "to_table": "clients",
                "condition": "ventes_detail.id_client = clients.id_client",
                "type": "LEFT",
            }
        ],
    }
    m = load_model(_write_yaml(tmp_path, data))
    assert len(m.joins) == 1
    j = m.joins[0]
    assert j.from_table == "ventes_detail"
    assert j.on == "ventes_detail.id_client = clients.id_client"
    assert j.type == "LEFT"


def test_load_model_rules(tmp_path):
    data = {
        "schema_version": "2",
        "tables": [],
        "rules": ["Les montants sont en CAD.", "Utiliser date_vente pour les filtres."],
    }
    m = load_model(_write_yaml(tmp_path, data))
    assert len(m.rules) == 2
    assert "CAD" in m.rules[0]


def test_load_model_glossary_v1_compat(tmp_path):
    data = {
        "glossary": [
            {"terme": "chiffre d'affaires", "definition": "SUM(montant_ht)"}
        ]
    }
    m = load_model(_write_yaml(tmp_path, data))
    assert len(m.glossary) == 1
    assert m.glossary[0]["terme"] == "chiffre d'affaires"


def test_load_model_real_file():
    """Charge le fichier de production et vérifie les invariants."""
    m = load_model("semantic/model.yaml")
    assert m.schema_version == "2"
    assert len(m.tables) >= 5
    assert len(m.metrics) >= 5
    assert len(m.joins) >= 4
    assert len(m.rules) >= 8


# ── model_to_prompt_text ──────────────────────────────────────────────────────

def test_prompt_text_includes_metrics(tmp_path):
    data = {
        "schema_version": "2",
        "metrics": [{"name": "CA", "aliases": [], "sql": "SUM(montant_ht)", "tables": ["v"]}],
        "tables": [],
    }
    m = load_model(_write_yaml(tmp_path, data))
    text = model_to_prompt_text(m)
    assert "CA" in text
    assert "SUM(montant_ht)" in text


def test_prompt_text_includes_tables(tmp_path):
    data = {
        "schema_version": "2",
        "tables": [
            {
                "name": "ventes_detail",
                "description": "Lignes",
                "columns": [{"name": "montant_ht", "type": "float", "description": "Montant HT"}],
            }
        ],
    }
    m = load_model(_write_yaml(tmp_path, data))
    text = model_to_prompt_text(m)
    assert "ventes_detail" in text
    assert "montant_ht" in text


def test_prompt_text_includes_rules(tmp_path):
    data = {
        "schema_version": "2",
        "tables": [],
        "rules": ["Montants en CAD."],
    }
    m = load_model(_write_yaml(tmp_path, data))
    text = model_to_prompt_text(m)
    assert "CAD" in text


def test_prompt_text_empty_model():
    m = SemanticModel(schema_version="1")
    text = model_to_prompt_text(m)
    assert isinstance(text, str)


def test_prompt_text_glossary_fallback(tmp_path):
    data = {
        "glossary": [{"terme": "panier moyen", "definition": "SUM/COUNT commandes"}]
    }
    m = load_model(_write_yaml(tmp_path, data))
    text = model_to_prompt_text(m)
    assert "panier moyen" in text
