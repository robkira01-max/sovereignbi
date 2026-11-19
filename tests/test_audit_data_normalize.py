"""P-074 : normalisation et contrôle qualité (aucune correction silencieuse)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.audit_data.normalize import (
    ImportOptions, OptionsError, ValueIssue, normalize, parse_amount, parse_date, suggest, validate_options,
)
from app.audit_data.parse import Table

H = ["Date", "Compte", "Libellé", "Montant", "Devise"]
MAP = {"entry_date": "Date", "account": "Compte", "label": "Libellé", "amount": "Montant", "currency": "Devise"}


def table(rows, headers=H):
    return Table(headers=list(headers), rows=[(i + 2, list(r)) for i, r in enumerate(rows)])


def opts(**kw):
    base = dict(mapping=MAP, decimal_separator=",", date_format="%d/%m/%Y")
    base.update(kw)
    return ImportOptions(**base)


def codes(res):
    return sorted(i.code for i in res.issues)


# ── montants ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,dec,expected", [
    ("1 200,50", ",", "1200.50"), ("1.200,50", ",", "1200.50"), ("1,200.50", ".", "1200.50"), ("1200", ",", "1200"),
    ("(100,00)", ",", "-100.00"), ("-5,5", ",", "-5.5"), ("+7", ",", "7"), ("1 000,5", ",", "1000.5"),
    (12, ".", "12"), (12.5, ",", "12.5"), (Decimal("3.10"), ".", "3.10"), (None, ".", None),
])
def test_amounts_parse_exactly(raw, dec, expected):
    r = parse_amount(raw, dec)
    assert (r is None) if expected is None else r == Decimal(expected)


def test_float_amounts_do_not_carry_binary_noise():
    assert parse_amount(0.1, ".") == Decimal("0.1") and str(parse_amount(1200.5, ".")) == "1200.5"


@pytest.mark.parametrize("raw,dec", [
    ("12,50", "."), ("1,200.50", ","), ("abc", ","), ("12,5,5", ","), ("1 2 3", ","), ("--5", ","), ("1e5", ","),
    ("١٢٣", ","), ("", ","), ("1.200.50", ","),
])
def test_ambiguous_or_garbled_amounts_are_refused(raw, dec):
    with pytest.raises(ValueIssue) as e:
        parse_amount(raw, dec)
    assert e.value.code == "non_numeric_amount"


def test_decimal_separator_is_not_guessed():
    # « 1,234 » vaut 1,234 avec « , » décimal, mais « . » déclaré le lit comme 1234 : l'utilisateur tranche
    assert parse_amount("1,234", ",") == Decimal("1.234")
    assert parse_amount("1,234", ".") == Decimal("1234")


def test_too_many_decimals_is_refused_not_rounded():
    with pytest.raises(ValueIssue) as e:
        parse_amount("1,1234567", ",")
    assert e.value.code == "too_many_decimals"
    assert parse_amount("1,1234560", ",") == Decimal("1.123456")      # zéros de fin : aucune perte


def test_non_finite_bool_date_and_huge_amounts_are_refused():
    for bad in (float("nan"), float("inf"), True, date(2026, 1, 1)):
        with pytest.raises(ValueIssue):
            parse_amount(bad, ".")
    with pytest.raises(ValueIssue) as e:
        parse_amount("9" * 40, ".")
    assert e.value.code == "amount_out_of_range"


# ── dates ───────────────────────────────────────────────────────────────────

def test_dates_follow_the_declared_format_only():
    assert parse_date("03/04/2026", "%d/%m/%Y") == date(2026, 4, 3)
    assert parse_date("03/04/2026", "%m/%d/%Y") == date(2026, 3, 4)
    assert parse_date(datetime(2026, 1, 5, 10), "%d/%m/%Y") == date(2026, 1, 5)
    for bad in ("2026-01-05", "31/02/2026", "x" * 30, 45000, 45000.5):
        with pytest.raises(ValueIssue) as e:
            parse_date(bad, "%d/%m/%Y")
        assert e.value.code == "invalid_date"


# ── options ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("kw,code", [
    ({"decimal_separator": "x"}, "decimal_separator_required"),
    ({"date_format": "%d %b"}, "date_format_required"),
    ({"mapping": {**MAP, "bogus": "Date"}}, "unknown_field"),
    ({"mapping": {**MAP, "account": "Nope"}}, "unknown_column"),
    ({"mapping": {**MAP, "label": "Date"}}, "column_reused"),
    ({"mapping": {k: v for k, v in MAP.items() if k != "account"}}, "missing_mapping"),
    ({"mapping": {k: v for k, v in MAP.items() if k != "amount"}}, "missing_mapping"),
    ({"mapping": {**MAP, "debit": "Extra"}, "_extra": True}, "amount_ambiguous"),
    ({"mapping": {k: v for k, v in MAP.items() if k != "currency"}}, "currency_required"),
    ({"default_currency": "ZZZ"}, "unknown_currency"),
    ({"default_fiscal_year": 1800}, "invalid_fiscal_year"),
])
def test_invalid_options_are_refused_with_a_code(kw, code):
    kw = dict(kw)
    extra = kw.pop("_extra", False)
    t = table([["01/01/2026", "601", "x", "1", "DJF", "9"]], headers=H + ["Extra"]) if extra \
        else table([["01/01/2026", "601", "x", "1", "DJF"]])
    with pytest.raises(OptionsError) as e:
        validate_options(t, opts(**kw))
    assert e.value.code == code


def test_missing_currency_is_an_error_unless_explicitly_defaulted():
    t = table([["01/01/2026", "601", "x", "100", "DJF"]])
    no_ccy = {k: v for k, v in MAP.items() if k != "currency"}
    with pytest.raises(OptionsError) as e:
        normalize(t, opts(mapping=no_ccy))
    assert e.value.code == "currency_required"
    res = normalize(t, opts(mapping=no_ccy, default_currency="DJF"))
    assert res.records[0].currency == "DJF" and res.records[0].currency_source == "default"


# ── contrôle qualité ────────────────────────────────────────────────────────

def test_clean_data_has_no_issue_and_exact_values():
    res = normalize(table([["05/01/2026", 601, "Achat", "1 200,50", "djf"]]), opts())
    r = res.records[0]
    assert res.issues == [] and not r.has_error
    assert (r.entry_date, r.account, r.amount, r.currency, r.currency_source) == (date(2026, 1, 5), "601", Decimal("1200.50"), "DJF", "column")


def test_each_defect_is_reported_with_row_field_and_code():
    res = normalize(table([
        [None, "601", "a", "10", "DJF"],               # date manquante
        ["31/02/2026", "601", "b", "10", "DJF"],       # date invalide
        ["05/01/2026", None, "c", "10", "DJF"],        # compte manquant
        ["05/01/2026", "601", "d", "abc", "DJF"],      # montant non numérique
        ["05/01/2026", "601", "e", None, "DJF"],       # aucun montant
        ["05/01/2026", "601", "f", "10", "XXX"],       # devise inconnue
        ["05/01/2026", "601", "g", "10", None],        # devise manquante
        ["05/01/2026", "601", "h", "10", "DJF"],       # ok
    ]), opts())
    got = {(i.source_row, i.field, i.code) for i in res.issues}
    assert got == {(2, "entry_date", "missing_value"), (3, "entry_date", "invalid_date"), (4, "account", "missing_value"),
                   (5, "amount", "non_numeric_amount"), (6, "amount", "missing_value"),
                   (7, "currency", "unknown_currency"), (8, "currency", "missing_currency")}
    assert [r.has_error for r in res.records] == [True] * 7 + [False]
    assert res.records[1].entry_date is None and res.records[3].amount is None       # NULL, jamais une valeur inventée
    assert all(i.severity == "error" for i in res.issues)


def test_raw_values_in_issues_are_truncated():
    res = normalize(table([["05/01/2026", "601", "x", "z" * 500, "DJF"]]), opts())
    assert len(res.issues[0].raw_value) <= 100


def test_duplicates_are_flagged_as_warning_referencing_first_row():
    row = ["05/01/2026", "601", "Achat", "100", "DJF"]
    res = normalize(table([row, row, row]), opts())
    dup = [i for i in res.issues if i.code == "duplicate_row"]
    assert [(i.source_row, i.severity) for i in dup] == [(3, "warning"), (4, "warning")] and "ligne 2" in dup[0].message
    assert len(res.records) == 3                       # rien n'est supprimé


def test_out_of_range_dates_and_amounts_are_warnings():
    res = normalize(table([["05/01/1850", "601", "x", "1", "DJF"], ["05/01/2026", "601", "y", "20000000000000", "DJF"]]), opts())
    assert codes(res) == ["amount_out_of_range", "date_out_of_range"] and all(i.severity == "warning" for i in res.issues)
    assert not any(r.has_error for r in res.records)


def test_debit_credit_columns_signed_amount_and_totals_check():
    t = Table(headers=["Date", "Compte", "Débit", "Crédit", "Devise"], rows=[
        (2, ["05/01/2026", "601", "100", None, "DJF"]), (3, ["05/01/2026", "401", None, "90", "DJF"])])
    m = {"entry_date": "Date", "account": "Compte", "debit": "Débit", "credit": "Crédit", "currency": "Devise"}
    res = normalize(t, opts(mapping=m, decimal_separator="."))
    assert [r.amount for r in res.records] == [Decimal(100), Decimal(-90)]
    mism = [i for i in res.issues if i.code == "totals_mismatch"]
    assert len(mism) == 1 and mism[0].source_row is None and "écart 10" in mism[0].message
    assert res.totals == {"debit": "100", "credit": "90"}


def test_fiscal_year_column_and_default():
    t = Table(headers=H + ["Exercice"], rows=[(2, ["05/01/2026", "601", "x", "1", "DJF", "2026"]),
                                              (3, ["05/01/2026", "601", "y", "1", "DJF", "26"]),
                                              (4, ["05/01/2026", "601", "z", "1", "DJF", None])])
    res = normalize(t, opts(mapping={**MAP, "fiscal_year": "Exercice"}, default_fiscal_year=2025))
    assert [r.fiscal_year for r in res.records] == [2026, None, 2025] and codes(res) == ["invalid_fiscal_year"]


def test_issue_storage_is_capped_but_counts_are_complete(monkeypatch):
    from app.audit_data import normalize as n
    monkeypatch.setattr(n, "MAX_STORED_ISSUES", 3)
    res = normalize(table([[None, "601", "x", "1", "DJF"]] * 10), opts())
    assert len(res.issues) == 3 and res.truncated and res.counts["missing_value"] == 10


def test_suggest_maps_french_and_english_headers_and_proposes_not_decides():
    t = Table(headers=["Date écriture", "N° compte", "Libellé", "Montant", "Devise"],
              rows=[(2, ["05/01/2026", "601", "x", "1 200,50", "DJF"]), (3, ["13/01/2026", "602", "y", "80,00", "DJF"])])
    s = suggest(t)
    assert s["mapping"] == {"entry_date": "Date écriture", "account": "N° compte", "label": "Libellé", "amount": "Montant", "currency": "Devise"}
    assert s["decimal_separator"] == "," and s["date_formats"] == ["%d/%m/%Y"]
    amb = suggest(Table(headers=["Date", "Compte", "Montant"], rows=[(2, ["03/04/2026", "6", "1"])]))
    assert amb["date_formats"] == ["%d/%m/%Y", "%m/%d/%Y"]          # ambigu : deux formats, choix humain
    assert amb["decimal_separator"] is None
