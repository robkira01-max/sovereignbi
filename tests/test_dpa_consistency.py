"""Le DPA ne doit citer que des réglages et des routes qui existent dans le code (un contrat qui promet une
variable inexistante est faux : cas réel, `KIMI_RPM`, retiré après vérification)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DPA = (ROOT / "docs/legal/dpa-fr.md").read_text(encoding="utf-8")
INCIDENT_DOC = (ROOT / "docs/incident-procedure.md").read_text(encoding="utf-8")


def _source() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "app").rglob("*.py")) + (ROOT / ".env.example").read_text(encoding="utf-8")


def test_every_setting_named_in_the_dpa_exists_in_the_code():
    names = set(re.findall(r"\b(?:KIMI_[A-Z_]+|SOVEREIGN_[A-Z_]+|LLM_PROVIDER|OLLAMA_URL|SMTP_[A-Z]+)\b", DPA + INCIDENT_DOC))
    assert {"SOVEREIGN_AI_STRICT", "KIMI_BASE_URL", "KIMI_MODEL", "LLM_PROVIDER", "OLLAMA_URL"} <= names     # l'annexe D est bien lue
    src = _source()
    missing = sorted(n for n in names if n not in src)
    assert not missing, f"réglages cités dans le DPA mais absents du code : {missing}"


def _norm(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "{}", path.split("?")[0].rstrip("/"))


def test_every_route_named_in_the_dpa_exists():
    from app.main import app

    paths = app.openapi()["paths"]                      # source fiable : les routes imbriquées n'apparaissent pas toutes dans app.routes
    routes = {(m.upper(), _norm(path)) for path, ops in paths.items() for m in ops if m in {"get", "post", "put", "delete"}}
    assert len(routes) > 100, "OpenAPI incomplet : le test ne vérifierait rien"
    cited = re.findall(r"`(GET|POST|PUT|DELETE)\s+(/[^`\s]*)`", DPA + INCIDENT_DOC)
    cited += [(m, p) for m, p in re.findall(r"\b(GET|POST|PUT|DELETE)\s+(/[A-Za-z0-9_/{}-]+)", DPA + INCIDENT_DOC)]
    assert ("GET", "/compliance/notice") in {(m, _norm(p)) for m, p in cited}
    missing = sorted({(m, _norm(p)) for m, p in cited} - routes)
    assert not missing, f"routes citées dans le DPA mais inexistantes : {missing}"


def test_annex_d_covers_the_three_configurations_and_every_data_flow():
    assert "Annexe D" in DPA
    for needle in ("A — modèle local", "B — externe, mode strict", "C — externe, mode strict désactivé"):
        assert needle in DPA
    for flow in ("Question de l'utilisateur", "3 lignes d'exemple par table", "Lignes de résultat", "Extraits de documents",
                 "insights", "Historique du chat", "Valeurs citées dans les messages d'erreur"):
        assert flow in DPA, flow


def test_annex_d_never_pretends_to_know_the_providers_commitments():
    d3 = DPA[DPA.index("#### D.3"):DPA.index("#### D.4")]
    assert d3.count("[À COMPLÉTER]") >= 14                    # chaque engagement reste à obtenir par écrit
    for claim in ("ne sert pas", "conserve", "garantit"):
        assert claim not in d3.replace("ne servent pas à entraîner", "")


def test_the_dpa_is_still_marked_as_an_unvalidated_draft():
    assert "BROUILLON" in DPA and "non validé par un juriste" in DPA
