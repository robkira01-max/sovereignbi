#!/usr/bin/env bash
# 20 — Vérifie qu'une archive de sauvegarde SovereignBI est restaurable.
# Usage : ./tools/test_restore.sh <archive.tar.gz>
# Retour : 0 = OK, 1 = ÉCHEC

set -euo pipefail

ARCHIVE="${1:-}"
if [[ -z "$ARCHIVE" || ! -f "$ARCHIVE" ]]; then
    echo "[test_restore] Usage : $0 <archive.tar.gz>" >&2
    exit 1
fi

WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

echo "[test_restore] Extraction de ${ARCHIVE} vers ${WORK_DIR}…"
tar -xzf "$ARCHIVE" -C "$WORK_DIR"

# Vérifie la présence du répertoire data/ (source de vérité DuckDB)
if [[ ! -d "${WORK_DIR}/data" ]]; then
    echo "[test_restore] ÉCHEC — répertoire data/ absent de l'archive" >&2
    exit 1
fi

# Vérifie qu'au moins un fichier DuckDB ou CSV est présent
DB_FILES=$(find "${WORK_DIR}/data" \( -name "*.duckdb" -o -name "*.csv" \) | wc -l)
if [[ "$DB_FILES" -eq 0 ]]; then
    echo "[test_restore] AVERTISSEMENT — aucun fichier de données trouvé dans data/"
fi

echo "[test_restore] OK — archive valide (${DB_FILES} fichiers de données, templates présents : $([ -d ${WORK_DIR}/templates ] && echo oui || echo non))"
exit 0
