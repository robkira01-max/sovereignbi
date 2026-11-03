#!/usr/bin/env bash
# 20 — Sauvegarde SovereignBI : données DuckDB, dashboards YAML, cache SQLite.
# Usage : ./tools/backup.sh [DEST_DIR]
# Cron  : 0 3 * * * /home/kali/sovereignbi/tools/backup.sh /backups/sovereignbi

set -euo pipefail

DEST_DIR="${1:-/backups/sovereignbi}"
SRC_DIR="${SOVEREIGNBI_DIR:-/home/kali/sovereignbi}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TS=$(date -u +"%Y%m%d_%H%M%S")
ARCHIVE="${DEST_DIR}/sovereignbi_${TS}.tar.gz"

mkdir -p "$DEST_DIR"

# Inclut : data/ (DuckDB + datasets), templates/, le cache SQLite si présent
tar -czf "$ARCHIVE" \
    -C "$SRC_DIR" \
    --exclude="*.pyc" \
    --exclude="__pycache__" \
    --exclude=".venv" \
    --exclude="node_modules" \
    --exclude="frontend/dist" \
    data/ \
    templates/ \
    $([ -f "${SRC_DIR}/sovereignbi_cache.db" ] && echo "sovereignbi_cache.db" || true)

SIZE=$(du -sh "$ARCHIVE" | cut -f1)
echo "[backup] ${TS} — Archive : ${ARCHIVE} (${SIZE})"

# Nettoyage des archives plus vieilles que RETENTION_DAYS
find "$DEST_DIR" -name "sovereignbi_*.tar.gz" -mtime "+${RETENTION_DAYS}" -delete
echo "[backup] Rétention ${RETENTION_DAYS}j appliquée"
