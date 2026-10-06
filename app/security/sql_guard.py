"""Garde-fou SQL : analyse syntaxique (sqlglot), pas de regex.

Règles : une seule instruction, SELECT uniquement, tables en liste blanche,
fonctions de lecture de fichiers bloquées, LIMIT forcé.
"""
import sqlglot
from sqlglot import exp


class SQLGuardError(ValueError):
    pass


_FORBIDDEN_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
    exp.Command, exp.Merge, exp.Pragma, exp.Set, exp.Use, exp.Attach,
)
_BLOCKED_FUNCS = {
    "read_csv", "read_csv_auto", "read_parquet", "read_json", "read_json_auto",
    "read_text", "read_blob", "glob", "query", "query_table", "sniff_csv",
    "parquet_scan", "csv_scan", "json_scan", "pragma_database_list",
}


def validate_sql(sql: str, allowed_tables: set[str], max_rows: int = 1000, dialect: str = "duckdb") -> str:
    try:
        statements = [s for s in sqlglot.parse(sql, read=dialect) if s is not None]
    except sqlglot.errors.ParseError as e:
        raise SQLGuardError(f"SQL invalide : {e}") from e
    if len(statements) != 1:
        raise SQLGuardError("Une seule instruction SQL est autorisée.")
    tree = statements[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Subquery)):
        raise SQLGuardError("Seules les requêtes SELECT sont autorisées.")
    if tree.find(*_FORBIDDEN_NODES):
        raise SQLGuardError("Instruction interdite détectée.")

    for f in tree.find_all(exp.Func):
        name = (f.name if isinstance(f, exp.Anonymous) else f.sql_name()).lower()
        if name in _BLOCKED_FUNCS or name.startswith("read_"):
            raise SQLGuardError(f"Fonction interdite : {name}")

    allowed = {t.lower() for t in allowed_tables}
    ctes = {c.alias.lower() for c in tree.find_all(exp.CTE)}
    for t in tree.find_all(exp.Table):
        if not t.name:
            raise SQLGuardError("Source de données non autorisée.")
        if t.name.lower() not in allowed | ctes:
            raise SQLGuardError(f"Table non autorisée : {t.name}")

    if not tree.args.get("limit"):
        tree = tree.limit(max_rows)
    return tree.sql(dialect=dialect)
