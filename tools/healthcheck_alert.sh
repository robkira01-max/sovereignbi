#!/usr/bin/env bash
# 17 — Surveillance externe SovereignBI : pinge /health toutes les 2 min.
# Usage : ./tools/healthcheck_alert.sh [URL] [EMAIL]
# Cron  : */2 * * * * /home/kali/sovereignbi/tools/healthcheck_alert.sh >> /var/log/sovereignbi_health.log 2>&1

set -euo pipefail

URL="${1:-${SOVEREIGNBI_URL:-http://localhost:9001}}"
ALERT_EMAIL="${2:-${ALERT_EMAIL:-admin@example.com}}"
TIMEOUT=10
STATE_FILE="/tmp/sovereignbi_health_state"

check() {
    HTTP_CODE=$(curl -sf --max-time "$TIMEOUT" -o /dev/null -w "%{http_code}" "${URL}/health" 2>/dev/null || echo "000")
    echo "$HTTP_CODE"
}

send_alert() {
    local subject="$1"
    local body="$2"
    echo "$body" | mail -s "$subject" "$ALERT_EMAIL" 2>/dev/null \
        || echo "[healthcheck] mail non disponible — alerte: $subject"
}

CODE=$(check)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [[ "$CODE" != "200" ]]; then
    PREV_STATE=$(cat "$STATE_FILE" 2>/dev/null || echo "ok")
    echo "${TIMESTAMP} DOWN (HTTP ${CODE}) ${URL}"
    if [[ "$PREV_STATE" == "ok" ]]; then
        send_alert "[SovereignBI] ALERTE — Service indisponible (HTTP ${CODE})" \
            "URL: ${URL}/health\nHeure: ${TIMESTAMP}\nCode HTTP: ${CODE}"
    fi
    echo "down" > "$STATE_FILE"
else
    PREV_STATE=$(cat "$STATE_FILE" 2>/dev/null || echo "ok")
    echo "${TIMESTAMP} OK (HTTP 200) ${URL}"
    if [[ "$PREV_STATE" == "down" ]]; then
        send_alert "[SovereignBI] RÉTABLI" "URL: ${URL}/health\nHeure: ${TIMESTAMP}"
    fi
    echo "ok" > "$STATE_FILE"
fi
