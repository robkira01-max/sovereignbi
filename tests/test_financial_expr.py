"""P-073 : évaluateur d'expressions financières (Decimal, sans eval)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.financial.expr import MAX_EXPR_LEN, Expr, ExpressionError

D = Decimal


def ev(src, **v):
    return Expr(src, set(v)).evaluate({k: D(x) for k, x in v.items()})


def test_arithmetic_is_exact_decimal_not_float():
    assert ev("a + b", a="0.1", b="0.2") == D("0.3")
    assert ev("a * 100", a="1.15") == D("115.00")
    assert ev("2.675 * 1") == D("2.675")           # constante lue depuis le texte, pas via float


def test_precedence_parentheses_and_unary():
    assert ev("a + b * c", a="1", b="2", c="3") == 7
    assert ev("(a + b) * c", a="1", b="2", c="3") == 9
    assert ev("-a + b", a="5", b="8") == 3
    assert ev("a - -b", a="5", b="8") == 13


def test_whitelisted_functions():
    assert ev("max(a - b, 0)", a="3", b="8") == 0
    assert ev("max(a - b, 0)", a="9", b="8") == 1
    assert ev("min(a, b, 7)", a="9", b="8") == 7
    assert ev("abs(a - b)", a="3", b="8") == 5


def test_division_by_zero_is_not_swallowed():
    import decimal
    with pytest.raises((decimal.DivisionByZero, decimal.InvalidOperation)), decimal.localcontext() as c:
        c.traps[decimal.DivisionByZero] = True
        c.traps[decimal.InvalidOperation] = True
        ev("a / b", a="1", b="0")


@pytest.mark.parametrize("src", [
    "__import__('os').system('id')",     # appel non autorisé
    "a ** b",                            # puissance interdite
    "a % b", "a // b",                   # autres opérateurs
    "a.real",                            # attribut
    "a[0]",                              # indexation
    "'texte'",                           # chaîne
    "True",                              # booléen
    "1j",                                # complexe
    "lambda: 1",                         # lambda
    "[x for x in (a,)]",                 # compréhension
    "a if b else a",                     # conditionnelle
    "a < b",                             # comparaison
    "a and b",                           # logique
    "sum(a)",                            # fonction hors liste blanche
    "max(a, key=abs)",                   # mot-clé
    "max()",                             # sans argument
    "abs(a, b)",                         # mauvais nombre d'arguments
    "(a).__class__",                     # attribut dunder
    "x + a",                             # variable non déclarée
    "a; b", "a = 1", "",                 # syntaxe / vide
])
def test_rejects_anything_outside_the_whitelist(src):
    with pytest.raises(ExpressionError):
        Expr(src, {"a", "b"})


def test_limits_on_size_and_complexity():
    with pytest.raises(ExpressionError, match="longue"):
        Expr("a" + " + a" * (MAX_EXPR_LEN // 3), {"a"})
    with pytest.raises(ExpressionError, match="complexe"):
        Expr(" + ".join(["a"] * 70), {"a"})      # > 120 nœuds mais < 300 caractères


@pytest.mark.parametrize("src", ["0x10", "0b101", "0o7", "1_000", "1e999", "1e-999", "1e400 + a"])
def test_non_decimal_or_extreme_constants_are_refused_at_load_time(src):
    with pytest.raises(ExpressionError):
        Expr(src, {"a"})


def test_ordinary_constants_are_still_accepted():
    assert ev("a * 1.5 + 100 + 0.25", a="2") == D("103.25")
