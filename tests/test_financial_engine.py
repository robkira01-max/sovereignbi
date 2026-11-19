"""P-073 : moteur de calcul (critères d'acceptation de la proposition)."""
from __future__ import annotations

from decimal import Decimal

import pytest
import yaml

from app.financial.engine import (
    CalculationError,
    calculate,
    canonical,
    input_snapshot_hash,
    result_hash,
)
from app.financial.registry import DEFAULT_DIR, load_registry

D = Decimal
REG = load_registry(DEFAULT_DIR)


def run(code, **inputs):
    return calculate(REG.get(code), {k: D(v) for k, v in inputs.items()})


# ── cas de référence de la proposition ──────────────────────────────────────

def test_reference_budget_120m_spent_114m_is_95_percent():
    r = run("BUD001", budget_vote="120000000", depenses="114000000")
    assert r.status == "ok" and r.value == D("95.00") and r.unit == "%"


def test_reference_budget_50m_spent_57m_is_114_percent():
    assert run("BUD001", budget_vote="50000000", depenses="57000000").value == D("114.00")


def test_reference_revenue_60m_expected_54m_collected_is_90_percent():
    assert run("REC001", recettes_prevues="60000000", recettes_encaissees="54000000").value == D("90.00")


@pytest.mark.parametrize("code,inputs,expected", [
    ("BUD002", dict(depenses="57", budget_vote="50"), "7.00"),       # dépassement
    ("BUD002", dict(depenses="40", budget_vote="50"), "0.00"),       # pas de dépassement : 0, pas négatif
    ("BUD003", dict(depenses="57", budget_vote="50"), "14.00"),
    ("BUD004", dict(budget_vote="50", depenses="57"), "-7.00"),      # négatif = dépassement
    ("BUD005", dict(depenses="57", budget_vote="50"), "14.00"),
    ("BUD006", dict(budget_vote="50", depenses="57"), "0.00"),
    ("BUD006", dict(budget_vote="50", depenses="20"), "30.00"),
    ("BUD007", dict(engagements="30", budget_vote="120"), "25.00"),
    ("BUD008", dict(paiements="15", engagements="60"), "25.00"),
    ("REC002", dict(recettes_encaissees="54", recettes_prevues="60"), "-6.00"),
    ("REC003", dict(recettes_prevues="60", recettes_encaissees="54"), "6.00"),
    ("REC003", dict(recettes_prevues="60", recettes_encaissees="70"), "0.00"),
])
def test_shipped_library_values(code, inputs, expected):
    assert run(code, **inputs).value == D(expected)


# ── règles explicites : zéro, manquant, négatif, inconnu ───────────────────

def test_division_by_zero_is_refused_with_explicit_error():
    with pytest.raises(CalculationError) as e:
        run("BUD001", budget_vote="0", depenses="10")
    assert e.value.code == "division_by_zero"
    with pytest.raises(CalculationError) as e:       # 0/0 aussi
        run("BUD001", budget_vote="0", depenses="0")
    assert e.value.code == "division_by_zero"


def test_missing_negative_and_unknown_inputs_are_explicit_errors():
    fv = REG.get("BUD001")
    with pytest.raises(CalculationError) as e:
        calculate(fv, {"depenses": D(1)})
    assert e.value.code == "missing_value" and "budget_vote" in str(e.value)
    with pytest.raises(CalculationError) as e:
        calculate(fv, {"depenses": D(1), "budget_vote": None})
    assert e.value.code == "missing_value"
    with pytest.raises(CalculationError) as e:
        run("BUD001", budget_vote="-5", depenses="1")
    assert e.value.code == "negative_value"
    with pytest.raises(CalculationError) as e:
        run("BUD001", budget_vote="5", depenses="1", surprise="2")
    assert e.value.code == "unknown_variable"
    with pytest.raises(CalculationError) as e:
        calculate(fv, {"depenses": D("NaN"), "budget_vote": D(1)})
    assert e.value.code == "invalid_value"
    with pytest.raises(CalculationError) as e:
        calculate(fv, {"depenses": D("Infinity"), "budget_vote": D(1)})
    assert e.value.code == "invalid_value"


def _custom(tmp_path, **over):
    v = {"version": 1, "label": "T", "expression": "a / b", "precision": 2, "rounding": "ROUND_HALF_UP",
         "on_zero_division": "error", "variables": {"a": {"allow_negative": True}, "b": {"allow_negative": True}}}
    v.update(over)
    (tmp_path / "tst001.yaml").write_text(yaml.safe_dump({"code": "TST001", "versions": [v]}))
    return load_registry(tmp_path).get("TST001")


def test_zero_division_rule_null_gives_declared_undefined_result(tmp_path):
    r = calculate(_custom(tmp_path, on_zero_division="null"), {"a": D(1), "b": D(0)})
    assert r.status == "undefined" and r.value is None and "indéfini" in r.message


def test_optional_variable_uses_its_explicit_default(tmp_path):
    fv = _custom(tmp_path, expression="a + b", variables={"a": {}, "b": {"required": False, "default": "5"}})
    assert calculate(fv, {"a": D(1)}).value == D("6.00")
    assert calculate(fv, {"a": D(1), "b": D(2)}).value == D("3.00")


@pytest.mark.parametrize("mode,expected", [("ROUND_HALF_UP", "2.68"), ("ROUND_HALF_EVEN", "2.68"),
                                           ("ROUND_DOWN", "2.67"), ("ROUND_FLOOR", "2.67"), ("ROUND_CEILING", "2.68")])
def test_rounding_mode_is_the_formulas_own(tmp_path, mode, expected):
    fv = _custom(tmp_path, expression="a / b", rounding=mode)
    assert calculate(fv, {"a": D("2.675"), "b": D(1)}).value == D(expected)


def test_half_up_vs_half_even_differ_on_exact_halves(tmp_path):
    up = calculate(_custom(tmp_path, rounding="ROUND_HALF_UP", precision=0), {"a": D("2.5"), "b": D(1)})
    even = calculate(_custom(tmp_path, rounding="ROUND_HALF_EVEN", precision=0), {"a": D("2.5"), "b": D(1)})
    assert (up.value, even.value) == (D(3), D(2))


def test_raw_value_is_kept_unrounded(tmp_path):
    r = calculate(_custom(tmp_path, precision=2), {"a": D(1), "b": D(3)})
    assert r.value == D("0.33") and r.raw_value.as_tuple().digits[:6] == (3, 3, 3, 3, 3, 3)


def test_out_of_range_inputs_are_refused_at_validation(tmp_path):
    fv = _custom(tmp_path, expression="a * b")
    for bad in ("1e300", "1e-999990", "1" * 39):
        with pytest.raises(CalculationError) as e:
            calculate(fv, {"a": D(bad), "b": D(1)})
        assert e.value.code == "invalid_value"
    assert calculate(fv, {"a": D("1e30"), "b": D(1)}).status == "ok"       # la borne elle-même reste permise


def test_overflow_from_allowed_inputs_fails_cleanly_instead_of_crashing(tmp_path):
    fv = _custom(tmp_path, expression=" * ".join(["a"] * 34), variables={"a": {}})   # (1e30)^34 = 1e1020 > Emax
    with pytest.raises(CalculationError) as e:
        calculate(fv, {"a": D("1e30")})
    assert e.value.code == "overflow"


# ── reproductibilité ────────────────────────────────────────────────────────

def test_same_inputs_same_hash_and_different_inputs_different_hash():
    def h(**inp):
        r = run("BUD001", **inp)
        return result_hash(r, input_snapshot_hash(r.inputs))
    assert h(budget_vote="120000000", depenses="114000000") == h(budget_vote="120000000", depenses="114000000")
    assert h(budget_vote="120000000", depenses="114000000") != h(budget_vote="120000000", depenses="114000001")
    # même valeur écrite autrement → même hash (forme canonique)
    assert h(budget_vote="120000000", depenses="114000000") == h(budget_vote="1.2E+8", depenses="114000000.00")


def test_snapshot_hash_includes_declared_provenance():
    ins = {"a": D(1)}
    assert input_snapshot_hash(ins, {"a": {"explicit": True}}) != input_snapshot_hash(ins, {"a": {"table": "t"}})


def test_canonical_form():
    assert [canonical(D(x)) for x in ("95.00", "1E+2", "-0", "0.000", "12.340")] == ["95", "100", "0", "0", "12.34"]
