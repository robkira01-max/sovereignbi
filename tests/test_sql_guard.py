import pytest

from app.security.sql_guard import SQLGuardError, validate_sql

T = {"ventes"}


def test_select_ok_and_limit_added():
    out = validate_sql("SELECT region, SUM(montant) FROM ventes GROUP BY region", T)
    assert "LIMIT 1000" in out.upper()


def test_cte_ok():
    validate_sql("WITH a AS (SELECT * FROM ventes) SELECT COUNT(*) FROM a", T)


@pytest.mark.parametrize("sql", [
    "DROP TABLE ventes",
    "DELETE FROM ventes",
    "INSERT INTO ventes VALUES (1)",
    "SELECT 1; DROP TABLE ventes",
    "SELECT * FROM autre_table",
    "SELECT * FROM read_csv('/etc/passwd')",
    "SELECT * FROM ventes, read_parquet('x.parquet')",
    "COPY ventes TO '/tmp/x.csv'",
    "ATTACH '/tmp/x.db'",
    "SELECT * FROM glob('/*')",
    "pas du sql du tout !!",
])
def test_dangerous_rejected(sql):
    with pytest.raises(SQLGuardError):
        validate_sql(sql, T)
