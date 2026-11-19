"""Évaluateur d'expressions financières (P-073) : arithmétique en Decimal, sans `eval`.

Pourquoi un évaluateur maison : les formules vivent dans des fichiers YAML modifiables ; elles ne doivent
jamais pouvoir exécuter de code. On analyse l'expression avec `ast`, on n'accepte qu'une liste blanche de
nœuds (+ - * /, parenthèses, nombres, variables déclarées, max/min/abs) et on calcule nous-mêmes.
Les constantes sont relues depuis le texte source (jamais via float) pour ne perdre aucune décimale.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

MAX_EXPR_LEN = 300
MAX_NODES = 120
FUNCTIONS = {"max": max, "min": min, "abs": abs}
_BIN = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b}


class ExpressionError(ValueError):
    """Expression invalide ou non autorisée (erreur de définition de formule, pas d'entrée)."""


class Expr:
    """Expression analysée et validée ; `evaluate` ne fait que de l'arithmétique Decimal."""

    def __init__(self, source: str, declared: set[str]) -> None:
        if not isinstance(source, str) or not source.strip():
            raise ExpressionError("Expression vide.")
        if len(source) > MAX_EXPR_LEN:
            raise ExpressionError(f"Expression trop longue (max {MAX_EXPR_LEN} caractères).")
        try:
            tree = ast.parse(source.strip(), mode="eval")
        except SyntaxError as e:
            raise ExpressionError(f"Syntaxe invalide : {e.msg}") from None
        self.source = source.strip()
        self._tree = tree.body
        self.names: set[str] = set()
        self._count = 0
        self._check(self._tree, declared)

    # ── validation ──────────────────────────────────────────────────────────

    def _check(self, node: ast.AST, declared: set[str]) -> None:
        self._count += 1
        if self._count > MAX_NODES:
            raise ExpressionError("Expression trop complexe.")
        if isinstance(node, ast.BinOp):
            if type(node.op) not in _BIN:
                raise ExpressionError("Opérateur non autorisé (seuls + - * / le sont).")
            self._check(node.left, declared)
            self._check(node.right, declared)
        elif isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, (ast.USub, ast.UAdd)):
                raise ExpressionError("Opérateur unaire non autorisé.")
            self._check(node.operand, declared)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise ExpressionError("Seuls les nombres sont autorisés comme constantes.")
            text = ast.get_source_segment(self.source, node) or ""
            try:    # littéraux 0x10, 0b1, 1_0, ou exposants démesurés : refusés dès le chargement, pas au calcul
                d = Decimal(text)
            except InvalidOperation:
                raise ExpressionError(f"Constante non décimale : {text!r}.") from None
            if not d.is_finite() or (d != 0 and abs(d.adjusted()) > 30) or "_" in text:
                raise ExpressionError(f"Constante hors limites : {text!r}.")
        elif isinstance(node, ast.Name):
            if node.id not in declared:
                raise ExpressionError(f"Variable non déclarée : « {node.id} ».")
            self.names.add(node.id)
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS or node.keywords:
                raise ExpressionError(f"Appel non autorisé (fonctions permises : {', '.join(sorted(FUNCTIONS))}).")
            if not node.args or (node.func.id == "abs" and len(node.args) != 1):
                raise ExpressionError(f"Arguments invalides pour {node.func.id}().")
            for a in node.args:
                self._check(a, declared)
        else:
            raise ExpressionError(f"Construction non autorisée : {type(node).__name__}.")

    # ── évaluation ──────────────────────────────────────────────────────────

    def evaluate(self, values: Mapping[str, Decimal]) -> Decimal:
        """Peut lever decimal.DivisionByZero / InvalidOperation : l'appelant décide (jamais de silence ici)."""
        return self._ev(self._tree, values)

    def _ev(self, node: ast.AST, values: Mapping[str, Decimal]) -> Decimal:
        if isinstance(node, ast.BinOp):
            return _BIN[type(node.op)](self._ev(node.left, values), self._ev(node.right, values))
        if isinstance(node, ast.UnaryOp):
            v = self._ev(node.operand, values)
            return -v if isinstance(node.op, ast.USub) else v
        if isinstance(node, ast.Constant):
            text = ast.get_source_segment(self.source, node)
            try:
                return Decimal(text if text is not None else str(node.value))
            except InvalidOperation:
                raise ExpressionError(f"Constante illisible : {text!r}.") from None
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.Call):
            return FUNCTIONS[node.func.id](*[self._ev(a, values) for a in node.args])
        raise ExpressionError("Nœud inattendu.")  # inatteignable : _check a déjà filtré
