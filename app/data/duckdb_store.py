"""Stockage de données local : DuckDB sur fichier persistant, accès externe désactivé."""
import os
import re
from pathlib import Path

import duckdb
import pandas as pd

from app import ai_policy
from app.security import row_policy


def _safe_name(stem: str) -> str:
    name = re.sub(r"\W+", "_", stem.strip().lower()).strip("_")
    return name if name and not name[0].isdigit() else f"t_{name}"


# Tables internes du pack Audit (P-073) : ni importables par un utilisateur, ni visibles de l'IA / des tableaux de bord.
# Elles sont écrites uniquement par app/financial/runs.py via la connexion directe.
RESERVED_TABLES = frozenset({"audit_analysis_runs", "audit_calculation_results",
                             "audit_documents", "audit_quality_issues",
                             "audit_rule_runs", "audit_findings"})
# Données normalisées du pack Audit (P-074) : interrogeables (sécurité par ligne applicable) mais jamais remplaçables par un upload.
UPLOAD_BLOCKED = RESERVED_TABLES | {"audit_financial_records"}


WORKSPACE_NAMESPACE = "workspace_"     # espace de travail (P-086a) : tables internes, jamais créées ni remplacées par un upload
AUDIT_NAMESPACE = "audit_"     # préfixe réservé au pack Audit : jamais créé par un upload (donc source « de confiance »)


class ReservedTableError(ValueError):
    """Nom de table réservé (historique interne) : à traduire en refus 400 par l'appelant."""


class ProtectedTableError(ValueError):
    """Remplacement refusé : la table sert de source à une mesure calculée (P-080/MOYEN-1) ; à traduire en refus 409."""


class DataStore:
    def __init__(self):
        # Fichier persistant si SOVEREIGN_DB_PATH est défini, sinon mémoire (tests).
        db_path = os.environ.get("SOVEREIGN_DB_PATH", ":memory:")
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(db_path, config={"enable_external_access": False})
        # Reconstituer la liste des tables depuis le fichier si existant.
        existing = self.con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        self.tables: set[str] = {row[0] for row in existing if row[0] not in RESERVED_TABLES and not row[0].startswith(WORKSPACE_NAMESPACE)}
        # Tables du pack Audit créées PAR LE CODE du produit pendant ce démarrage : seules elles sont de confiance.
        # Une table `audit_*` retrouvée dans un fichier persistant n'est jamais de confiance d'office.
        self.trusted: set[str] = set()

    def load_trusted_table(self, name: str, df: pd.DataFrame) -> str:
        """Création d'une table du pack Audit (préfixe `audit_`) par le code du produit : jamais appelée par une route d'upload."""
        name = _safe_name(name)
        if not name.startswith(AUDIT_NAMESPACE) or name in RESERVED_TABLES:
            raise ReservedTableError(f"« {name} » n'est pas une table du pack Audit.")
        df = df.copy()
        df.columns = [_safe_name(str(c)) for c in df.columns]
        self.con.register("_tmp_df", df)
        self.con.execute(f'CREATE OR REPLACE TABLE "{name}" AS SELECT * FROM _tmp_df')
        self.con.unregister("_tmp_df")
        self.tables.add(name)
        self.trusted.add(name)
        return name

    def assert_user_loadable(self, name: str) -> str:
        """Nom effectif et autorisé pour un dépôt utilisateur (upload, synchro, connecteur) ; lève sinon. Un seul contrôle partagé."""
        name = _safe_name(name)
        if name in UPLOAD_BLOCKED or name.startswith((AUDIT_NAMESPACE, WORKSPACE_NAMESPACE)):
            raise ReservedTableError(f"« {name} » est un nom réservé (pack Audit ou espace de travail) : choisissez un autre nom de table.")
        if name in self.tables:
            from app.financial import trusted
            trusted.check_can_replace(name)
        return name

    def load_dataframe(self, name: str, df: pd.DataFrame) -> str:
        name = self.assert_user_loadable(name)
        row_policy.check_can_replace(name)
        df = df.copy()
        df.columns = [_safe_name(str(c)) for c in df.columns]
        self.con.register("_tmp_df", df)
        self.con.execute(f'CREATE OR REPLACE TABLE "{name}" AS SELECT * FROM _tmp_df')
        self.con.unregister("_tmp_df")
        self.tables.add(name)
        return name

    def load_file(self, path: str | Path) -> list[str]:
        from app.data.excel_loader import load_excel
        p = Path(path)
        if p.suffix.lower() == ".csv":
            return [self.load_dataframe(p.stem, pd.read_csv(p))]
        if p.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
            sheets = load_excel(p)
            stem = p.stem
            return [
                self.load_dataframe(f"{stem}_{s}" if len(sheets) > 1 else stem, df)
                for s, df in sheets.items()
            ]
        raise ValueError(f"Format non supporté : {p.suffix}")

    def schema_description(self) -> str:
        lines = []
        for t in sorted(self.tables):
            cols = self.con.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = ? ORDER BY ordinal_position", [t]).fetchall()
            lines.append(f"Table {t}({', '.join(f'{c} {d}' for c, d in cols)})")
            if ai_policy.strict():      # mode strict : le schéma seul, jamais de valeurs (SOVEREIGN_AI_STRICT)
                continue
            try:    # les exemples partent dans le prompt de l'IA : ils doivent respecter la sécurité par ligne
                sample = self.con.execute(row_policy.apply(f'SELECT * FROM "{t}" LIMIT 3')).fetchall()
            except row_policy.AccessDenied:
                sample = "(table protégée : exemples masqués)"
            lines.append(f"  exemples : {sample}")
        return "\n".join(lines)

    def execute(self, sql: str) -> tuple[list[str], list[tuple]]:
        cur = self.con.execute(row_policy.apply(sql))     # seul passage vers DuckDB : sécurité par ligne (P-068)
        return [d[0] for d in cur.description], cur.fetchall()
