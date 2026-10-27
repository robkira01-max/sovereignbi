"""Stockage de données local : DuckDB sur fichier persistant, accès externe désactivé."""
import os
import re
from pathlib import Path

import duckdb
import pandas as pd


def _safe_name(stem: str) -> str:
    name = re.sub(r"\W+", "_", stem.strip().lower()).strip("_")
    return name if name and not name[0].isdigit() else f"t_{name}"


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
        self.tables: set[str] = {row[0] for row in existing}

    def load_dataframe(self, name: str, df: pd.DataFrame) -> str:
        name = _safe_name(name)
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
            sample = self.con.execute(f'SELECT * FROM "{t}" LIMIT 3').fetchall()
            lines.append(f"Table {t}({', '.join(f'{c} {d}' for c, d in cols)})")
            lines.append(f"  exemples : {sample}")
        return "\n".join(lines)

    def execute(self, sql: str) -> tuple[list[str], list[tuple]]:
        cur = self.con.execute(sql)
        return [d[0] for d in cur.description], cur.fetchall()
