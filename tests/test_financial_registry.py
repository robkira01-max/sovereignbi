"""P-073 : registre de formules versionnées (YAML)."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.financial.registry import DEFAULT_DIR, RegistryError, load_registry

V1 = {
    "version": 1, "label": "Taux", "expression": "a / b * 100", "result_unit": "%", "precision": 2,
    "rounding": "ROUND_HALF_UP", "on_zero_division": "error",
    "variables": {"a": {"label": "A", "unit": "monnaie"}, "b": {"label": "B", "unit": "monnaie"}},
}


def write(d: Path, code="TST001", versions=None, **extra):
    data = {"code": code, "family": "test", "versions": versions if versions is not None else [dict(V1)], **extra}
    (d / f"{code.lower()}.yaml").write_text(yaml.safe_dump(data, allow_unicode=True))
    return d


@pytest.fixture()
def d(tmp_path):
    return tmp_path


def test_shipped_library_loads_with_11_formulas_8_budget_3_revenue():
    reg = load_registry(DEFAULT_DIR)
    codes = reg.codes()
    assert len(codes) == 11
    assert sum(c.startswith("BUD") for c in codes) == 8 and sum(c.startswith("REC") for c in codes) == 3
    hashes = {reg.get(c).definition_hash for c in codes}
    assert len(hashes) == 11                                  # chaque définition est distincte


def test_every_shipped_formula_declares_explicit_zero_division_and_rounding():
    reg = load_registry(DEFAULT_DIR)
    for code in reg.codes():
        fv = reg.get(code)
        assert fv.on_zero_division in ("error", "null") and fv.rounding.startswith("ROUND_")
        assert all(not v.allow_negative for v in fv.variables)    # montants de base jamais négatifs par défaut


def test_adding_a_version_keeps_the_old_one_available(d):
    v2 = {**V1, "version": 2, "expression": "a / b * 1000", "result_unit": "‰"}
    write(d, versions=[dict(V1), v2])
    reg = load_registry(d)
    assert reg.get("TST001").version == 2                      # dernière par défaut
    assert reg.get("TST001", 1).expression == "a / b * 100"    # l'ancienne reste consultable
    assert reg.get("TST001", 1).definition_hash != reg.get("TST001", 2).definition_hash


def test_hash_covers_calculation_behaviour_but_not_wording(d):
    write(d)
    base = load_registry(d).get("TST001").definition_hash
    write(d, versions=[{**V1, "label": "Autre libellé", "description": "texte", "interpretation": "x"}])
    assert load_registry(d).get("TST001").definition_hash == base
    for change in ({"expression": "a / b * 10"}, {"precision": 3}, {"rounding": "ROUND_DOWN"},
                   {"on_zero_division": "null"}, {"result_unit": "pct"}):
        write(d, versions=[{**V1, **change}])
        assert load_registry(d).get("TST001").definition_hash != base, change


def test_ruleset_version_is_deterministic_and_depends_on_definitions(d):
    write(d)
    reg = load_registry(d)
    fv = reg.get("TST001")
    assert reg.ruleset_version([fv]) == reg.ruleset_version([fv])
    write(d, versions=[{**V1, "expression": "a / b"}])
    reg2 = load_registry(d)
    assert reg2.ruleset_version([reg2.get("TST001")]) != reg.ruleset_version([fv])


@pytest.mark.parametrize("mutate,message", [
    (lambda v: v[0].update(version=2), "sans trou"),                       # ne commence pas à 1
    (lambda v: v.append({**V1, "version": 3}), "sans trou"),               # trou 1 -> 3
    (lambda v: v[0].update(rounding="ROUND_MAGIC"), "rounding"),
    (lambda v: v[0].update(on_zero_division="ignore"), "on_zero_division"),
    (lambda v: v[0].update(precision=-1), "precision"),
    (lambda v: v[0].update(precision=99), "precision"),
    (lambda v: v[0].update(precision=True), "precision"),
    (lambda v: v[0].update(expression="a / c"), "non déclarée"),
    (lambda v: v[0].update(expression="a * 2"), "non utilisée"),
    (lambda v: v[0].update(expression="__import__('os')"), "non autorisé|non déclarée"),
    (lambda v: v[0]["variables"]["a"].update(required=False), "valeur par défaut"),
    (lambda v: v[0]["variables"]["a"].update(default="1"), "par défaut"),            # défaut + obligatoire
    (lambda v: v[0]["variables"].update({"max": {}}), "invalide"),                   # nom de fonction
    (lambda v: v[0]["variables"].update({"Bad-Name": {}}), "invalide"),
    (lambda v: v[0].pop("expression"), "expression"),
    (lambda v: v[0].update(variables={}), "non vide"),
])
def test_invalid_definitions_fail_loudly(d, mutate, message):
    versions = [{**V1, "variables": {k: dict(x) for k, x in V1["variables"].items()}}]
    mutate(versions)
    write(d, versions=versions)
    with pytest.raises(RegistryError, match=message):
        load_registry(d)


def test_file_name_must_match_code_and_code_must_be_valid(d):
    data = {"code": "TST001", "versions": [dict(V1)]}
    (d / "autre.yaml").write_text(yaml.safe_dump(data))
    with pytest.raises(RegistryError, match="nom du fichier"):
        load_registry(d)
    (d / "autre.yaml").unlink()
    (d / "bad.yaml").write_text(yaml.safe_dump({"code": "bad code", "versions": [dict(V1)]}))
    with pytest.raises(RegistryError, match="code invalide"):
        load_registry(d)


def test_unreadable_or_empty_inputs_fail_loudly(d):
    with pytest.raises(RegistryError, match="Aucune formule"):
        load_registry(d)
    with pytest.raises(RegistryError, match="introuvable"):
        load_registry(d / "nope")
    (d / "tst001.yaml").write_text("code: [unclosed")
    with pytest.raises(RegistryError, match="illisible"):
        load_registry(d)


def test_unknown_formula_or_version(d):
    write(d)
    reg = load_registry(d)
    with pytest.raises(RegistryError, match="inconnue"):
        reg.get("NOPE")
    with pytest.raises(RegistryError, match="Version 9"):
        reg.get("TST001", 9)
