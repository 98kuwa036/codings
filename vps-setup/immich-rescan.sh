#!/bin/sh
#
# immich-rescan.sh
#
# Watches the rclone-mounted OneDrive directory for new files and triggers
# an Immich external library scan via the Immich API.
#
# Runs as a Docker container alongside Immich (see docker-compose.yml).
# Uses 60-second debounce to batch rapid file additions into a single scan.
#
# Required environment variables (set in .env):
#   IMMICH_URL          - e.g. http://immich-server:3001
#   IMMICH_API_KEY      - Immich admin API key
#   IMMICH_LIBRARY_ID   - External library ID (from Immich Web UI)
#   WATCH_PATH          - Directory to watch (default: /mnt/onedrive)
#

WATCH_PATH="${WATCH_PATH:-/mnt/onedrive}"
DEBOUNCE_SECONDS="${DEBOUNCE_SECONDS:-60}"
IMMICH_URL="${IMMICH_URL:-http://immich-server:3001}"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [rescan] $*"
}

trigger_scan() {
    if [ -z "${IMMICH_LIBRARY_ID}" ]; then
        log "WARN: IMMICH_LIBRARY_ID not set, skipping scan"
        return
    fi

    log "Triggering library scan for library: ${IMMICH_LIBRARY_ID}"
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST \
        -H "x-api-key: ${IMMICH_API_KEY}" \
        -H "Content-Type: application/json" \
        "${IMMICH_URL}/api/library/${IMMICH_LIBRARY_ID}/scan")

    if [ "${RESPONSE}" = "204" ] || [ "${RESPONSE}" = "200" ]; then
        log "Scan triggered successfully (HTTP ${RESPONSE})"
    else
        log "ERROR: Scan trigger failed (HTTP ${RESPONSE})"
    fi
}

wait_for_immich() {
    log "Waiting for Immich server at ${IMMICH_URL}..."
    for i in $(seq 1 30); do
        STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${IMMICH_URL}/api/server/ping" 2>/dev/null)
        if [ "${STATUS}" = "200" ]; then
            log "Immich is ready"
            return 0
        fi
        log "  Attempt ${i}/30: Immich not ready yet (HTTP ${STATUS}), retrying in 10s..."
        sleep 10
    done
    log "ERROR: Immich did not become ready within 5 minutes"
    return 1
}

# ─────────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────────
log "Starting Immich auto-rescan watcher"
log "Watch path: ${WATCH_PATH}"
log "Debounce: ${DEBOUNCE_SECONDS}s"

wait_for_immich || exit 1

# Initial scan on startup
log "Running initial library scan..."
trigger_scan

# Watch for new/modified files using inotifywait
# Events: create, move (rclone uses move to finalize uploads), close_write
LAST_TRIGGER=0

log "Watching ${WATCH_PATH} for changes..."
inotifywait -m -r \
    -e create \
    -e moved_to \
    -e close_write \
    --format '%T %e %w%f' \
    --timefmt '%Y-%m-%d %H:%M:%S' \
    "${WATCH_PATH}" 2>/dev/null | while read -r TIMESTAMP EVENT FILEPATH; do

    # Ignore .xmp changes (we trigger on the photo file)
    case "${FILEPATH}" in
        *.xmp|*.json|*.log|*.tmp) continue ;;
    esac

    log "Change detected: ${EVENT} ${FILEPATH}"

    NOW=$(date +%s)
    ELAPSED=$((NOW - LAST_TRIGGER))

    if [ "${ELAPSED}" -lt "${DEBOUNCE_SECONDS}" ]; then
        log "  Debouncing (${ELAPSED}s < ${DEBOUNCE_SECONDS}s), will scan after cooldown"
        continue
    fi

    # Debounce: sleep and check if another event arrives
    sleep "${DEBOUNCE_SECONDS}"

    trigger_scan
    LAST_TRIGGER=$(date +%s)
done
