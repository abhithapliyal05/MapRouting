#!/usr/bin/env bash
# Bring the routing stack up from a clean clone.
#   ./scripts/bootstrap.sh
# Idempotent: downloads are skipped when the data is already present.
set -euo pipefail

cd "$(dirname "$0")/.."

DATA_DIR="data"
OSM_FILE="$DATA_DIR/tokyo_center.osm"
PBF_URL="https://download.geofabrik.de/asia/japan/kanto-latest.osm.pbf"   # ~520 MB, Valhalla builds tiles from it
# Same bbox as backend/astar_backend.py (south,west,north,east)
BBOX="35.600,139.650,35.750,139.850"
OVERPASS_MIRRORS=(
  "https://overpass-api.de/api/interpreter"
  "https://overpass.kumi.systems/api/interpreter"
)

log()  { printf '[bootstrap] %s\n' "$*"; }
die()  { printf '[bootstrap] ERROR: %s\n' "$*" >&2; exit 1; }

# 1. Pre-flight: fail in one clear line, not after a minute of crash-looping
for cmd in docker curl; do
  command -v "$cmd" >/dev/null 2>&1 || die "'$cmd' is not installed or not on PATH"
done
docker compose version >/dev/null 2>&1 || die "'docker compose' plugin not available"
docker info >/dev/null 2>&1 || die "Docker daemon is not running"

mkdir -p "$DATA_DIR"

# 2. OSM extract for the A* backend (mounted read-only, so it must exist before start)
if [[ -s "$OSM_FILE" ]]; then
  log "found $OSM_FILE, skipping download"
else
  log "downloading Tokyo-center OSM extract from Overpass"
  query="[out:xml][timeout:180];(way[\"highway\"~\"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link)\$\"](${BBOX}););out body;>;out skel qt;"
  ok=0
  for mirror in "${OVERPASS_MIRRORS[@]}"; do
    log "trying $mirror"
    # Overpass rejects curl's default headers (HTTP 406), so identify ourselves
    if curl -fsSL --retry 2 --max-time 300 \
         -A "TokyoRoutingBootstrap/1.0" -H "Accept: application/xml, text/xml, */*" \
         --data-urlencode "data=${query}" -o "$OSM_FILE.part" "$mirror"; then
      mv "$OSM_FILE.part" "$OSM_FILE"; ok=1; break
    fi
    rm -f "$OSM_FILE.part"
  done
  [[ $ok -eq 1 ]] || die "could not download $OSM_FILE from any Overpass mirror"
fi

# 3. Valhalla input: it builds tiles from any .pbf in the data dir on first start
shopt -s nullglob
pbfs=("$DATA_DIR"/*.pbf)
if [[ ${#pbfs[@]} -gt 0 || -s "$DATA_DIR/valhalla_tiles.tar" ]]; then
  log "found Valhalla input/tiles, skipping download"
else
  log "downloading Kanto extract for Valhalla (~520 MB)"
  curl -fSL --retry 3 -C - -o "$DATA_DIR/kanto-latest.osm.pbf.part" "$PBF_URL" \
    || die "download failed: $PBF_URL"
  mv "$DATA_DIR/kanto-latest.osm.pbf.part" "$DATA_DIR/kanto-latest.osm.pbf"
fi

# 4. Start the stack and wait for every healthcheck to pass
log "starting stack (first run builds Valhalla tiles and first run builds tiles, ~40 min for Kanto)"
docker compose up -d --build --wait --wait-timeout 3600

docker compose ps
log "done: frontend http://localhost:8080  valhalla :8002  astar :8003"
